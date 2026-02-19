# SentientShield-WebAttackPredictor

This project builds and deploys a web threat detection model that classifies incoming requests as normal or attacks (SQL Injection, XSS, DDoS, brute force).

## Features
- Automated preprocessing: imputations, scaling, one-hot encoding, and TF-IDF for text fields.
- Model comparison: Logistic Regression, Random Forest, and XGBoost.
- Metrics: accuracy, precision, recall, F1-score, and ROC-AUC (macro, OVR).
- Deployment: FastAPI `/predict` endpoint returning label and probabilities.

## Dataset Schema
Expected CSV columns:
- `request_type` (str), `headers` (str), `payload_size` (float), `response_time` (float), `ip_reputation` (float), `url` (str), `user_agent` (str), `anomaly_score` (float), `label` (str)

If `data/web_threats.csv` is not found, a synthetic dataset is generated at `data/sample_web_threats.csv` for demonstration.

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Train models and save the best:
   ```bash
   python scripts/train.py
   ```
3. Launch API:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
4. Example prediction:
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "request_type": "POST",
       "headers": "User-Agent: Mozilla/5.0; Accept: application/json",
       "payload_size": 1024,
       "response_time": 180,
       "ip_reputation": 35,
       "url": "/login?q=index",
       "user_agent": "Mozilla/5.0",
       "anomaly_score": 0.8
     }'
   ```

## Notes
- For best results, replace the synthetic dataset with your real logs.
- Adjust TF-IDF `max_features` and n-gram ranges for larger datasets.
- If XGBoost is heavy, you can disable it or tweak parameters.

---

## Dashboards
- Overview: `http://127.0.0.1:8000/static/premium.html`
- NeuralFort: `http://127.0.0.1:8000/static/neuralfort_dashboard.html`
- Model: `http://127.0.0.1:8000/static/dashboard.html`

## Frontend Features
- Layout toggle between sidebar and topbar (persists via `localStorage`).
- Polished click effects (ripple/pop/wiggle/pulse/glow).
- Realtime feed via WebSocket at `/api/ws/realtime` with auto‑retry.
- Security Copilot chat, anomalies/healing/LLM insights panels.

## Auth & Settings
- Open the Settings panel in any dashboard and paste a JWT.
- The token is stored locally and automatically sent as `Authorization: Bearer` in all `/api` requests.

## Run Server for Dashboards
```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```