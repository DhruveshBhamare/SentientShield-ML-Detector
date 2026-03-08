from typing import Dict, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from ..core.security import auth_dependency
import os
from ..services.log_service import DistilBERTLogClassifier, MiniLMEmbedder, InMemoryVectorIndex, FaissVectorIndex, ZeroShotThreatClassifier, PhishingDetector, MITREAttckMapper, SOCReportGenerator, CVERAGEngine, TrendStore, PGTrendStore, RiskScoringEngine, PipelineEngine, NVIDIAQwenChatbot

router = APIRouter(prefix="/api/logs", tags=["Logs"])
_clf = DistilBERTLogClassifier()
_embedder = MiniLMEmbedder()
try:
    _index = FaissVectorIndex(_embedder)
    if _index.index is None:
        _index = InMemoryVectorIndex(_embedder)
except Exception:
    _index = InMemoryVectorIndex(_embedder)
_zs = ZeroShotThreatClassifier()
_phish = PhishingDetector()
_attck = MITREAttckMapper(_zs, _embedder)
_soc = SOCReportGenerator(_clf, _attck)
_cve = CVERAGEngine(_embedder)
_trend = PGTrendStore(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else TrendStore(_attck.db_path)
_risk = RiskScoringEngine(_clf, _cve, _trend, _embedder)
_pipe = PipelineEngine(_clf, _embedder, _index, _attck, _cve, _risk, _soc)
_nvidia_bot = NVIDIAQwenChatbot()

class LogRequest(BaseModel):
    message: str = Field(..., description="Log message text")
    context: Optional[Dict] = None

@router.post("/classify-severity")
async def classify_severity(req: LogRequest, user: Dict = Depends(auth_dependency)):
    label, score = _clf.classify_severity(req.message)
    return {"severity": label, "score": score, "user": user.get("sub") or user.get("uid")}

@router.post("/predict-type")
async def predict_type(req: LogRequest, user: Dict = Depends(auth_dependency)):
    label, score = _clf.predict_threat_type(req.message)
    return {"threat_type": label, "score": score, "user": user.get("sub") or user.get("uid")}

@router.post("/filter-alert")
async def filter_alert(req: LogRequest, user: Dict = Depends(auth_dependency)):
    alert, action, score = _clf.filter_alert(req.message)
    return {"alert": alert, "action": action, "score": score, "user": user.get("sub") or user.get("uid")}

class BulkLogs(BaseModel):
    logs: list[str] = Field(default_factory=list)

@router.post("/ingest")
async def ingest(req: BulkLogs, user: Dict = Depends(auth_dependency)):
    added = _index.add(req.logs)
    return {"added": added, "total": len(_index.texts), "user": user.get("sub") or user.get("uid")}

class SimilarQuery(BaseModel):
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, ge=1, le=50)

@router.post("/similar")
async def similar(req: SimilarQuery, user: Dict = Depends(auth_dependency)):
    results = _index.search(req.query, req.top_k)
    return {"results": results, "user": user.get("sub") or user.get("uid")}

class ZeroShotRequest(BaseModel):
    message: str
    labels: list[str] | None = None
    multi_label: bool = True

@router.post("/zero-shot")
async def zero_shot(req: ZeroShotRequest, user: Dict = Depends(auth_dependency)):
    default_labels = ["SQL Injection", "DDoS", "Malware", "Privilege Escalation", "Phishing", "XSS", "RCE"]
    labels = req.labels or default_labels
    result = _zs.classify(req.message, labels, req.multi_label)
    top = labels[0] if not result["labels"] else result["labels"][0]
    top_score = 0.0 if not result["scores"] else result["scores"][0]
    return {"labels": result["labels"], "scores": result["scores"], "top_label": top, "top_score": top_score, "user": user.get("sub") or user.get("uid")}

class EmailRequest(BaseModel):
    text: str

