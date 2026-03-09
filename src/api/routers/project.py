import os
import json
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from ...configs.security import auth_dependency
from ...configs.config import (
    ROOT_DIR,
    STATIC_DIR,
    ARTIFACTS_DIR,
    MODEL_PATH,
    METADATA_PATH,
)
from ...models.loader import get_metadata


router = APIRouter(prefix="/api/project", tags=["Project"])


@router.get("/info")
async def project_info(user: Dict = Depends(auth_dependency)):
    try:
        readme_path = Path(ROOT_DIR) / "README.md"
        description = None
        if readme_path.exists():
            # Read first heading and following paragraph for summary
            text = readme_path.read_text(encoding="utf-8")
            lines = [l.strip() for l in text.splitlines()]
            heading = next((l for l in lines if l.startswith("#")), None)
            paragraph = next((l for l in lines if l and not l.startswith("#") and not l.startswith("[") and not l.startswith("<")), None)
            description = paragraph or heading

        metadata = {}
        try:
            metadata = get_metadata()
        except Exception:
            # May not be trained yet
            metadata = {}

        return {
            "name": "SentientShield-WebAttackPredictor",
            "version": "1.0.0",
            "description": description,
            "paths": {
                "root": str(ROOT_DIR),
                "static": str(STATIC_DIR),
                "artifacts": str(ARTIFACTS_DIR),
            },
            "model": {
                "best_model": metadata.get("best_model"),
                "label_classes": metadata.get("label_classes", []),
                "metrics": metadata.get("metrics"),
                "last_trained_at": metadata.get("last_trained_at"),
            },
            "user": user.get("sub") or user.get("uid"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def project_models(user: Dict = Depends(auth_dependency)):
    try:
        # Static description aligned with scripts/train.py pipeline
        preprocessing = [
            "header parsing",
            "categorical encoding",
            "scaling/normalization",
            "feature engineering",
        ]

        candidates = [
            {"name": "LogisticRegression", "package": "scikit-learn", "type": "linear classifier"},
            {"name": "RandomForestClassifier", "package": "scikit-learn", "type": "ensemble trees"},
            {"name": "XGBClassifier", "package": "xgboost", "type": "gradient boosting"},
        ]

        runtime_artifacts = [
            {"file": "best_model.joblib", "required": True},
            {"file": "incremental_model.joblib", "required": False},
            {"file": "metadata.json", "required": True},
            {"file": "model_performance_log.csv", "required": False},
        ]

        return {
            "preprocessing": preprocessing,
            "candidates": candidates,
            "artifacts": runtime_artifacts,
            "user": user.get("sub") or user.get("uid"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts")
async def project_artifacts(user: Dict = Depends(auth_dependency)):
    try:
        files = [
            "best_model.joblib",
            "incremental_model.joblib",
            "metadata.json",
            "model_performance_log.csv",
        ]

        status: List[Dict] = []
        for fname in files:
            fpath = Path(ARTIFACTS_DIR) / fname
            status.append({
                "file": fname,
                "exists": fpath.exists(),
                "size_bytes": fpath.stat().st_size if fpath.exists() else None,
                "path": str(fpath),
            })

        return {"artifacts": status, "user": user.get("sub") or user.get("uid")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requirements")
async def project_requirements(user: Dict = Depends(auth_dependency)):
    try:
        req_path = Path(ROOT_DIR) / "requirements.txt"
        packages: List[str] = []
        if req_path.exists():
            for line in req_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                packages.append(line)

        return {"packages": packages, "user": user.get("sub") or user.get("uid")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))