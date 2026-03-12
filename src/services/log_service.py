import math
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import re

# Configure logging
logger = logging.getLogger(__name__)

from ..models.loader import get_model, get_metadata, get_model_path

_LIGHT_MODE = os.getenv("SENTIENTSHIELD_LIGHT_MODE", "").strip().lower() in ("1", "true", "yes", "on")

try:
    if _LIGHT_MODE:
        raise ImportError("SentientShield light mode disables transformers imports")
    from transformers import AutoTokenizer, AutoModel, BitsAndBytesConfig, AutoModelForCausalLM
    import torch
    _HAS_TRANSFORMERS = True
except Exception:
    AutoTokenizer = None
    AutoModel = None
    AutoModelForCausalLM = None
    BitsAndBytesConfig = None
    torch = None
    _HAS_TRANSFORMERS = False
try:
    if _LIGHT_MODE:
        raise ImportError("SentientShield light mode disables transformers pipeline imports")
    from transformers import pipeline
    _HAS_PIPELINE = True
except Exception:
    pipeline = None
    _HAS_PIPELINE = False

def _norm(v):
    return v / (v.norm(dim=-1, keepdim=True) + 1e-12)

class DistilBERTLogClassifier:
    def __init__(self):
        self.available = _HAS_TRANSFORMERS and not _LIGHT_MODE
        if self.available:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(get_model_path("distilbert-base-uncased"))
                use_gpu = bool(torch.cuda.is_available())
                bnb_ok = False
                if use_gpu and BitsAndBytesConfig is not None:
                    try:
                        import bitsandbytes as bnb
                        bnb_ok = True
                    except Exception:
                        bnb_ok = False
                if use_gpu and bnb_ok:
                    cfg = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                    )
                    self.model = AutoModel.from_pretrained(
                        get_model_path("distilbert-base-uncased"),
                        quantization_config=cfg,
                    )
                    self.device = "cuda"
                elif use_gpu:
                    self.model = AutoModel.from_pretrained(
                        "distilbert-base-uncased",
                        torch_dtype=torch.float16,
                    )
                    self.model.to("cuda")
                    self.device = "cuda"
                else:
                    self.model = AutoModel.from_pretrained(get_model_path("distilbert-base-uncased"))
                    self.device = "cpu"
                self.model.eval()
                self.severity_labels = [
                    ("low", "low severity log, informational, minor issue"),
                    ("medium", "medium severity log, warning, potential issue"),
                    ("high", "high severity log, error, significant problem"),
                    ("critical", "critical severity log, security incident, urgent action"),
                ]
                self.threat_labels = [
                    ("sql_injection", "web attack type sql injection, union select, drop table"),
                    ("xss", "web attack type cross site scripting, script tag, onerror"),
                    ("rce", "remote code execution, system call, eval"),
                    ("lfi", "local file inclusion, path traversal, etc passwd"),
                    ("xxe", "xml external entity, dtd entity expansion"),
                    ("ssrf", "server side request forgery, internal endpoint access"),
                    ("idor", "insecure direct object reference, predictable ids"),
                    ("csrf", "cross site request forgery, missing token"),
                    ("ddos", "distributed denial of service, high traffic flood"),
                    ("brute_force", "credential brute force, repeated login attempts"),
                    ("phishing", "phishing, social engineering, deceptive link"),
                    ("malware", "malware activity, payload download, suspicious binary"),
                ]
                self._sev_proto = self._embed_proto([p for _, p in self.severity_labels])
                self._thr_proto = self._embed_proto([p for _, p in self.threat_labels])
            except Exception as e:
                print(f"DistilBERT model loading failed: {e}")
                self.available = False
        
        if not self.available:
            self.severity_labels = [("low", ""), ("medium", ""), ("high", ""), ("critical", "")]
            self.threat_labels = [
                ("sql_injection", ""), ("xss", ""), ("rce", ""), ("lfi", ""), ("xxe", ""),
                ("ssrf", ""), ("idor", ""), ("csrf", ""), ("ddos", ""), ("brute_force", ""),
                ("phishing", ""), ("malware", "")
            ]
            self._sev_proto = None
            self._thr_proto = None

    def _embed(self, text: str):
        with torch.no_grad():
            tokens = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            if hasattr(self, "device"):
                tokens = tokens.to(self.device)
            out = self.model(**tokens)
            x = out.last_hidden_state.mean(dim=1)
            return _norm(x)

    def _embed_proto(self, prompts: List[str]):
        with torch.no_grad():
            tokens = self.tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=64)
            if hasattr(self, "device"):
                tokens = tokens.to(self.device)
            out = self.model(**tokens)
            x = out.last_hidden_state.mean(dim=1)
            return _norm(x)

    def _cos_scores(self, x, proto):
        return (x @ proto.T).squeeze(0)

    def classify_severity(self, message: str) -> Tuple[str, float]:
        if not message:
            return "low", 0.0
        if self.available:
            x = self._embed(message)
            s = self._cos_scores(x, self._sev_proto)
            i = int(s.argmax().item())
            score = float(s[i].item())
            return self.severity_labels[i][0], score
        msg = message.lower()
        rules = [
            ("critical", ["panic", "breach", "compromise", "exfiltration", "ransom"]),
            ("high", ["failed login", "sql", "injection", "shell", "root", "elevated"]),
            ("medium", ["timeout", "error", "exception", "retry", "degraded"]),
            ("low", ["info", "started", "connected", "ok", "success"]),
        ]
        for label, kws in rules:
            if any(k in msg for k in kws):
                return label, 0.7
        return "low", 0.3

    def predict_threat_type(self, message: str) -> Tuple[str, float]:
        if not message:
            return "unknown", 0.0
        if self.available:
            x = self._embed(message)
            s = self._cos_scores(x, self._thr_proto)
            i = int(s.argmax().item())
            score = float(s[i].item())
            return self.threat_labels[i][0], score
        msg = message.lower()
        patterns = [
            ("sql_injection", ["union select", "drop table", "' or '1'='1", "or 1=1"]),
            ("xss", ["<script", "onerror", "onload", "javascript:"]),
            ("rce", ["system(", "exec(", "eval(", "assert("]),
            ("lfi", ["../", "..\\", "/etc/passwd", "windows/system32"]),
            ("xxe", ["<!ENTITY", "SYSTEM", "file://"]),
            ("ssrf", ["http://localhost", "http://127.0.0.1", "gopher://"]),
            ("idor", ["id=", "user=", "account=", "profile="]),
            ("csrf", ["csrf", "token", "nonce"]),
            ("ddos", ["high traffic", "flood", "rate limit"]),
            ("brute_force", ["failed login", "attempts", "password guess"]),
            ("phishing", ["click this link", "verify account", "credential harvest"]),
            ("malware", ["payload", "trojan", "virus", "binary"]),
        ]
        for label, kws in patterns:
            if any(k in msg for k in kws):
                return label, 0.8
        return "unknown", 0.2

    def filter_alert(self, message: str) -> Tuple[bool, str, float]:
        sev, s_score = self.classify_severity(message)
        thr, t_score = self.predict_threat_type(message)
        m = message.lower()
        noise = any(k in m for k in ["heartbeat", "healthcheck", "debug", "trace"])
        if noise and sev in ["low", "medium"]:
            return False, "ignore", 0.2
        if sev in ["high", "critical"]:
            return True, "alert", max(s_score, t_score)
        if thr in ["sql_injection", "xss", "rce", "ddos", "brute_force", "ssrf"]:
            return True, "alert", max(s_score, t_score)
        return False, "review", max(s_score, t_score)

