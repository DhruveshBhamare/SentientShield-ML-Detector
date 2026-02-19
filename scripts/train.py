import os
import json
import joblib
import warnings
from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from sklearn.metrics import classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import FunctionTransformer
from .utils import fillna_text

warnings.filterwarnings("ignore", category=UserWarning)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
DEFAULT_DATASET = os.path.join(DATA_DIR, "web_threat_dataset.csv")
SAMPLE_DATASET = os.path.join(DATA_DIR, "sample_web_threats.csv")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "best_model.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "metadata.json")

FEATURES = [
    "request_type", "headers", "payload_size", "response_time",
    "ip_reputation", "url", "user_agent", "anomaly_score"
]
TARGET = "attack_type"  # expected classes: normal, sql_injection, xss, ddos, brute_force


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def generate_sample_dataset(path: str, n: int = 800) -> None:
    np.random.seed(42)
    request_types = ["GET", "POST", "PUT", "DELETE"]
    user_agents = [
        "Mozilla/5.0", "curl/8.5.0", "python-requests/2.31", "Chrome/124.0"
    ]
    labels = ["normal", "sql_injection", "xss", "ddos", "brute_force"]

    def random_url():
        base = np.random.choice(["/login", "/search", "/api/data", "/admin", "/index"])
        suffix = "".join(np.random.choice(list("abcdefghijklmnopqrstuvwxyz0123456789"), size=np.random.randint(0, 15)))
        return f"{base}?q={suffix}"

    rows = []
    for _ in range(n):
        label = np.random.choice(labels, p=[0.60, 0.10, 0.10, 0.10, 0.10])
        request_type = np.random.choice(request_types)
        payload_size = np.random.gamma(shape=2.0, scale=300.0)
        response_time = np.random.gamma(shape=2.0, scale=120.0)
        ip_reputation = np.clip(np.random.normal(70, 25), 0, 100)
        anomaly_score = np.clip(np.random.normal(0.2 if label == "normal" else 0.7, 0.15), 0, 1)
        headers = "; ".join([
            f"User-Agent: {np.random.choice(user_agents)}",
            f"Accept: application/json",
            f"X-Forwarded-For: 192.168.{np.random.randint(0,255)}.{np.random.randint(0,255)}",
            f"Content-Type: {np.random.choice(['application/json','text/html','application/x-www-form-urlencoded'])}"
        ])
        url = random_url()
        user_agent = np.random.choice(user_agents)

        # add attack-specific signatures
        if label == "sql_injection":
            payload_size *= 1.4
            url += "' OR '1'='1"
            headers += "; X-SQL-Test: ' OR '1'='1"
            anomaly_score = max(anomaly_score, 0.75)
        elif label == "xss":
            url += "<script>alert('x')</script>"
            headers += "; X-XSS-Test: <img src=x onerror=alert(1)>"
            anomaly_score = max(anomaly_score, 0.7)
        elif label == "ddos":
            response_time *= 1.8
            payload_size *= 1.2
            anomaly_score = max(anomaly_score, 0.8)
        elif label == "brute_force":
            payload_size *= 0.9
            anomaly_score = max(anomaly_score, 0.65)

        rows.append({
            "request_type": request_type,
            "headers": headers,
            "payload_size": float(payload_size),
            "response_time": float(response_time),
            "ip_reputation": float(ip_reputation),
            "url": url,
            "user_agent": user_agent,
            "anomaly_score": float(anomaly_score),
            "label": label,
        })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def load_dataset() -> pd.DataFrame:
    if os.path.exists(DEFAULT_DATASET):
        print(f"Loading dataset: {DEFAULT_DATASET}")
        return pd.read_csv(DEFAULT_DATASET)
    elif os.path.exists(SAMPLE_DATASET):
        print(f"Loading dataset: {SAMPLE_DATASET}")
        return pd.read_csv(SAMPLE_DATASET)
    else:
        print("No dataset found; generating a sample dataset for demonstration...")
        generate_sample_dataset(SAMPLE_DATASET)
        return pd.read_csv(SAMPLE_DATASET)