@router.post("/phishing-email")
async def phishing_email(req: EmailRequest, user: Dict = Depends(auth_dependency)):
    res = _phish.classify_text(req.text)
    return {"label": res["label"], "score": res["score"], "user": user.get("sub") or user.get("uid")}

class URLRequest(BaseModel):
    url: str

@router.post("/phishing-url")
async def phishing_url(req: URLRequest, user: Dict = Depends(auth_dependency)):
    res = _phish.classify_url(req.url)
    return {"label": res["label"], "score": res["score"], "user": user.get("sub") or user.get("uid")}

class AttckMapRequest(BaseModel):
    message: str

@router.post("/attck-map")
async def attck_map(req: AttckMapRequest, user: Dict = Depends(auth_dependency)):
    res = _attck.map(req.message)
    return {"mapping": res, "user": user.get("sub") or user.get("uid")}

@router.get("/attck-history")
async def attck_history(limit: int = 20, user: Dict = Depends(auth_dependency)):
    items = _attck.history(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

class SocReportRequest(BaseModel):
    logs: list[str] = Field(default_factory=list)
    title: str | None = None

@router.post("/soc-report")
async def soc_report(req: SocReportRequest, user: Dict = Depends(auth_dependency)):
    try:
        # Prepare the custom SOC report prompt for NVIDIA Qwen
        prompt = _soc._prompt(req.logs, req.title)
        report = _nvidia_bot.generate_response(prompt, stream=False)
        return {"report": report, "model": _nvidia_bot.model, "user": user.get("sub") or user.get("uid")}
    except Exception as e:
        logger.error(f"NVIDIA SOC Report failed: {e}")
        res = _soc.generate(req.logs, req.title)
        return {"report": res["report"], "model": res["model"], "user": user.get("sub") or user.get("uid"), "fallback": True}

class CveEnrichRequest(BaseModel):
    message: str

@router.post("/cve-enrich")
async def cve_enrich(req: CveEnrichRequest, user: Dict = Depends(auth_dependency)):
    items = _cve.ingest_from_log(req.message)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

class CveSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)

@router.post("/cve-search")
async def cve_search(req: CveSearchRequest, user: Dict = Depends(auth_dependency)):
    results = _cve.search(req.query, req.top_k)
    return {"results": results, "user": user.get("sub") or user.get("uid")}

class CveExplainRequest(BaseModel):
    message: str = Field(..., description="Text containing CVE ID (e.g., CVE-2024-12345)")

@router.post("/cve-explain")
async def cve_explain(req: CveExplainRequest, user: Dict = Depends(auth_dependency)):
    items = _cve.ingest_from_log(req.message)
    rec = items[0] if items else None
    if not rec:
        return {"explanation": "", "error": "No CVE found", "user": user.get("sub") or user.get("uid")}
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
    explanation = ""
    try:
        explanation = _nvidia_bot.generate_response(prompt, stream=False)
    except Exception as e:
        logger.error(f"NVIDIA CVE Explanation failed: {e}")
        if getattr(_soc, "available", False) and getattr(_soc, "generator", None):
            out = _soc.generator(prompt, do_sample=True, temperature=0.2, top_p=0.9, max_new_tokens=400)
            if isinstance(out, list) and out:
                explanation = out[0].get("generated_text", "").strip()
            else:
                explanation = str(out).strip()
        else:
            explanation = (
                f"{rec['id']} ({rec['severity']}): {rec['title']}\n"
                f"- Summary: {rec['description'][:400]}...\n"
                f"- CVSS: {rec['cvss']} | Method: {rec['method']}\n"
                f"- Fix: {rec['fix']}\n"
            )
    return {"explanation": explanation, "cve": rec, "user": user.get("sub") or user.get("uid"), "model": _nvidia_bot.model if not explanation.startswith("CVE-") else "fallback"}

class RecordEventRequest(BaseModel):
    message: str

