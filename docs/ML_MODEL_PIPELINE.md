# SentientShield ML Model Pipeline (Data → Features → Prediction)

This document explains how SentientShield turns request/log data into an **attack-type prediction**, from data “sorting” (preprocessing) to inference and how results reach the UI.

## 1) What the ML model predicts

SentientShield’s `/api/predict` endpoint predicts an **attack_type** label based on structured request features such as method, headers, URL, user agent, size, latency, and anomaly score.

- API route: [predict.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py#L14-L89)
- Input schema: [RequestFeatures](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/schemas/common.py#L5-L15)

## 2) High-level flow (runtime)

1. **Frontend collects features** (or you provide them manually in the UI).
2. Frontend sends a request to `POST /api/predict` with the feature JSON payload.
3. Backend loads the trained scikit-learn pipeline from `artifacts/best_model.joblib`.
4. The model pipeline preprocesses inputs and predicts:
   - `predicted_label`
   - `probabilities` (if supported by the model)
   - `confidence`
5. (Optional) If `raw_log` is provided, a deeper “intelligence pipeline” runs for enrichment (severity, threat type, MITRE, risk score).
6. Response is returned to the UI and also appended to `logs/api_calls.jsonl`.

## 3) API payload structure

`POST /api/predict`

Fields in [RequestFeatures](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/schemas/common.py#L5-L15):

- `request_type` (string): HTTP method (GET/POST/…)
- `headers` (string|null): raw headers string (serialized)
- `payload_size` (float): bytes
- `response_time` (float): ms
- `ip_reputation` (float): 0–100
- `url` (string|null)
- `user_agent` (string|null)
- `anomaly_score` (float): 0.0–1.0
- `raw_log` (string|null): optional free-form log line for enrichment (not required for the ML classifier)

## 4) “Data sorting” (preprocessing) pipeline

The ML model is saved as a **scikit-learn Pipeline** that includes both preprocessing and the classifier. This means the API can send raw feature values and the pipeline handles vectorization/encoding internally.

Training code: [scripts/train.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/scripts/train.py)

### 4.1 Feature groups

The training pipeline splits features into:

**Numeric features**
- `payload_size`
- `response_time`
- `ip_reputation`
- `anomaly_score`

**Categorical**
- `request_type`

**Text**
- `headers`
- `url`
- `user_agent`

Source: [FEATURES + build_preprocessor](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/scripts/train.py#L33-L167)

### 4.2 Numeric processing

Numeric features go through:
- median imputation
- standard scaling

### 4.3 Categorical processing

`request_type` goes through:
- most-frequent imputation
- one-hot encoding

### 4.4 Text processing

Text features are converted into ML-ready vectors using TF‑IDF:

- `headers`: TF‑IDF with max_features=400, ngram 1–2
- `url`: TF‑IDF with max_features=400, ngram 1–2
- `user_agent`: TF‑IDF with max_features=300, ngram 1–2

Each text column is filled with empty strings for missing values before TF‑IDF.

## 5) Model training & selection (offline)

During training (`scripts/train.py`):

1. Dataset is loaded from:
   - `data/web_threat_dataset.csv` if present, otherwise sample dataset fallback
2. Labels are encoded (LabelEncoder).
3. Train/test split with stratification.
4. Multiple candidate models are trained:
   - LogisticRegression
   - RandomForest
   - XGBoost (if installed/working)
5. Best model is chosen by **macro F1**.
6. Best full pipeline is saved to `artifacts/best_model.joblib`.
7. Metadata is saved to `artifacts/metadata.json` including:
   - best model name
   - metrics
   - label classes
   - feature list, target
   - train timestamp

Source: [train main()](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/scripts/train.py#L194-L297)

## 6) Model loading in the API

At runtime, the API loads:
- `artifacts/best_model.joblib`
- `artifacts/metadata.json`

If missing, it attempts to download them from HuggingFace Hub:
- default repo: `DhruveshBhamare/SentientShield-ML-Model`

Source: [models/loader.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/models/loader.py#L29-L72)

## 7) Inference logic

In [predict.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py#L17-L61):

1. Build a `row` dict with the feature keys expected by the trained pipeline.
2. Try `model.predict_proba([row])`:
   - maps probabilities to `metadata["label_classes"]`
   - sets `confidence = max(proba)`
3. If `predict_proba` isn’t supported, fallback to `model.predict([row])`.

The returned JSON includes:
- `predicted_label`
- `probabilities` (when available)
- `model` (best model name from metadata)
- `confidence` (when available)

## 8) Intelligence enrichment (optional)

If the request includes `raw_log`, the API triggers an enrichment pipeline:
- `intel_pipeline.process_log(raw_log)`

This produces a structured intelligence report that may include:
- severity
- threat_type
- MITRE mapping
- risk_score
- soc_report text

Source:
- [predict.py raw_log branch](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py#L62-L71)
- [intel_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/intel_service.py#L31-L178)

## 9) Logging & observability

Every `/api/predict` request appends a JSON line to:
- `logs/api_calls.jsonl`

It records:
- timestamp, path, method, status
- user id
- predicted label + confidence
- (if available) risk_score and threat_type from enrichment

Source: [predict.py logging](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py#L72-L87)

## 10) End-to-end sequence diagram (simplified)

```text
Browser UI
  └─ POST /api/dev-token  ───────────────► FastAPI (auth)
  └─ POST /api/predict (features JSON) ─► FastAPI /api/predict
                                         ├─ load model + metadata (joblib/json)
                                         ├─ sklearn Pipeline:
                                         │    preprocess (num/cat/text) → clf
                                         ├─ predict_proba / predict
                                         ├─ optional intel_pipeline(raw_log)
                                         └─ return JSON response
```

## 11) Practical tips (for better predictions)

- Provide realistic `headers`, `url`, and `user_agent` strings; TF‑IDF relies heavily on these text signals.
- Keep numeric fields in expected ranges:
  - `ip_reputation`: 0–100
  - `anomaly_score`: 0.0–1.0
- If you want enrichment + SOC-style details, include `raw_log`.

