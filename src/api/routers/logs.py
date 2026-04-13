from typing import Dict, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from ...configs.security import auth_dependency
import os
import logging
from ...services.log_service import DistilBERTLogClassifier, MiniLMEmbedder, InMemoryVectorIndex, FaissVectorIndex, ZeroShotThreatClassifier, PhishingDetector, MITREAttckMapper, SOCReportGenerator, TrendStore, PGTrendStore, RiskScoringEngine, PipelineEngine, NVIDIAQwenChatbot

router = APIRouter(prefix="/api/logs", tags=["Logs"])
logger = logging.getLogger(__name__)
_ctx = None
_ctx_lock = threading.Lock()

def _get_ctx():
    global _ctx
    if _ctx is not None:
        return _ctx

    with _ctx_lock:
        if _ctx is not None:
            return _ctx
        
        logger.info("[Logs] Initializing AI Context for the first time...")
        clf = DistilBERTLogClassifier()
        embedder = MiniLMEmbedder()
        nvidia_bot = NVIDIAQwenChatbot()
        if embedder.available:
            try:
                index = FaissVectorIndex(embedder)
                if index.index is None:
                    index = InMemoryVectorIndex(embedder)
            except Exception:
                index = InMemoryVectorIndex(embedder)
        else:
            index = InMemoryVectorIndex(embedder)
        zs = ZeroShotThreatClassifier()
        phish = PhishingDetector()
        attck = MITREAttckMapper(zs, embedder)
        soc = SOCReportGenerator(clf, attck, llm_client=nvidia_bot)
        trend = PGTrendStore(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else TrendStore(attck.db_path)
        risk = RiskScoringEngine(clf, trend, embedder)
        pipe = PipelineEngine(clf, embedder, index, attck, risk, soc)

        _ctx = {
            "clf": clf,
            "embedder": embedder,
            "nvidia_bot": nvidia_bot,
            "index": index,
            "zs": zs,
            "phish": phish,
            "attck": attck,
            "soc": soc,
            "trend": trend,
            "risk": risk,
            "pipe": pipe,
        }
    return _ctx

def prewarm_logs_context():
    """Trigger lazy initialization in a thread safe way."""
    try:
        _get_ctx()
    except Exception as e:
        logger.error(f"[Logs] Prewarm failed: {e}")

class LogRequest(BaseModel):
    message: str = Field(..., description="Log message text")
    context: Optional[Dict] = None

@router.post("/classify-severity")
async def classify_severity(req: LogRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    label, score = ctx["clf"].classify_severity(req.message)
    return {"severity": label, "score": score, "user": user.get("sub") or user.get("uid")}

@router.post("/predict-type")
async def predict_type(req: LogRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    label, score = ctx["clf"].predict_threat_type(req.message)
    return {"threat_type": label, "score": score, "user": user.get("sub") or user.get("uid")}

@router.post("/filter-alert")
async def filter_alert(req: LogRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    alert, action, score = ctx["clf"].filter_alert(req.message)
    return {"alert": alert, "action": action, "score": score, "user": user.get("sub") or user.get("uid")}

class BulkLogs(BaseModel):
    logs: list[str] = Field(default_factory=list)

@router.post("/ingest")
async def ingest(req: BulkLogs, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    added = ctx["index"].add(req.logs)
    return {"added": added, "total": len(ctx["index"].texts), "user": user.get("sub") or user.get("uid")}

class SimilarQuery(BaseModel):
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, ge=1, le=50)

@router.post("/similar")
async def similar(req: SimilarQuery, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    results = ctx["index"].search(req.query, req.top_k)
    return {"results": results, "user": user.get("sub") or user.get("uid")}

class ZeroShotRequest(BaseModel):
    message: str
    labels: list[str] | None = None
    multi_label: bool = True

@router.post("/zero-shot")
async def zero_shot(req: ZeroShotRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    default_labels = ["SQL Injection", "DDoS", "Malware", "Privilege Escalation", "Phishing", "XSS", "RCE"]
    labels = req.labels or default_labels
    result = ctx["zs"].classify(req.message, labels, req.multi_label)
    top = labels[0] if not result["labels"] else result["labels"][0]
    top_score = 0.0 if not result["scores"] else result["scores"][0]
    return {"labels": result["labels"], "scores": result["scores"], "top_label": top, "top_score": top_score, "user": user.get("sub") or user.get("uid")}

class EmailRequest(BaseModel):
    text: str

@router.post("/phishing-email")
async def phishing_email(req: EmailRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    res = ctx["phish"].classify_text(req.text)
    return {"label": res["label"], "score": res["score"], "user": user.get("sub") or user.get("uid")}

class URLRequest(BaseModel):
    url: str

@router.post("/phishing-url")
async def phishing_url(req: URLRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    res = ctx["phish"].classify_url(req.url)
    return {"label": res["label"], "score": res["score"], "user": user.get("sub") or user.get("uid")}

class AttckMapRequest(BaseModel):
    message: str

@router.post("/attck-map")
async def attck_map(req: AttckMapRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    res = ctx["attck"].map(req.message)
    return {"mapping": res, "user": user.get("sub") or user.get("uid")}

@router.get("/attck-history")
async def attck_history(limit: int = 20, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["attck"].history(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

class SocReportRequest(BaseModel):
    logs: list[str] = Field(default_factory=list)
    title: str | None = None

@router.post("/soc-report")
async def soc_report(req: SocReportRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    res = ctx["soc"].generate(req.logs, req.title)
    return {"report": res["report"], "model": res.get("model", "fallback"), "user": user.get("sub") or user.get("uid")}

class RecordEventRequest(BaseModel):
    message: str

@router.post("/record-event")
async def record_event(req: RecordEventRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    sev, s_score = ctx["clf"].classify_severity(req.message)
    thr, t_score = ctx["clf"].predict_threat_type(req.message)
    risk = max(s_score, t_score)
    ctx["trend"].record_event(req.message, sev, thr, risk)
    ctx["attck"].map(req.message)
    return {"severity": sev, "threat_type": thr, "risk": risk, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/top-attack-types")
async def top_attack_types(limit: int = 10, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].top_attack_types(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/attack-frequency")
async def attack_frequency(bucket: str = "hour", limit: int = 24, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].attack_frequency(bucket=bucket, limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/frequency")
async def frequency(bucket: str = "hour", limit: int = 24, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].attack_frequency(bucket=bucket, limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/mitre-distribution")
async def mitre_distribution(limit: int = 15, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].mitre_distribution(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/mitre-table")
async def mitre_table(limit: int = 20, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].mitre_table(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/trends/risk-trends")
async def risk_trends(bucket: str = "day", limit: int = 14, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].risk_trends(bucket=bucket, limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

class RiskScoreRequest(BaseModel):
    message: str
    asset_value: float | None = None

@router.post("/risk-score")
async def risk_score(req: RiskScoreRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    res = ctx["risk"].score(req.message, req.asset_value)
    return {"result": res, "user": user.get("sub") or user.get("uid")}

@router.get("/events/recent")
async def recent_events(limit: int = 50, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].recent_events(limit=limit)
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/recent")
async def recent(limit: int = 20, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    items = ctx["trend"].recent_events(limit=max(1, min(limit, 200)))
    items = sorted(items, key=lambda x: x.get("ts") or "", reverse=True)[: max(1, min(limit, 200))]
    return {"items": items, "user": user.get("sub") or user.get("uid")}

@router.get("/metrics/alerts-today")
async def alerts_today(user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    count = ctx["trend"].alerts_today()
    return {"count": count, "user": user.get("sub") or user.get("uid")}

@router.get("/metrics/critical-today")
async def critical_today(user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    count = ctx["trend"].critical_today()
    return {"count": count, "user": user.get("sub") or user.get("uid")}

@router.get("/metrics/risk-gauge")
async def risk_gauge(user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    avg = ctx["trend"].average_risk_today()
    return {"avg": avg, "user": user.get("sub") or user.get("uid")}

class LlmGenerateRequest(BaseModel):
    prompt: str

@router.post("/llm-generate")
async def llm_generate(req: LlmGenerateRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    # Use the new NVIDIA Qwen chatbot for all LLM generation requests
    try:
        response = ctx["nvidia_bot"].generate_response(req.prompt, stream=False)
        return {"text": response, "user": user.get("sub") or user.get("uid"), "model": ctx["nvidia_bot"].model}
    except Exception as e:
        logger.error(f"LLM Generation failed: {e}")
        # Fallback to local SOC generator if available
        res = ctx["soc"].generate([req.prompt], "AI Assistance Request")
        return {"text": res["report"], "user": user.get("sub") or user.get("uid"), "fallback": True}
class PipelineRunRequest(BaseModel):
    message: str
    asset_value: float | None = None
    ingest: bool = True
    soc_report: bool = Field(default=False, validation_alias="report")
    title: str | None = None

@router.post("/pipeline/run")
async def pipeline_run(req: PipelineRunRequest, user: Dict = Depends(auth_dependency)):
    ctx = _get_ctx()
    res = ctx["pipe"].run(req.message, req.asset_value, req.ingest, req.soc_report, req.title)
    return {"result": res, "user": user.get("sub") or user.get("uid")}

class BatchWorkflowRequest(BaseModel):
    logs: list[str] = Field(default_factory=list)
    title: str | None = None

@router.post("/workflow/batch-process")
async def trigger_batch_workflow(req: BatchWorkflowRequest, user: Dict = Depends(auth_dependency)):
    """
    Triggers a batch log processing workflow.
    In Render environments, it uses the Render SDK to trigger a distributed task.
    In local environments, it runs synchronously.
    """
    try:
        if os.getenv("RENDER"):
            from render_sdk import RenderAsync
            render = RenderAsync()
            # Slug format: {service-slug}/{task-name}
            # service-slug is defined in render.yaml as 'sentientshield-workflows'
            # task-name is defined in render_workflows.py as 'process_logs'
            task_slug = "sentientshield-workflows/process_logs"
            
            logger.info(f"Triggering Render Workflow task: {task_slug}")
            started_run = await render.workflows.start_task(task_slug, [req.logs])
            
            return {
                "status": "triggered",
                "workflow_run_id": started_run.id,
                "task": task_slug,
                "user": user.get("sub") or user.get("uid")
            }
        else:
            # Fallback for local development
            from scripts.render_workflows import process_logs_task
            logger.info("Running workflow task locally (Synchronous)")
            results = process_logs_task(req.logs)
            return {
                "status": "completed", 
                "results": results, 
                "user": user.get("sub") or user.get("uid")
            }
    except Exception as e:
        logger.error(f"Workflow trigger failed: {e}")
        return {"status": "error", "detail": str(e), "user": user.get("sub") or user.get("uid")}
