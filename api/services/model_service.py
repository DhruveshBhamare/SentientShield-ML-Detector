import os
import json
from typing import Dict, Optional

import joblib

from ..core.config import MODEL_PATH, METADATA_PATH


_model = None
_metadata: Dict = {}


def load_model_if_needed() -> None:
    global _model, _metadata
    if _model is not None:
        return
    if not os.path.exists(MODEL_PATH) or not os.path.exists(METADATA_PATH):
        raise FileNotFoundError("Model or metadata not found. Please run training first.")
    _model = joblib.load(MODEL_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        _metadata = json.load(f)


def get_model():
    load_model_if_needed()
    return _model


def get_metadata() -> Dict:
    load_model_if_needed()
    return _metadata