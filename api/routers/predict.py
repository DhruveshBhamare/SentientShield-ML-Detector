import json
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ..core.security import auth_dependency
from ..core.config import API_LOG_PATH
from ..schemas.common import RequestFeatures
from ..services.model_service import get_model, get_metadata
from ..services.intel_service import intel_pipeline


router = APIRouter(prefix="/api", tags=["Predict"])


@router.post("/predict")
async def predict(features: RequestFeatures, user: Dict = Depends(auth_dependency)):
    try:
        model = get_model()
        metadata = get_metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    row = {
        "request_type": features.request_type,
        "headers": features.headers or "",
        "payload_size": features.payload_size,
        "response_time": features.response_time,
        "ip_reputation": features.ip_reputation,
        "url": features.url or "",
        "user_agent": features.user_agent or "",
        "anomaly_score": features.anomaly_score,
    }

    try:
        proba = model.predict_proba([row])[0]
        pred_idx = int(proba.argmax())
        classes = metadata.get("label_classes", [])
        pred_label = classes[pred_idx] if classes else str(pred_idx)
        prob_map = {classes[i] if i < len(classes) else str(i): float(p) for i, p in enumerate(proba)}
        result = {
            "predicted_label": pred_label,
            "probabilities": prob_map,
            "model": metadata.get("best_model"),
            "confidence": float(max(proba))
        }
    except Exception:
        try:
            pred_idx = int(model.predict([row])[0])
            classes = metadata.get("label_classes", [])
            pred_label = classes[pred_idx] if classes else str(pred_idx)
            result = {
                "predicted_label": pred_label,
                "probabilities": {},
                "model": metadata.get("best_model"),
                "confidence": None
            }
        except Exception as inner:
            raise HTTPException(status_code=500, detail=f"Inference error: {inner}")

    # --- FULL AUTOMATIC INTELLIGENCE PIPELINE ---
    intel_report = None
    if features.raw_log:
        try:
            intel_report = await intel_pipeline.process_log(features.raw_log)
            result["intelligence"] = intel_report
        except Exception as e:
            print(f"Intelligence Pipeline Error: {e}")
            result["intelligence_error"] = str(e)

    try:
        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "path": "/api/predict",
            "method": "POST",
            "status": 200,
            "user": user.get("sub") or user.get("uid"),
            "prediction": result["predicted_label"],
            "confidence": result.get("confidence"),
            "risk_score": intel_report.get("risk_score") if intel_report else None,
            "threat_type": intel_report.get("threat_type") if intel_report else None
        }
        with open(API_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

    return result