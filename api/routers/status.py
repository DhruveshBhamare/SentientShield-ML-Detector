import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ..core.security import auth_dependency
from ..core.config import PERF_LOG_PATH, METADATA_PATH


router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/status")
async def status(user: Dict = Depends(auth_dependency)):
    try:
        meta = {}
        if Path(METADATA_PATH).exists():
            meta = json.loads(Path(METADATA_PATH).read_text(encoding="utf-8"))

        performance = []
        if Path(PERF_LOG_PATH).exists():
            with open(PERF_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        performance.append(json.loads(line))
                    except Exception:
                        continue

        return {
            "server_time": datetime.utcnow().isoformat() + "Z",
            "user": user.get("sub") or user.get("uid"),
            "model": meta.get("best_model"),
            "label_classes": meta.get("label_classes", []),
            "performance": performance[-50:],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dev-token")
async def dev_token():
    try:
        import time
        import jwt
        from ..core.config import JWT_SECRET, JWT_ALG
        payload = {"sub": "dev-user", "uid": "dev-user", "exp": int(time.time()) + 3600}
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
        return {"token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