class MiniLMEmbedder:
    def __init__(self):
        self.available = False
        self.model = None
        self.device = "cpu"
        if _LIGHT_MODE:
            return
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = SentenceTransformer(get_model_path("sentence-transformers/all-MiniLM-L6-v2"), device=self.device)
            self.available = True
        except Exception:
            self.available = False
            self.model = None

    def encode(self, texts: List[str]):
        if not texts:
            return None
        if not self.available:
            return None
        vecs = self.model.encode(texts, convert_to_tensor=True, normalize_embeddings=True)
        return vecs

class InMemoryVectorIndex:
    def __init__(self, embedder: MiniLMEmbedder):
        self.embedder = embedder
        self.texts: List[str] = []
        self.vecs = None

    def add(self, texts: List[str]):
        if not texts:
            return 0
        vecs = self.embedder.encode(texts)
        if vecs is None:
            return 0
        if self.vecs is None:
            self.vecs = vecs
            self.texts = list(texts)
        else:
            import torch
            self.vecs = torch.cat([self.vecs, vecs], dim=0)
            self.texts.extend(texts)
        return len(texts)

    def search(self, query: str, top_k: int = 5):
        if not self.texts or self.vecs is None:
            return []
        qv = self.embedder.encode([query])
        if qv is None:
            return []
        import torch
        sims = (qv @ self.vecs.T).squeeze(0)
        vals, idxs = torch.topk(sims, k=min(top_k, sims.shape[0]))
        results = []
        for s, i in zip(vals.tolist(), idxs.tolist()):
            results.append({"text": self.texts[i], "score": float(s)})
        return results

class FaissVectorIndex:
    def __init__(self, embedder: MiniLMEmbedder):
        self.embedder = embedder
        self.texts: List[str] = []
        self.index = None
        self.dim = None
        if _LIGHT_MODE:
            self.faiss = None
            return
        try:
            import faiss
            self.faiss = faiss
        except Exception:
            self.faiss = None
        self._init_index()

    def _init_index(self):
        if not self.embedder.available:
            return
        vecs = self.embedder.encode(["init"])
        if vecs is None:
            return
        import torch
        v = vecs[0].detach().cpu().numpy().astype("float32")
        self.dim = v.shape[-1]
        if self.faiss is not None and self.dim:
            self.index = self.faiss.IndexFlatIP(self.dim)

    def add(self, texts: List[str]):
        if not texts:
            return 0
        if self.index is None:
            return 0
        vecs = self.embedder.encode(texts)
        if vecs is None:
            return 0
        import torch
        V = vecs.detach().cpu().numpy().astype("float32")
        self.index.add(V)
        self.texts.extend(texts)
        return len(texts)

    def search(self, query: str, top_k: int = 5):
        if self.index is None or not self.texts:
            return []
        vec = self.embedder.encode([query])
        if vec is None:
            return []
        import torch
        Q = vec.detach().cpu().numpy().astype("float32")
        D, I = self.index.search(Q, top_k)
        results = []
        for score, idx in zip(D[0].tolist(), I[0].tolist()):
            if idx < 0 or idx >= len(self.texts):
                continue
            results.append({"text": self.texts[idx], "score": float(score)})
        return results

class ZeroShotThreatClassifier:
    def __init__(self):
        self.available = False
        self.clf = None
        if _LIGHT_MODE:
            return
        try:
            if _HAS_PIPELINE:
                self.clf = pipeline("zero-shot-classification", model=get_model_path("facebook/bart-large-mnli"))
                self.available = True
        except Exception:
            self.available = False
            self.clf = None

    def classify(self, text: str, labels: List[str], multi_label: bool = True):
        if not text or not labels:
            return {"labels": [], "scores": []}
        if not self.available:
            lower = text.lower()
            scores = []
            for l in labels:
                k = l.lower().replace(" ", "_")
                hits = sum(1 for w in k.split("_") if w and w in lower)
                scores.append(hits)
            total = sum(scores) or 1
            norm = [s / total for s in scores]
            order = sorted(range(len(labels)), key=lambda i: norm[i], reverse=True)
            return {"labels": [labels[i] for i in order], "scores": [norm[i] for i in order]}
        res = self.clf(text, candidate_labels=labels, multi_label=multi_label)
        return {"labels": res["labels"], "scores": [float(s) for s in res["scores"]]}

