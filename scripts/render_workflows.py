import os
import sys
import logging
import json
from datetime import datetime
from typing import List, Dict

# Ensure root is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from render_sdk import Workflows, Retry
from src.services.log_service import (
    DistilBERTLogClassifier, 
    MiniLMEmbedder, 
    InMemoryVectorIndex, 
    MITREAttckMapper, 
    ZeroShotThreatClassifier,
    CVERAGEngine,
    RiskScoringEngine,
    SOCReportGenerator,
    PipelineEngine,
    NVIDIAQwenChatbot,
    TrendStore
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SentientShieldWorkflow")

# Initialize Render Workflows App
app = Workflows()

def get_pipeline():
    """Helper to initialize the full security pipeline."""
    clf = DistilBERTLogClassifier()
    embedder = MiniLMEmbedder()
    index = InMemoryVectorIndex(embedder)
    zs = ZeroShotThreatClassifier()
    attck = MITREAttckMapper(zs, embedder)
    nvidia_bot = NVIDIAQwenChatbot()
    soc = SOCReportGenerator(clf, attck, llm_client=nvidia_bot)
    cve = CVERAGEngine(embedder, llm_client=nvidia_bot)
    trend = TrendStore(os.path.join("logs", "intelligence.db"))
    risk = RiskScoringEngine(clf, cve, trend, embedder)
    return PipelineEngine(clf, embedder, index, attck, cve, risk, soc)

@app.task(name="process_logs")
def process_logs_task(logs: List[str]):
    """
    Render Workflow Task: Processes a batch of logs through the AI pipeline.
    """
    logger.info(f"Processing {len(logs)} logs via Render Workflow...")
    pipeline = get_pipeline()
    results = []
    
    for log in logs:
        res = pipeline.run(log, soc_report=True, title=f"Workflow Report - {datetime.now().isoformat()}")
        results.append({
            "log": log,
            "analysis": res
        })
        logger.info(f"Processed: {log[:50]}... -> {res['severity']['label']}")
    
    return results

@app.task(name="daily_retrain")
def daily_retrain_task():
    """
    Render Workflow Task: Offloads model retraining to Render instances.
    """
    logger.info("Starting scheduled retraining workflow...")
    from scripts.retrain import daily_retrain
    result = daily_retrain()
    logger.info(f"Retraining workflow completed: {result}")
    return result

if __name__ == "__main__":
    # If RENDER is set, start the task registration and runner process
    if os.getenv("RENDER"):
        print("Starting Render Workflow Runner...")
        app.start()
    else:
        # If run directly locally, process 9 sample logs to demonstrate
        sample_logs = [
            "SELECT * FROM users WHERE id = 1 OR 1=1; --",
            "<script>alert('XSS_ATTACK_DETECTED')</script>",
            "Failed login attempt for user admin from 192.168.1.100 - multiple attempts in 5 seconds",
            "GET /../../../../etc/passwd HTTP/1.1",
            "Your account has been suspended. Click here to verify: http://secure-sentient-shield.com/login",
            "Suspicious outbound connection to 45.23.11.2 port 4444 (Reverse Shell pattern)",
            "System health check: All components operational. Memory usage: 45%",
            "Insider Threat Alert: Unauthorized access to sensitive financial data by user 'marketing_assistant' at 3 AM",
            "Ransomware Activity: Mass file encryption detected on /shared/finance_records. AES key exchange observed to 103.45.12.9"
        ]
        
        print("\n" + "="*50)
        print("SENTIENT SHIELD - LOG PROCESSING DEMO (9 LOGS)")
        print("="*50 + "\n")
        
        pipeline = get_pipeline()
        for i, log in enumerate(sample_logs, 1):
            print(f"[{i}/9] Processing: {log}")
            res = pipeline.run(log, soc_report=False)
            print(f"    - Severity: {res['severity']['label'].upper()} (Score: {res['severity']['score']:.2f})")
            print(f"    - Threat:   {res['threat_type']['label'].upper()}")
            if res['attck_mapping']:
                print(f"    - MITRE:    {res['attck_mapping'][0]['technique_name']} ({res['attck_mapping'][0]['technique_id']})")
            print("-" * 30)

        print("\nDemo complete. (To register tasks on Render, ensure RENDER=true)")
