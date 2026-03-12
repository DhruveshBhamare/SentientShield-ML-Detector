import os
import json
import logging
from typing import Dict, Optional

import joblib
from huggingface_hub import hf_hub_download

from ..configs.config import MODEL_PATH, METADATA_PATH, ARTIFACTS_DIR, MODELS_DIR

logger = logging.getLogger(__name__)

_model = None
_metadata: Dict = {}

def get_model_path(model_id: str) -> str:
    """Resolve model path from local models directory or fallback to model_id."""
    # Check if model_id is a path relative to MODELS_DIR and contains actual model files
    local_path = os.path.join(MODELS_DIR, model_id)
    
    # Heuristic: check if the directory exists and has a model weight file
    if os.path.exists(local_path):
        model_files = ["model.safetensors", "pytorch_model.bin", "tf_model.h5", "model.ckpt.index", "flax_model.msgpack"]
        if any(os.path.exists(os.path.join(local_path, f)) for f in model_files):
            return local_path
            
    return model_id

# HF Hub config
HF_REPO_ID = (
    os.getenv("HF_HUB_REPO_ID")
    or os.getenv("HF_HUB_MODEL_ID")
    or "DhruveshBhamare/SentientShield-ML-Model"
)

def download_from_hf():
    """Download model and metadata from HuggingFace Hub if they are missing."""
    try:
        if not os.path.exists(MODEL_PATH):
            logger.info(f"Downloading model from HF Hub: {HF_REPO_ID}")
            hf_hub_download(
                repo_id=HF_REPO_ID,
                filename="best_model.joblib",
                local_dir=ARTIFACTS_DIR
            )
        
        if not os.path.exists(METADATA_PATH):
            logger.info(f"Downloading metadata from HF Hub: {HF_REPO_ID}")
            hf_hub_download(
                repo_id=HF_REPO_ID,
                filename="metadata.json",
                local_dir=ARTIFACTS_DIR
            )
    except Exception as e:
        logger.error(f"Failed to download models from HF Hub: {e}")
        # Fallback to local files if any exist or re-raise
        if not os.path.exists(MODEL_PATH) or not os.path.exists(METADATA_PATH):
            raise FileNotFoundError(f"Model or metadata not found and HF download failed: {e}")

def load_model_if_needed() -> None:
    global _model, _metadata
    if _model is not None:
        return
    
    # Try downloading from HF if missing
    if not os.path.exists(MODEL_PATH) or not os.path.exists(METADATA_PATH):
        download_from_hf()

    _model = joblib.load(MODEL_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        _metadata = json.load(f)


def get_model():
    load_model_if_needed()
    return _model


def get_metadata() -> Dict:
    load_model_if_needed()
    return _metadata