class PhishingDetector:
    def __init__(self):
        self.available = False
        self.clf = None
        self.device = -1
        if _LIGHT_MODE:
            return
        try:
            if _HAS_PIPELINE:
                import torch
                self.device = 0 if torch.cuda.is_available() else -1
                self.clf = pipeline("text-classification", model=get_model_path("ealvaradob/bert-finetuned-phishing"), device=self.device)
                self.available = True
        except Exception:
            self.available = False
            self.clf = None

    def classify_text(self, text: str):
        if not text:
            return {"label": "not_phishing", "score": 0.0}
        if self.available:
            out = self.clf(text, truncation=True)
            if isinstance(out, list) and out:
                res = out[0]
            else:
                res = out
            return {"label": res.get("label", ""), "score": float(res.get("score", 0.0))}
        lower = text.lower()
        indicators = ["verify", "urgent", "account", "password", "click", "login", "reset", "security", "update", "invoice", "payment"]
        hits = sum(1 for k in indicators if k in lower)
        score = min(1.0, hits / 5.0)
        return {"label": "phishing" if score > 0.5 else "not_phishing", "score": score}

class MITREAttckMapper:
    def __init__(self, zs: ZeroShotThreatClassifier, embedder: MiniLMEmbedder):
        self.zs = zs
        self.embedder = embedder
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(base_dir, "data")
        self.db_path = os.path.join(self.data_dir, "attck.db")
        self._ensure_db()
        self.tactics = [
            "Credential Access","Defense Evasion","Initial Access","Execution","Persistence",
            "Privilege Escalation","Discovery","Lateral Movement","Exfiltration","Command and Control","Impact","Collection"
        ]
        self.techniques = [
            {"id":"T1003","name":"Credential Dumping","tactic":"Credential Access","desc":"Dump credentials from system memory or files"},
            {"id":"T1078","name":"Valid Accounts","tactic":"Credential Access","desc":"Use compromised credentials to access systems"},
            {"id":"T1059","name":"Command and Scripting Interpreter","tactic":"Execution","desc":"Execute commands via interpreters like bash, cmd, PowerShell"},
            {"id":"T1204","name":"User Execution","tactic":"Execution","desc":"Malicious file execution by user interaction"},
            {"id":"T1566","name":"Phishing","tactic":"Initial Access","desc":"Deceive users to obtain credentials or deliver malware"},
            {"id":"T1190","name":"Exploit Public-Facing Application","tactic":"Initial Access","desc":"Exploit vulnerabilities in internet-facing applications"},
            {"id":"T1055","name":"Process Injection","tactic":"Privilege Escalation","desc":"Inject code into processes to escalate privileges"},
            {"id":"T1040","name":"Network Sniffing","tactic":"Discovery","desc":"Sniff network traffic to discover information"},
            {"id":"T1210","name":"Exploitation of Remote Services","tactic":"Lateral Movement","desc":"Exploit remote services to move laterally"},
            {"id":"T1041","name":"Exfiltration Over Command and Control Channel","tactic":"Exfiltration","desc":"Exfiltrate data over C2 channels"},
            {"id":"T1095","name":"Non-Application Layer Protocol","tactic":"Command and Control","desc":"Use uncommon or custom protocols for C2"},
            {"id":"T1499","name":"Endpoint Denial of Service","tactic":"Impact","desc":"Exhaust resources to cause service denial"},
            {"id":"T1036","name":"Masquerading","tactic":"Defense Evasion","desc":"Disguise artifacts to evade detection"},
            {"id":"T1082","name":"System Information Discovery","tactic":"Discovery","desc":"Query system information to understand environment"},
            {"id":"T1113","name":"Screen Capture","tactic":"Collection","desc":"Capture screen content to collect information"},
        ]
        self._build_embeddings()

    def _ensure_db(self):
        os.makedirs(self.data_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS attck_mappings ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "ts TEXT,"
                "message TEXT,"
                "tactic TEXT,"
                "technique_id TEXT,"
                "technique_name TEXT,"
                "score REAL)"
            )
            conn.commit()
        finally:
            conn.close()

    def _build_embeddings(self):
        texts = [t["name"] + " " + t["desc"] for t in self.techniques]
        self.tech_vecs = None
        if self.embedder.available:
            self.tech_vecs = self.embedder.encode(texts)

    def map(self, message: str) -> Dict[str, str]:
        if not message:
            return {"tactic":"", "technique_id":"", "technique_name":"", "score":0.0}
        zs_res = self.zs.classify(message, self.tactics, multi_label=False)
        tactic = zs_res["labels"][0] if zs_res["labels"] else ""
        candidates = [t for t in self.techniques if t["tactic"] == tactic] or self.techniques
        best = candidates[0]
        best_score = 0.0
        if self.tech_vecs is not None:
            corpus_idx = [self.techniques.index(t) for t in candidates]
            import torch
            q = self.embedder.encode([message])
            sims = (q @ self.tech_vecs.T).squeeze(0)
            scores = [(float(sims[i].item()), self.techniques[i]) for i in corpus_idx]
            scores.sort(key=lambda x: x[0], reverse=True)
            if scores:
                best_score, best = scores[0]
        else:
            lower = message.lower()
            heuristic = []
            for t in candidates:
                hits = sum(1 for w in t["name"].lower().split() if w in lower) + sum(1 for w in t["desc"].lower().split() if w in lower)
                heuristic.append((hits, t))
            heuristic.sort(key=lambda x: x[0], reverse=True)
            if heuristic:
                best_score = float(heuristic[0][0]) / 5.0
                best = heuristic[0][1]
        self._store(message, tactic, best["id"], best["name"], best_score)
        return {"tactic": tactic, "technique_id": best["id"], "technique_name": best["name"], "score": best_score}

    def _store(self, message: str, tactic: str, tech_id: str, tech_name: str, score: float):
        conn = sqlite3.connect(self.db_path)
        try:
            ts = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO attck_mappings (ts,message,tactic,technique_id,technique_name,score) VALUES (?,?,?,?,?,?)",
                (ts, message, tactic, tech_id, tech_name, score)
            )
            conn.commit()
        finally:
            conn.close()

    def history(self, limit: int = 20) -> List[Dict[str, str]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute("SELECT ts,message,tactic,technique_id,technique_name,score FROM attck_mappings ORDER BY id DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            out = []
            for ts, msg, tac, tid, tname, sc in rows:
                out.append({"ts": ts, "message": msg, "tactic": tac, "technique_id": tid, "technique_name": tname, "score": sc})
            return out
        finally:
            conn.close()

import re
import requests
import base64

class NVIDIAQwenChatbot:
    """NVIDIA-powered chatbot using Qwen 3.5 model."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "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")
        self.invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.model = os.getenv("NVIDIA_MODEL", "qwen/qwen3.5-397b-a17b")

    def generate_response(self, prompt: str, stream: bool = False):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream" if stream else "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16384,
            "temperature": 0.60,
            "top_p": 0.95,
            "top_k": 20,
            "presence_penalty": 0,
            "repetition_penalty": 1,
            "stream": stream,
            "chat_template_kwargs": {"enable_thinking": True},
        }
        try:
            response = requests.post(self.invoke_url, headers=headers, json=payload, stream=stream, timeout=60)
            response.raise_for_status()
            if stream:
                # Return a generator for streaming
                def response_generator():
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode("utf-8")
                            if decoded_line.startswith("data: "):
                                data_str = decoded_line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                                except:
                                    continue
                return response_generator()
            else:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "No response generated.")
        except Exception as e:
            logger.error(f"NVIDIA API Error: {e}")
            return f"Error: {str(e)}"

class SOCReportGenerator:
    def __init__(self, clf: DistilBERTLogClassifier, attck: MITREAttckMapper, llm_client: Optional['NVIDIAQwenChatbot'] = None):
        self.available = False
        self.generator = None
        self.tokenizer = None
        self.clf = clf
        self.attck = attck
        self.llm_client = llm_client
        if _LIGHT_MODE:
            return
        try:
            if _HAS_TRANSFORMERS and BitsAndBytesConfig is not None:
                use_gpu = bool(torch.cuda.is_available())
                if use_gpu:
                    cfg = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                    )
                    self.tokenizer = AutoTokenizer.from_pretrained(get_model_path("meta-llama/Meta-Llama-3-8B-Instruct"))
                    self.model = AutoModelForCausalLM.from_pretrained(
                        get_model_path("meta-llama/Meta-Llama-3-8B-Instruct"),
                        quantization_config=cfg,
                        device_map="auto",
                    )
                    from transformers import pipeline as genpipe
                    self.generator = genpipe("text-generation", model=self.model, tokenizer=self.tokenizer, max_new_tokens=800)
                    self.available = True
        except Exception:
            self.available = False
            self.generator = None
            self.tokenizer = None

    def _prompt(self, logs: List[str], title: str | None = None):
        header = f"Generate a SOC Incident Report{'' if not title else f': {title}'}"
        body = "\n".join([f"- {l}" for l in logs if l])
        return (
            header + "\n\n"
            "Sections:\n"
            "1) Incident Summary\n"
            "2) Root Cause\n"
            "3) Impact Assessment\n"
            "4) Remediation Steps\n"
            "5) Executive Summary\n\n"
            "Log Events:\n" + body + "\n\n"
            "Write a concise, professional report suitable for SOC and executive stakeholders."
        )

    def generate(self, logs: List[str], title: str | None = None):
        prompt = self._prompt(logs, title)
        
        # 1. Try NVIDIA Qwen (Highest Quality)
        if self.llm_client:
            try:
                report = self.llm_client.generate_response(prompt, stream=False)
                if report and not report.startswith("Error:"):
                    return {"report": report.strip(), "model": self.llm_client.model}
            except Exception as e:
                logger.error(f"NVIDIA SOC Report failed: {e}")

        # 2. Try Local Llama-3 (Fallback)
        if self.available and self.generator:
            out = self.generator(prompt, do_sample=True, temperature=0.2, top_p=0.9)
            if isinstance(out, list) and out:
                text = out[0].get("generated_text", "")
            else:
                text = str(out)
            return {"report": text.strip(), "model": "Meta-Llama-3-8B-Instruct"}
        
        # 3. Last Resort (Static Fallback)
        return self.fallback(logs, title)

    def fallback(self, logs: List[str], title: str | None = None):
        lines = [l for l in logs if l]
        severities = [self.clf.classify_severity(l)[0] for l in lines]
        threats = [self.clf.predict_threat_type(l)[0] for l in lines]
        attck_maps = [self.attck.map(l) for l in lines]
        sev_counts: Dict[str,int] = {}
        thr_counts: Dict[str,int] = {}
        for s in severities: sev_counts[s] = sev_counts.get(s,0)+1
        for t in threats: thr_counts[t] = thr_counts.get(t,0)+1
        top_sev = sorted(sev_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        top_thr = sorted(thr_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        techs = [m["technique_id"]+" "+m["technique_name"] for m in attck_maps if m.get("technique_id")]
        techs_dedup = []
        seen = set()
        for t in techs:
            if t not in seen:
                seen.add(t)
                techs_dedup.append(t)
        summary = (
            f"Incident Summary:\n"
            f"- Events analyzed: {len(lines)}\n"
            f"- Dominant severities: {', '.join([f'{s}({c})' for s,c in top_sev]) or 'N/A'}\n"
            f"- Dominant threats: {', '.join([f'{t}({c})' for t,c in top_thr]) or 'N/A'}\n"
            f"- ATT&CK techniques: {', '.join(techs_dedup) or 'N/A'}\n\n"
            f"Root Cause:\n"
            f"- Based on observed patterns, probable cause relates to top threats: {', '.join([t for t,_ in top_thr]) or 'N/A'}.\n"
            f"- Review affected systems and authentication flows for anomalies.\n\n"
            f"Impact Assessment:\n"
            f"- Potential impact includes service disruption, credential exposure, or unauthorized access.\n"
            f"- Severity distribution indicates risk concentration in: {', '.join([s for s,_ in top_sev]) or 'N/A'}.\n\n"
            f"Remediation Steps:\n"
            f"- Contain affected accounts and rotate credentials.\n"
            f"- Patch vulnerable services and harden perimeter configurations.\n"
            f"- Enhance monitoring rules for detected ATT&CK techniques.\n"
            f"- Run post-incident forensic analysis and update IR playbooks.\n\n"
            f"Executive Summary:\n"
            f"- A set of {len(lines)} events indicate heightened {', '.join([t for t,_ in top_thr]) or 'risk'} activity.\n"
            f"- Immediate containment and remediation actions recommended to mitigate exposure.\n"
        )
        title_line = f"Title: {title}\n\n" if title else ""
        return {"report": title_line + summary, "model": "fallback-template"}

class CVEFetcher:
    def __init__(self):
        self.session = None
        try:
            import requests
            self.session = requests.Session()
        except Exception:
            self.session = None

    def fetch(self, cve_id: str) -> Dict[str, str]:
        title = ""
        desc = ""
        cvss = None
        severity = ""
        method = ""
        fix = ""
        if self.session:
            try:
                url = f"https://services.nvd.nist.gov/rest/json/cve/2.0?cveId={cve_id}"
                r = self.session.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("vulnerabilities") or data.get("cveItems") or []
                    if items:
                        c = items[0]
                        node = c.get("cve", {})
                        title = node.get("titles",[{}])[0].get("title","") if node.get("titles") else ""
                        descs = node.get("descriptions") or []
                        if descs:
                            desc = descs[0].get("value","")
                        metrics = c.get("cve", {}).get("metrics") or c.get("metrics") or {}
                        for key in ["cvssMetricV31","cvssMetricV30","cvssMetricV2"]:
                            arr = metrics.get(key) or []
                            if arr:
                                cv = arr[0].get("cvssData") or arr[0].get("cvssData",{})
                                cvss = cv.get("baseScore")
                                severity = (cv.get("baseSeverity") or cv.get("severity") or "").upper()
                                break
            except Exception:
                pass
        lower = (title + " " + desc).lower()
        if not method:
            if "sql" in lower or "injection" in lower: method = "SQL Injection"
            elif "xss" in lower or "cross-site scripting" in lower: method = "XSS"
            elif "buffer overflow" in lower: method = "Buffer Overflow"
            elif "rce" in lower or "remote code execution" in lower: method = "RCE"
        if not fix:
            fix = "Apply vendor patch, update dependencies, and mitigate via configuration hardening."
        return {
            "id": cve_id,
            "title": title,
            "description": desc,
            "cvss": cvss if cvss is not None else 0.0,
            "severity": severity or "UNKNOWN",
            "method": method or "UNKNOWN",
            "fix": fix,
        }

class CVERAGEngine:
    def __init__(self, embedder: MiniLMEmbedder, llm_client: Optional['NVIDIAQwenChatbot'] = None):
        self.embedder = embedder
        self.fetcher = CVEFetcher()
        self.llm_client = llm_client
        self.records: List[Dict[str,str]] = []
        self.index = None
        self.dim = None
        if _LIGHT_MODE:
            self.faiss = None
            self._init_index()
            return
        try:
            import faiss
            self.faiss = faiss
        except Exception:
            self.faiss = None
        self._init_index()

    def _init_index(self):
        if self.embedder.available:
            vec = self.embedder.encode(["init"])
            if vec is not None:
                import torch
                v = vec[0].detach().cpu().numpy().astype("float32")
                self.dim = v.shape[-1]
        if self.faiss is not None and self.dim:
            self.index = self.faiss.IndexFlatIP(self.dim)

    def _embed_text(self, text: str):
        v = self.embedder.encode([text])
        if v is None:
            return None
        import torch
        return v.detach().cpu().numpy().astype("float32")

    def _extract_ids(self, text: str) -> List[str]:
        ids = re.findall(r"CVE-\d{4}-\d{4,7}", text, flags=re.IGNORECASE)
        return [i.upper() for i in ids]

    def ingest_from_log(self, message: str) -> List[Dict[str,str]]:
        ids = self._extract_ids(message)
        out = []
        for cid in ids:
            rec = self.fetcher.fetch(cid)
            text = f"{rec['id']} {rec['title']} {rec['description']}"
            vec = self._embed_text(text)
            if vec is not None and self.index is not None:
                self.index.add(vec)
                self.records.append(rec)
            out.append(rec)
        return out

    def search(self, query: str, top_k: int = 5):
        if self.index is None or not self.records:
            return []
        vec = self._embed_text(query)
        if vec is None:
            return []
        D, I = self.index.search(vec, top_k)
        results = []
        for score, idx in zip(D[0].tolist(), I[0].tolist()):
            if idx < 0 or idx >= len(self.records):
                continue
            rec = self.records[idx].copy()
            rec["score"] = float(score)
            results.append(rec)
        return results

    def explain_cve(self, cve_id: str, rec: Dict[str, Any] | None = None) -> str:
        """Provide an AI-powered explanation for a given CVE."""
        if not rec:
            rec = self.fetcher.fetch(cve_id)
        
        prompt = (
            f"Explain the following CVE for a SOC analyst:\n\n"
            f"ID: {rec['id']}\n"
            f"Title: {rec['title']}\n"
            f"Description: {rec['description']}\n"
            f"CVSS: {rec['cvss']}\n"
            f"Severity: {rec['severity']}\n"
            f"Exploitation Method: {rec['method']}\n"
            f"Fix Recommendation: {rec['fix']}\n\n"
            f"Provide a concise summary covering:\n"
            f"- What the vulnerability is\n"
            f"- Likely exploitation path\n"
            f"- Operational impact\n"
            f"- Remediation steps\n"
        )
        
        if self.llm_client:
            try:
                explanation = self.llm_client.generate_response(prompt, stream=False)
                if explanation and not explanation.startswith("Error:"):
                    return explanation.strip()
            except Exception as e:
                logger.error(f"NVIDIA CVE Explanation failed: {e}")
        
        # Static Fallback
        return (
            f"{rec['id']} ({rec['severity']}): {rec['title']}\n"
            f"- Summary: {rec['description'][:400]}...\n"
            f"- CVSS: {rec['cvss']} | Method: {rec['method']}\n"
            f"- Fix: {rec['fix']}\n"
        )

class TrendStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        conn = self._conn()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS log_events ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "ts TEXT,"
                "message TEXT,"
                "severity TEXT,"
                "threat_type TEXT,"
                "risk REAL)"
            )
            conn.commit()
        finally:
            conn.close()

    def record_event(self, message: str, severity: str, threat_type: str, risk: float):
        conn = self._conn()
        try:
            ts = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO log_events (ts,message,severity,threat_type,risk) VALUES (?,?,?,?,?)",
                (ts, message, severity, threat_type, risk)
            )
            conn.commit()
        finally:
            conn.close()
    def top_attack_types(self, limit: int = 10):
        conn = self._conn()
        try:
            cur = conn.execute(
                "SELECT threat_type, COUNT(*) as cnt FROM log_events WHERE threat_type IS NOT NULL AND threat_type <> '' GROUP BY threat_type ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            rows = cur.fetchall()
            return [{"threat_type": r[0], "count": int(r[1])} for r in rows]
        finally:
            conn.close()
    def attack_frequency(self, bucket: str = "hour", limit: int = 24):
        conn = self._conn()
        try:
            cur = conn.execute("SELECT ts FROM log_events ORDER BY id DESC")
            rows = cur.fetchall()
            from collections import Counter
            counts = Counter()
            for (ts,) in rows:
                dt = datetime.fromisoformat(ts)
                if bucket == "hour":
                    key = dt.strftime("%Y-%m-%d %H:00")
                elif bucket == "day":
                    key = dt.strftime("%Y-%m-%d")
                else:
                    key = dt.strftime("%Y-%m-%d %H:00")
                counts[key] += 1
            items = [{"time": k, "count": v} for k, v in sorted(counts.items())][-limit:]
            return items
        finally:
            conn.close()
    def mitre_distribution(self, limit: int = 15):
        conn = self._conn()
        try:
            cur = conn.execute(
                "SELECT technique_id, technique_name, COUNT(*) as cnt FROM attck_mappings GROUP BY technique_id, technique_name ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            rows = cur.fetchall()
            return [{"technique_id": r[0], "technique_name": r[1], "count": int(r[2])} for r in rows]
        finally:
            conn.close()
    def mitre_table(self, limit: int = 20):
        conn = self._conn()
        try:
            cur = conn.execute(
                "SELECT tactic, technique_id, COUNT(*) as cnt FROM attck_mappings GROUP BY tactic, technique_id ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            rows = cur.fetchall()
            return [{"tactic": r[0], "technique_id": r[1], "count": int(r[2])} for r in rows]
        finally:
            conn.close()
    def risk_trends(self, bucket: str = "day", limit: int = 14):
        conn = self._conn()
        try:
            cur = conn.execute("SELECT ts, risk FROM log_events ORDER BY id ASC")
            rows = cur.fetchall()
            from collections import defaultdict
            agg = defaultdict(list)
            for ts, risk in rows:
                dt = datetime.fromisoformat(ts)
                key = dt.strftime("%Y-%m-%d") if bucket == "day" else dt.strftime("%Y-%m-%d %H:00")
                agg[key].append(float(risk or 0.0))
            items = []
            for k in sorted(agg.keys()):
                vals = agg[k]
                avg = sum(vals)/max(1,len(vals))
                items.append({"time": k, "avg_risk": avg})
            return items[-limit:]
        finally:
            conn.close()
    def frequency_for_threat(self, threat_type: str, hours: int = 24):
        conn = self._conn()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            cur = conn.execute("SELECT ts FROM log_events WHERE threat_type=? ORDER BY id DESC", (threat_type,))
            rows = cur.fetchall()
            cnt = 0
            for (ts,) in rows:
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    continue
                if dt >= cutoff:
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def recent_messages(self, limit: int = 200):
        conn = self._conn()
        try:
            cur = conn.execute("SELECT message FROM log_events ORDER BY id DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
    def recent_events(self, limit: int = 50):
        conn = self._conn()
        try:
            cur = conn.execute("SELECT ts,message,severity,threat_type,risk FROM log_events ORDER BY id DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            out = []
            for ts, msg, sev, thr, risk in rows:
                out.append({"ts": ts, "message": msg, "severity": sev, "threat_type": thr, "risk": float(risk or 0.0)})
            return out
        finally:
            conn.close()
    def alerts_today(self):
        conn = self._conn()
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cur = conn.execute("SELECT ts,severity FROM log_events")
            rows = cur.fetchall()
            cnt = 0
            for ts, sev in rows:
                if ts.startswith(today) and (sev or "").lower() in ("high","critical"):
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def critical_today(self):
        conn = self._conn()
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cur = conn.execute("SELECT ts,severity FROM log_events")
            rows = cur.fetchall()
            cnt = 0
            for ts, sev in rows:
                if ts.startswith(today) and (sev or "").lower() == "critical":
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def average_risk_today(self):
        conn = self._conn()
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cur = conn.execute("SELECT ts,risk FROM log_events")
            rows = cur.fetchall()
            vals = []
            for ts, risk in rows:
                if ts.startswith(today):
                    vals.append(float(risk or 0.0))
            if not vals:
                return 0.0
            return sum(vals)/len(vals)
        finally:
            conn.close()

class PGTrendStore:
    def __init__(self, dsn: str):
        import psycopg2
        self.psycopg2 = psycopg2
        self.dsn = dsn
        self._ensure_tables()

    def _conn(self):
        return self.psycopg2.connect(self.dsn)

    def _ensure_tables(self):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS log_events ("
                "id SERIAL PRIMARY KEY,"
                "ts TEXT,"
                "message TEXT,"
                "severity TEXT,"
                "threat_type TEXT,"
                "risk REAL)"
            )
            conn.commit()
        finally:
            conn.close()

    def record_event(self, message: str, severity: str, threat_type: str, risk: float):
        conn = self._conn()
        try:
            ts = datetime.utcnow().isoformat()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO log_events (ts,message,severity,threat_type,risk) VALUES (%s,%s,%s,%s,%s)",
                (ts, message, severity, threat_type, risk)
            )
            conn.commit()
        finally:
            conn.close()

    def top_attack_types(self, limit: int = 10):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT threat_type, COUNT(*) as cnt FROM log_events WHERE threat_type IS NOT NULL AND threat_type <> '' GROUP BY threat_type ORDER BY cnt DESC LIMIT %s",
                (limit,)
            )
            rows = cur.fetchall()
            return [{"threat_type": r[0], "count": int(r[1])} for r in rows]
        finally:
            conn.close()

    def attack_frequency(self, bucket: str = "hour", limit: int = 24):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT ts FROM log_events ORDER BY id DESC")
            rows = cur.fetchall()
            from collections import Counter
            counts = Counter()
            for r in rows:
                ts = r[0]
                dt = datetime.fromisoformat(ts)
                if bucket == "hour":
                    key = dt.strftime("%Y-%m-%d %H:00")
                elif bucket == "day":
                    key = dt.strftime("%Y-%m-%d")
                else:
                    key = dt.strftime("%Y-%m-%d %H:00")
                counts[key] += 1
            items = [{"time": k, "count": v} for k, v in sorted(counts.items())][-limit:]
            return items
        finally:
            conn.close()

    def mitre_distribution(self, limit: int = 15):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT technique_id, technique_name, COUNT(*) as cnt FROM attck_mappings GROUP BY technique_id, technique_name ORDER BY cnt DESC LIMIT %s",
                (limit,)
            )
            rows = cur.fetchall()
            return [{"technique_id": r[0], "technique_name": r[1], "count": int(r[2])} for r in rows]
        finally:
            conn.close()

    def risk_trends(self, bucket: str = "day", limit: int = 14):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT ts, risk FROM log_events ORDER BY id ASC")
            rows = cur.fetchall()
            from collections import defaultdict
            agg = defaultdict(list)
            for ts, risk in rows:
                dt = datetime.fromisoformat(ts)
                key = dt.strftime("%Y-%m-%d") if bucket == "day" else dt.strftime("%Y-%m-%d %H:00")
                agg[key].append(float(risk or 0.0))
            items = []
            for k in sorted(agg.keys()):
                vals = agg[k]
                avg = sum(vals)/max(1,len(vals))
                items.append({"time": k, "avg_risk": avg})
            return items[-limit:]
        finally:
            conn.close()

    def frequency_for_threat(self, threat_type: str, hours: int = 24):
        conn = self._conn()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            cur = conn.cursor()
            cur.execute("SELECT ts FROM log_events WHERE threat_type=%s ORDER BY id DESC", (threat_type,))
            rows = cur.fetchall()
            cnt = 0
            for r in rows:
                ts = r[0]
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    continue
                if dt >= cutoff:
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def recent_messages(self, limit: int = 200):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT message FROM log_events ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
    def recent_events(self, limit: int = 50):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT ts,message,severity,threat_type,risk FROM log_events ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            out = []
            for r in rows:
                out.append({"ts": r[0], "message": r[1], "severity": r[2], "threat_type": r[3], "risk": float(r[4] or 0.0)})
            return out
        finally:
            conn.close()
    def alerts_today(self):
        conn = self._conn()
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cur = conn.cursor()
            cur.execute("SELECT ts,severity FROM log_events")
            rows = cur.fetchall()
            cnt = 0
            for ts, sev in rows:
                if ts.startswith(today) and (sev or "").lower() in ("high","critical"):
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def critical_today(self):
        conn = self._conn()
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cur = conn.cursor()
            cur.execute("SELECT ts,severity FROM log_events")
            rows = cur.fetchall()
            cnt = 0
            for ts, sev in rows:
                if ts.startswith(today) and (sev or "").lower() == "critical":
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def average_risk_today(self):
        conn = self._conn()
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            cur = conn.cursor()
            cur.execute("SELECT ts,risk FROM log_events")
            rows = cur.fetchall()
            vals = []
            for ts, risk in rows:
                if ts.startswith(today):
                    vals.append(float(risk or 0.0))
            if not vals:
                return 0.0
            return sum(vals)/len(vals)
        finally:
            conn.close()

class AnomalyEngine:
    def __init__(self, embedder: MiniLMEmbedder, store):
        self.embedder = embedder
        self.store = store
        self.model = None
        self._HAS_SK = False
        try:
            from sklearn.ensemble import IsolationForest
            self._HAS_SK = True
            self._IsolationForest = IsolationForest
        except Exception:
            self._HAS_SK = False

    def fit(self, limit: int = 300):
        if not self._HAS_SK:
            self.model = None
            return
        msgs = self.store.recent_messages(limit)
        if not msgs:
            self.model = None
            return
        vecs = [self.embedder.embed(m) for m in msgs]
        import numpy as np
        X = np.array(vecs, dtype=np.float32)
        model = self._IsolationForest(n_estimators=100, contamination="auto", random_state=42)
        model.fit(X)
        self.model = model

    def score(self, message: str):
        if not self._HAS_SK or not self.model:
            return 0.0
        import numpy as np
        v = np.array([self.embedder.embed(message)], dtype=np.float32)
        # decision_function: higher is normal, lower is anomaly; typically [-0.5, 0.5]
        df = float(self.model.decision_function(v)[0])
        # convert to 0..1 anomaly: 1 => most anomalous
        # scale: anomaly = sigmoid(-df * 4)
        import math
        anomaly = 1.0 / (1.0 + math.exp(df * 4.0))
        return max(0.0, min(anomaly, 1.0))

class RiskScoringEngine:
    def __init__(self, clf: DistilBERTLogClassifier, cve_engine: CVERAGEngine, store, embedder: MiniLMEmbedder):
        self.clf = clf
        self.cve_engine = cve_engine
        self.store = store
        self.anomaly = AnomalyEngine(embedder, store)
        self.NORMALIZATION = 1.0

    def _severity_weight(self, label: str, score: float):
        mapping = {
            "info": 0.1,
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "critical": 0.9
        }
        base = mapping.get((label or "").lower(), 0.25)
        s = max(min(score or base, 1.0), 0.0)
        return max(base, s)

    def _cvss_norm(self, message: str):
        ids = re.findall(r"CVE-\d{4}-\d{4,7}", message, flags=re.IGNORECASE)
        if not ids:
            return 0.5
        cid = ids[0].upper()
        try:
            rec = self.cve_engine.fetcher.fetch(cid)
            sc = float(rec.get("cvss", 5.0))
        except Exception:
            sc = 5.0
        return max(0.0, min(sc/10.0, 1.0))

    def _frequency_norm(self, threat_type: str, hours: int = 24):
        count = self.store.frequency_for_threat(threat_type or "", hours=hours)
        return max(0.0, min(count/50.0, 1.0))

    def score(self, message: str, asset_value: float | None = None):
        try:
            self.anomaly.fit(300)
        except Exception:
            pass
        sev, s_score = self.clf.classify_severity(message)
        thr, _ = self.clf.predict_threat_type(message)
        sev_w = self._severity_weight(sev, s_score)
        freq_n = self._frequency_norm(thr, 24)
        cvss_n = self._cvss_norm(message)
        av = asset_value if isinstance(asset_value, (int, float)) else 0.5
        av = max(0.0, min(float(av), 1.0))
        risk = (sev_w * freq_n * cvss_n * av) / max(self.NORMALIZATION, 1e-6)
        anom = 0.0
        try:
            anom = self.anomaly.score(message)
        except Exception:
            anom = 0.0
        risk_score = max(0.0, min(risk * 100.0, 100.0))
        boost_factor = 1.0 + (anom)  # isolation forest anomaly boost up to 2x
        risk_score_adj = max(0.0, min(risk_score * boost_factor, 100.0))
        label = "Low"
        if risk_score_adj >= 76:
            label = "Critical"
        elif risk_score_adj >= 51:
            label = "High"
        elif risk_score_adj >= 26:
            label = "Medium"
        return {
            "severity": sev,
            "threat_type": thr,
            "frequency": int(self.store.frequency_for_threat(thr, 24)),
            "asset_value": av,
            "cvss": cvss_n,
            "risk_score_base": risk_score,
            "anomaly_score": anom,
            "risk_score": risk_score_adj,
            "risk_label": label
        }

class PipelineEngine:
    def __init__(self, clf: DistilBERTLogClassifier, embedder: MiniLMEmbedder, index: InMemoryVectorIndex, attck: MITREAttckMapper, cve: CVERAGEngine, risk: RiskScoringEngine, soc: SOCReportGenerator):
        self.clf = clf
        self.embedder = embedder
        self.index = index
        self.attck = attck
        self.cve = cve
        self.risk = risk
        self.soc = soc

    def run(self, message: str, asset_value: float | None = None, ingest: bool = True, soc_report: bool = False, title: str | None = None):
        sev, s_score = self.clf.classify_severity(message)
        thr, t_score = self.clf.predict_threat_type(message)
        emb = self.embedder.encode([message])
        added = 0
        if ingest:
            added = self.index.add([message])
        mapping = self.attck.map(message)
        ids = self.cve._extract_ids(message)
        enriched = []
        for cid in ids:
            info = self.cve.fetcher.fetch(cid)
            if info:
                enriched.append(info)
        risk = self.risk.score(message, asset_value)
        report = None
        if soc_report:
            report = self.soc.generate([message], title or None)
        return {
            "severity": {"label": sev, "score": s_score},
            "threat_type": {"label": thr, "score": t_score},
            "embedding_added": added,
            "attck_mapping": mapping,
            "cve_enriched": enriched,
            "risk": risk,
            "soc_report": report["report"] if report else None
        }

    def top_attack_types(self, limit: int = 10):
        conn = self._conn()
        try:
            cur = conn.execute(
                "SELECT threat_type, COUNT(*) as cnt FROM log_events WHERE threat_type IS NOT NULL AND threat_type <> '' GROUP BY threat_type ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            return [{"threat_type": t, "count": int(c)} for (t, c) in cur.fetchall()]
        finally:
            conn.close()

    def attack_frequency(self, bucket: str = "hour", limit: int = 24):
        conn = self._conn()
        try:
            rows = conn.execute("SELECT ts FROM log_events ORDER BY id DESC").fetchall()
            from collections import Counter
            counts = Counter()
            for (ts,) in rows:
                dt = datetime.fromisoformat(ts)
                if bucket == "hour":
                    key = dt.strftime("%Y-%m-%d %H:00")
                elif bucket == "day":
                    key = dt.strftime("%Y-%m-%d")
                else:
                    key = dt.strftime("%Y-%m-%d %H:00")
                counts[key] += 1
            items = [{"time": k, "count": v} for k, v in sorted(counts.items())][-limit:]
            return items
        finally:
            conn.close()

    def mitre_distribution(self, limit: int = 15):
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "SELECT technique_id, technique_name, COUNT(*) as cnt FROM attck_mappings GROUP BY technique_id, technique_name ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            return [{"technique_id": tid, "technique_name": tn, "count": int(c)} for (tid, tn, c) in cur.fetchall()]
        finally:
            conn.close()

    def risk_trends(self, bucket: str = "day", limit: int = 14):
        conn = self._conn()
        try:
            rows = conn.execute("SELECT ts, risk FROM log_events ORDER BY id ASC").fetchall()
            from collections import defaultdict
            agg = defaultdict(list)
            for ts, risk in rows:
                dt = datetime.fromisoformat(ts)
                key = dt.strftime("%Y-%m-%d") if bucket == "day" else dt.strftime("%Y-%m-%d %H:00")
                agg[key].append(float(risk or 0.0))
            items = []
            for k in sorted(agg.keys()):
                vals = agg[k]
                avg = sum(vals)/max(1,len(vals))
                items.append({"time": k, "avg_risk": avg})
            return items[-limit:]
        finally:
            conn.close()

    def frequency_for_threat(self, threat_type: str, hours: int = 24):
        conn = self._conn()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            rows = conn.execute("SELECT ts FROM log_events WHERE threat_type=? ORDER BY id DESC", (threat_type,)).fetchall()
            cnt = 0
            for (ts,) in rows:
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    continue
                if dt >= cutoff:
                    cnt += 1
            return cnt
        finally:
            conn.close()
    def recent_messages(self, limit: int = 200):
        conn = self._conn()
        try:
            cur = conn.execute("SELECT message FROM log_events ORDER BY id DESC LIMIT ?", (limit,))
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def classify_url(self, url: str):
        if not url:
            return {"label": "not_phishing", "score": 0.0}
        text = url
        lower = url.lower()
        suspicious = 0
        suspicious += 1 if "xn--" in lower else 0
        suspicious += 1 if "@" in lower else 0
        suspicious += 1 if lower.startswith("http://") else 0
        suspicious += 1 if lower.count("-") >= 4 else 0
        suspicious += 1 if any(t in lower for t in [".zip", ".rar", ".exe"]) else 0
        if self.available:
            res = self.classify_text(text)
            score = max(res["score"], min(1.0, suspicious / 4.0))
            label = "phishing" if score > 0.5 else "not_phishing"
            return {"label": label, "score": score}
        score = min(1.0, suspicious / 4.0)
        return {"label": "phishing" if score > 0.5 else "not_phishing", "score": score}