@router.post("/record-event")
async def record_event(req: RecordEventRequest, user: Dict = Depends(auth_dependency)):
    sev, s_score = _clf.classify_severity(req.message)
    thr, t_score = _clf.predict_threat_type(req.message)
    risk = max(s_score, t_score)
    _trend.record_event(req.message, sev, thr, risk)
    _attck.map(req.message)
    return {"severity": sev, "threat_type": thr, "risk": risk, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/top-attack-types")
async def top_attack_types(limit: int = 10, user: Dict = Depends(auth_dependency)):
    items = _trend.top_attack_types(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/attack-frequency")
async def attack_frequency(bucket: str = "hour", limit: int = 24, user: Dict = Depends(auth_dependency)):
    items = _trend.attack_frequency(bucket=bucket, limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/mitre-distribution")
async def mitre_distribution(limit: int = 15, user: Dict = Depends(auth_dependency)):
    items = _trend.mitre_distribution(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/mitre-table")
async def mitre_table(limit: int = 20, user: Dict = Depends(auth_dependency)):
    items = _trend.mitre_table(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/risk-trends")
async def risk_trends(bucket: str = "day", limit: int = 14, user: Dict = Depends(auth_dependency)):
    items = _trend.risk_trends(bucket=bucket, limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

class RiskScoreRequest(BaseModel):
    message: str
    asset_value: float | None = None

@router.post("/risk-score")
async def risk_score(req: RiskScoreRequest, user: Dict = Depends(auth_dependency)):
    res = _risk.score(req.message, req.asset_value)
    return {"result": res, "user": user.get("sub") or user.get("uid")}

@router.get("/events/recent")
async def recent_events(limit: int = 50, user: Dict = Depends(auth_dependency)):
    items = _trend.recent_events(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/metrics/alerts-today")
async def alerts_today(user: Dict = Depends(auth_dependency)):
    count = _trend.alerts_today()
    return {"count": count, "user": user.get("sub") or user.get("uid")}

@router.get("/metrics/critical-today")
async def critical_today(user: Dict = Depends(auth_dependency)):
    count = _trend.critical_today()
    return {"count": count, "user": user.get("sub") or user.get("uid")}

@router.get("/metrics/risk-gauge")
async def risk_gauge(user: Dict = Depends(auth_dependency)):
    avg = _trend.average_risk_today()
    return {"avg": avg, "user": user.get("sub") or user.get("uid")}

class LlmGenerateRequest(BaseModel):
    prompt: str

@router.post("/llm-generate")
async def llm_generate(req: LlmGenerateRequest, user: Dict = Depends(auth_dependency)):
    # Use the new NVIDIA Qwen chatbot for all LLM generation requests
    try:
        response = _nvidia_bot.generate_response(req.prompt, stream=False)
        return {"text": response, "user": user.get("sub") or user.get("uid"), "model": _nvidia_bot.model}
    except Exception as e:
        logger.error(f"LLM Generation failed: {e}")
        # Fallback to local generator if available
        text = ""
        if getattr(_soc, "available", False) and getattr(_soc, "generator", None):
            out = _soc.generator(req.prompt, do_sample=True, temperature=0.2, top_p=0.9, max_new_tokens=600)
            if isinstance(out, list) and out:
                text = out[0].get("generated_text", "").strip()
            else:
                text = str(out).strip()
        else:
            text = req.prompt
        return {"text": text, "user": user.get("sub") or user.get("uid"), "fallback": True}
class PipelineRunRequest(BaseModel):
    message: str
    asset_value: float | None = None
    ingest: bool = True
    soc_report: bool = False
    title: str | None = None

@router.post("/pipeline/run")
async def pipeline_run(req: PipelineRunRequest, user: Dict = Depends(auth_dependency)):
    res = _pipe.run(req.message, req.asset_value, req.ingest, req.soc_report, req.title)
    return {"result": res, "user": user.get("sub") or user.get("uid")}
