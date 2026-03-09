import os
import json
import sqlite3
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

import torch

# Mock the transformers imports if they fail
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
except ImportError:
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    pipeline = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

import faiss

from ..configs.config import ROOT_DIR, LOG_DIR

# --- Configuration ---
INTEL_DB_PATH = os.path.join(LOG_DIR, "intelligence.db")

class IntelligencePipeline:
    def __init__(self):
        # Initialize AI models (Optimized Mock Mode)
        self._initialize_pipelines()

        self.threat_labels = ["SQL Injection", "XSS", "Brute Force", "DDoS", "RCE", "Local File Inclusion", "Path Traversal"]

        # 4. FAISS for Similarity Check
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.known_threats_data = [] # Stores metadata for indexed embeddings

        # 5. MITRE Mapping (Static for enrichment)
        self.mitre_map = {
            "SQL Injection": "T1190 - Exploit Public-Facing Application",
            "XSS": "T1189 - Drive-by Compromise",
            "Brute Force": "T1110 - Brute Force",
            "DDoS": "T1498 - Network Denial of Service",
            "RCE": "T1203 - Exploitation for Client Execution",
            "Local File Inclusion": "T1083 - File and Directory Discovery",
            "Path Traversal": "T1083 - File and Directory Discovery"
        }

        # Initialize Database
        self._init_db()

    def _initialize_pipelines(self):
        """
        Initialize the AI models. In a real environment, this would load weights.
        Here we mock the results to ensure the pipeline is always functional.
        """
        print("Initializing Intelligence Pipelines (Optimized Mock Mode)...")
        self.severity_pipe = lambda x: [{"label": "POSITIVE", "score": 0.95}]
        self.threat_type_pipe = lambda x, candidate_labels: {"labels": candidate_labels, "scores": [0.8, 0.1, 0.05, 0.05]}
        self.embedding_model = None
        print("Intelligence Pipelines Ready.")

    def _init_db(self):
        conn = sqlite3.connect(INTEL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS soc_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                log_content TEXT,
                severity TEXT,
                threat_type TEXT,
                mitre_technique TEXT,
                risk_score REAL,
                soc_report TEXT,
                cve_enrichment TEXT
            )
        ''')
        conn.commit()
        conn.close()

    async def process_log(self, log_content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Full Automatic Pipeline: Log -> Severity -> Threat Type -> MITRE -> Embedding -> FAISS -> CVE -> Risk -> Llama 3 Report -> SQLite
        """
        # Step 1: Severity (DistilBERT)
        severity_res = self.severity_pipe(log_content[:512])[0]
        severity_label = "HIGH" if severity_res['score'] > 0.8 else "MEDIUM" if severity_res['score'] > 0.5 else "LOW"

        # Step 2: Threat Type (BART Zero-Shot)
        threat_res = self.threat_type_pipe(log_content[:512], candidate_labels=self.threat_labels)
        threat_type = threat_res['labels'][0]
        threat_conf = threat_res['scores'][0]

        # Step 3: MITRE Mapping
        mitre_tech = self.mitre_map.get(threat_type, "T1210 - Exploitation of Remote Services")

        # Step 4: Embedding (MiniLM - Mocked)
        if self.embedding_model:
            embedding = self.embedding_model.encode([log_content])[0]
        else:
            embedding = np.random.rand(self.dimension).astype('float32')

        # Step 5: FAISS Similarity Check
        # (For simplicity, we search. If empty, we add. In prod, you'd pre-load known patterns)
        if self.index.ntotal > 0:
            distances, indices = self.index.search(np.array([embedding]).astype('float32'), 1)
            similarity_score = float(1.0 / (1.0 + distances[0][0]))
        else:
            similarity_score = 0.0
        
        self.index.add(np.array([embedding]).astype('float32'))
        self.known_threats_data.append({"threat": threat_type, "ts": datetime.utcnow().isoformat()})

        # Step 6: CVE Enrichment (Mock integration)
        cve_data = self._get_mock_cve(threat_type)

        # Step 7: Risk Score Calculation
        risk_score = self._calculate_risk_score(severity_res['score'], threat_conf, similarity_score)

        # Step 8: Auto SOC Report (Simulated Llama 3 Output)
        soc_report = self._generate_soc_report(log_content, threat_type, severity_label, risk_score, mitre_tech, cve_data)

        # Step 9: Store in SQLite
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "log_content": log_content,
            "severity": severity_label,
            "threat_type": threat_type,
            "mitre_technique": mitre_tech,
            "risk_score": risk_score,
            "soc_report": soc_report,
            "cve_enrichment": json.dumps(cve_data)
        }
        self._store_report(report_data)

        return report_data

    def _get_mock_cve(self, threat_type: str) -> List[str]:
        cve_mocks = {
            "SQL Injection": ["CVE-2023-24329", "CVE-2021-44228"],
            "XSS": ["CVE-2023-3824", "CVE-2022-31813"],
            "RCE": ["CVE-2021-44228", "CVE-2023-22515"]
        }
        return cve_mocks.get(threat_type, ["CVE-2024-XXXX"])

    def _calculate_risk_score(self, sev: float, conf: float, sim: float) -> float:
        # Weighted formula
        return round((sev * 0.4 + conf * 0.4 + sim * 0.2) * 100, 2)

    def _generate_soc_report(self, log, t_type, sev, risk, mitre, cve) -> str:
        return f"""
### AUTOMATED SOC INCIDENT REPORT
**ID:** {random_id()} | **Severity:** {sev} | **Risk Score:** {risk}/100

**Incident Analysis:**
Detected a potential **{t_type}** attempt targeting the system endpoint. The pattern aligns with **{mitre}**.

**Technical Details:**
- Payload Fingerprint: {hash(log)}
- MITRE ATT&CK: {mitre}
- Potential Vulnerabilities: {", ".join(cve)}

**Automated Recommendation:**
1. Block the source IP immediately.
2. Review logs for successful exploitation.
3. Patch relevant services associated with {cve[0]}.
"""

    def _store_report(self, data: Dict):
        conn = sqlite3.connect(INTEL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO soc_reports (timestamp, log_content, severity, threat_type, mitre_technique, risk_score, soc_report, cve_enrichment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['timestamp'], data['log_content'], data['severity'], data['threat_type'], 
              data['mitre_technique'], data['risk_score'], data['soc_report'], data['cve_enrichment']))
        conn.commit()
        conn.close()

def random_id():
    import string
    import random
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Global instance
intel_pipeline = IntelligencePipeline()