def build_preprocessor():
    numeric_features = ["payload_size", "response_time", "ip_reputation", "anomaly_score"]
    categorical_features = ["request_type"]

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    def _unused_fillna_text(s):
        try:
            return s.fillna("")
        except Exception:
            return s

    text_headers = Pipeline(steps=[
        ("fillna", FunctionTransformer(func=fillna_text, validate=False)),
        ("tfidf", TfidfVectorizer(max_features=400, ngram_range=(1, 2)))
    ])
    text_url = Pipeline(steps=[
        ("fillna", FunctionTransformer(func=fillna_text, validate=False)),
        ("tfidf", TfidfVectorizer(max_features=400, ngram_range=(1, 2)))
    ])
    text_ua = Pipeline(steps=[
        ("fillna", FunctionTransformer(func=fillna_text, validate=False)),
        ("tfidf", TfidfVectorizer(max_features=300, ngram_range=(1, 2)))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
            ("hdr", text_headers, "headers"),
            ("url", text_url, "url"),
            ("ua", text_ua, "user_agent"),
        ],
        remainder="drop",
        sparse_threshold=0.3,
        n_jobs=None,
    )
    return preprocessor


def evaluate_model(y_true_labels, y_pred_labels, y_true_enc, y_proba, label_encoder) -> Dict[str, Any]:
    acc = accuracy_score(y_true_labels, y_pred_labels)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true_labels, y_pred_labels, average="macro", zero_division=0
    )

    try:
        roc = roc_auc_score(y_true_enc, y_proba, multi_class="ovr", average="macro")
    except Exception:
        roc = None

    print("\nClassification Report (per-class):")
    print(classification_report(y_true_labels, y_pred_labels, zero_division=0))

    return {
        "accuracy": acc,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "roc_auc_macro": roc,
        "classes": list(label_encoder.classes_),
    }


def main():
    ensure_dirs()
    df = load_dataset()

    # Basic sanitation: ensure required columns
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    X = df[FEATURES].copy()
    y = df[TARGET].copy()

    # Encode labels
    label_encoder = LabelEncoder()
    y_enc = label_encoder.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    preprocessor = build_preprocessor()

    # Define candidate models
    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, n_jobs=None),
        "RandomForest": RandomForestClassifier(n_estimators=300, max_depth=None, n_jobs=-1, random_state=42),
        "XGBoost": XGBClassifier(
            n_estimators=400,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            tree_method="hist",
            random_state=42,
            num_class=len(label_encoder.classes_),
            n_jobs=-1,
        ),
    }

    results = []
    best_f1 = -1.0
    best = None

    for name, clf in models.items():
        pipeline = Pipeline(steps=[
            ("preprocess", preprocessor),
            ("clf", clf),
        ])
        print(f"\nTraining model: {name}")
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        # Ensure probability output exists
        try:
            y_proba = pipeline.predict_proba(X_test)
        except Exception:
            # fallback: dummy probabilities
            y_proba = np.zeros((len(y_pred), len(label_encoder.classes_)))
            for i, p in enumerate(y_pred):
                y_proba[i, int(p)] = 1.0

        metrics = evaluate_model(
            y_true_labels=label_encoder.inverse_transform(y_test),
            y_pred_labels=label_encoder.inverse_transform(y_pred),
            y_true_enc=y_test,
            y_proba=y_proba,
            label_encoder=label_encoder,
        )
        metrics["model_name"] = name
        results.append(metrics)

        if metrics["f1_macro"] > best_f1:
            best_f1 = metrics["f1_macro"]
            best = {
                "name": name,
                "pipeline": pipeline,
                "metrics": metrics,
            }

    # Persist best model
    if best is None:
        raise RuntimeError("No model was trained successfully.")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(best["pipeline"], MODEL_PATH)

    metadata = {
        "best_model": best["name"],
        "metrics": best["metrics"],
        "label_classes": list(label_encoder.classes_),
        "features": FEATURES,
        "target": TARGET,
        "last_trained_at": pd.Timestamp.utcnow().isoformat(),
        "dataset_path": DEFAULT_DATASET,
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\nBest model:", best["name"])
    print("Metrics:", json.dumps(best["metrics"], indent=2))
    print(f"Saved model to: {MODEL_PATH}")
    print(f"Saved metadata to: {METADATA_PATH}")


if __name__ == "__main__":
    main()