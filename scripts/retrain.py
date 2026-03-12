import os
import json
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import numpy as np
import joblib

from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from .train import build_preprocessor, FEATURES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
DATASET_PATH = os.path.join(DATA_DIR, "web_threat_dataset.csv")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "best_model.joblib")
INCREMENTAL_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "incremental_model.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "metadata.json")
PERF_LOG_PATH = os.path.join(ARTIFACTS_DIR, "model_performance_log.csv")

os.makedirs(LOGS_DIR, exist_ok=True)


def _load_dataset() -> pd.DataFrame:
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}. Generate it first.")
    return pd.read_csv(DATASET_PATH)


def _collect_new_logs() -> pd.DataFrame:
    # Collect any csv under logs/ and concat; schema should match dataset
    frames = []
    for name in os.listdir(LOGS_DIR):
        if name.lower().endswith(".csv"):
            frames.append(pd.read_csv(os.path.join(LOGS_DIR, name)))
    if frames:
        df = pd.concat(frames, ignore_index=True)
        return df
    # No external logs found; return empty
    return pd.DataFrame()


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    # Minimal cleaning: ensure required columns exist, fill missing strings
    needed = set(FEATURES + ["attack_type", "label"])
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Incoming logs missing required columns: {missing}")
    df["headers"] = df["headers"].fillna("")
    df["url"] = df["url"].fillna("")
    df["user_agent"] = df["user_agent"].fillna("")
    return df


def _evaluate(y_true_labels, y_pred_labels) -> Dict[str, Any]:
    acc = accuracy_score(y_true_labels, y_pred_labels)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true_labels, y_pred_labels, average="macro", zero_division=0
    )
    return {"accuracy": acc, "precision_macro": precision, "recall_macro": recall, "f1_macro": f1}


def daily_retrain() -> Dict[str, Any]:
    base_df = _load_dataset()
    new_df = _collect_new_logs()
    if not new_df.empty:
        new_df = _clean(new_df)
        # Append cleaned logs to dataset
        base_df = pd.concat([base_df, new_df], ignore_index=True)
        base_df.to_csv(DATASET_PATH, index=False)

    # Train/Update incremental model
    X = base_df[FEATURES].copy()
    y = base_df["attack_type"].copy()

    label_encoder = LabelEncoder()
    y_enc = label_encoder.fit_transform(y)

    X_train, X_val, y_train, y_val = train_test_split(X, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

    preprocessor = build_preprocessor()

    if os.path.exists(INCREMENTAL_MODEL_PATH):
        inc_pipeline: Pipeline = joblib.load(INCREMENTAL_MODEL_PATH)
        clf: SGDClassifier = inc_pipeline.named_steps["clf"]
        # partial_fit requires classes
        clf.partial_fit(preprocessor.fit_transform(X_train), y_train, classes=np.unique(y_enc))
        inc_pipeline.named_steps["preprocess"] = preprocessor
    else:
        clf = SGDClassifier(loss="log_loss", max_iter=1000, random_state=42)
        inc_pipeline = Pipeline(steps=[
            ("preprocess", preprocessor),
            ("clf", clf),
        ])
        # Use partial_fit with classes
        inc_pipeline.named_steps["clf"].partial_fit(preprocessor.fit_transform(X_train), y_train, classes=np.unique(y_enc))

    # Evaluate incremental model
    y_pred = inc_pipeline.predict(X_val)
    metrics = _evaluate(label_encoder.inverse_transform(y_val), label_encoder.inverse_transform(y_pred))

    # Compare with current best model
    best_metrics = None
    best_model_name = None
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            md = json.load(f)
            best_metrics = md.get("metrics")
            best_model_name = md.get("best_model")

    # Persist incremental model
    joblib.dump(inc_pipeline, INCREMENTAL_MODEL_PATH)

    # Decide active model: replace best if improved F1
    active_path = MODEL_PATH
    active_changed = False
    if best_metrics is None or metrics["f1_macro"] > best_metrics.get("f1_macro", -1):
        joblib.dump(inc_pipeline, MODEL_PATH)
        best_model_name = "SGDClassifier-Incremental"
        best_metrics = metrics
        active_changed = True

    # Update metadata and log
    metadata = {
        "best_model": best_model_name,
        "metrics": best_metrics,
        "label_classes": list(label_encoder.classes_),
        "features": FEATURES,
        "target": "attack_type",
        "last_trained_at": datetime.utcnow().isoformat(),
        "dataset_path": DATASET_PATH,
        "active_model_path": active_path,
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Append to performance log
    header = ["timestamp", "model", "accuracy", "precision_macro", "recall_macro", "f1_macro", "active_changed"]
    row = [metadata["last_trained_at"], best_model_name, best_metrics["accuracy"], best_metrics["precision_macro"], best_metrics["recall_macro"], best_metrics["f1_macro"], active_changed]
    if not os.path.exists(PERF_LOG_PATH):
        pd.DataFrame([row], columns=header).to_csv(PERF_LOG_PATH, index=False)
    else:
        with open(PERF_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(",".join(map(str, row)) + "\n")

    # --- PERMANENT DEPLOYMENT SYNC (HF HUB) ---
    hf_repo = os.getenv("HF_HUB_REPO_ID") or os.getenv("HF_HUB_MODEL_ID")
    hf_token = os.getenv("HF_TOKEN")
    if hf_repo and hf_token:
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=hf_token)
            api.upload_file(
                path_or_fileobj=MODEL_PATH,
                path_in_repo="best_model.joblib",
                repo_id=hf_repo,
                repo_type="model"
            )
            api.upload_file(
                path_or_fileobj=METADATA_PATH,
                path_in_repo="metadata.json",
                repo_id=hf_repo,
                repo_type="model"
            )
            print(f"[Permanent Deployment] Successfully synced retrained model to {hf_repo}")
        except Exception as sync_err:
            print(f"[Permanent Deployment] HF Sync failed: {sync_err}")

    return {"active_changed": active_changed, "metrics": best_metrics, "best_model": best_model_name}


if __name__ == "__main__":
    out = daily_retrain()
    print(json.dumps(out, indent=2))
