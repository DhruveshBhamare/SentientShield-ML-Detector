import os
from typing import List


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(ROOT_DIR, "src", "static")
ARTIFACTS_DIR = os.path.join(ROOT_DIR, "artifacts")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
LOG_DIR = os.path.join(ROOT_DIR, "logs")


# Ensure important directories exist
os.makedirs(LOG_DIR, exist_ok=True)


# Model files
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "best_model.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "metadata.json")
PERF_LOG_PATH = os.path.join(ARTIFACTS_DIR, "model_performance_log.csv")


# CORS and Security config
TRUSTED_ORIGINS: List[str] = [
    o.strip()
    for o in os.getenv("TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
    if o.strip()
]

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-prod")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")


# Logging files
API_LOG_PATH = os.path.join(LOG_DIR, "api_calls.jsonl")


# Scheduler
RETRAIN_INTERVAL_SECONDS = int(os.getenv("RETRAIN_INTERVAL_SECONDS", str(24 * 60 * 60)))
