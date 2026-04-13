# SentientShield-ML-Detector — Complete Codebase Explanation (Single Document)

This document explains the full project end-to-end: what each subsystem does, how requests flow through the app, where data is stored, and how to run/deploy it.

If you want flowcharts, see [FLOWS.md](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docs/FLOWS.md).

---

## 1) What this project is

SentientShield is an AI-assisted cybersecurity demo platform with three main user experiences:

1. **Command Center (static web UI)** for operators to run scans, pipeline analysis, and view results.
2. **Threat Analytics (Streamlit dashboard)** for trend charts and “record event” injection.
3. **Backend API (FastAPI)** powering both UIs and exposing ML + security automation endpoints.

Key features implemented in the code:
- Web-attack prediction via a classical ML model (XGBoost/Sklearn artifacts).
- Log triage pipeline: severity, threat type, embeddings, vector similarity, MITRE mapping, risk scoring, SOC report.
- “NeuralFort” resilience and website analysis endpoints.
- Optional scheduled retraining loop.
- Local and containerized deployments, plus demo tunneling.

---

## 2) Repository layout

Top-level:
- `src/` — application code (FastAPI + Streamlit + services)
- `scripts/` — training/retraining/setup utilities + workflow runner
- `docker/` — compose + Nginx proxy + startup script
- `docs/` — documentation
- `artifacts/` — runtime model metadata (and optional joblib artifacts)
- `data/` — datasets and knowledge base JSON

Important paths (jump links):
- API entrypoint: [main.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/main.py)
- Command Center UI: [premium.html](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/static/premium.html), [app.js](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/static/app.js), [styles.css](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/static/styles.css)
- Streamlit UI: [streamlit_app.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/streamlit_app.py)
- Log pipeline + stores: [log_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/log_service.py)
- Intelligence pipeline for /api/predict raw logs: [intel_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/intel_service.py)
- NeuralFort: [neuralfort router](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/neuralfort.py), [neuralfort service](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/neuralfort.py)
- Model loading: [loader.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/models/loader.py)

---

## 3) FastAPI app: how the backend is assembled

### 3.1 App creation and middleware
The FastAPI app is created in [main.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/main.py).

It sets up:
- CORS with `TRUSTED_ORIGINS`
- Rate limiting via `slowapi`
- Secure headers middleware
- Static file serving for the UI (`/static/*`)
- A redirect to the Command Center entry (`/` → `/static/premium.html#bot`)

### 3.2 Routers registered
[main.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/main.py) mounts multiple routers:
- Status endpoints: [status.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/status.py)
- Predict endpoints: [predict.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py)
- Project-info endpoints: [project.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/project.py)
- Logs + pipeline + trends endpoints: [logs.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/logs.py)
- Dashboard endpoints + websocket: [dashboard.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/dashboard.py)
- NeuralFort endpoints: [neuralfort.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/neuralfort.py)

### 3.3 Startup tasks
The app uses startup events to:
- Kick off the retraining loop (async) via [scheduler.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/tasks/scheduler.py)
- Preload artifacts in the background (so startup is fast on constrained hosts)

---

## 4) Authentication: JWT dependency

Protected endpoints require:
`Authorization: Bearer <token>`

Implementation:
- Token parsing is handled by FastAPI’s `HTTPBearer`.
- Signature verification and claims checks are in [security.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/configs/security.py).

Developer convenience:
- `/api/dev-token` returns a short-lived token for local testing: [status.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/status.py#L42-L52).

---

## 5) Static Command Center UI (premium.html + app.js)

### 5.1 How it’s served
The UI files live under `src/static/` and are mounted by FastAPI at `/static`.

Open in browser:
- `/static/premium.html`

### 5.2 What app.js does
[app.js](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/static/app.js) is the frontend controller:
- Binds buttons and inputs in `premium.html`
- Calls backend endpoints with `fetch` (JSON)
- Renders results into UI panels
- Stores auth token in localStorage (`ss_token`) and sends it as Bearer token

### 5.3 Main UI → API calls (high impact)
Typical calls include:
- `/api/status` (health + model meta)
- `/api/predict` (web attack prediction)
- `/api/logs/pipeline/run` (log triage pipeline)
- `/api/logs/record-event` + `/api/logs/trends/*` (analytics storage + charts)
- `/neuralfort/*` (resilience + website analysis)

---

## 6) Streamlit Threat Analytics Dashboard (src/streamlit_app.py)

Streamlit runs as a separate web server and behaves like an API client:
- Reads `API_URL` to know where the FastAPI backend is.
- Uses `requests` to call backend endpoints and render charts/tables.

Key behaviors:
- “Record Event” posts a raw message to `/api/logs/record-event` and the backend computes severity, threat type, risk, and stores it.
- Charts query `/api/logs/trends/*` endpoints to plot top attack types, frequency, MITRE distribution, risk trends, recent events.

Implementation: [streamlit_app.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/streamlit_app.py).

---

## 7) Web-attack prediction (classical model) — /api/predict

Endpoint: [predict.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py#L17-L89)

Steps:
1. Load model + metadata via [loader.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/models/loader.py).
2. Convert request features to a single row dict.
3. Run `predict_proba()` (preferred) or `predict()` fallback.
4. If `raw_log` exists, call the intelligence pipeline to generate a SOC report and store it in a local DB (see next section).
5. Append an API call log entry to `logs/api_calls.jsonl`.

Output:
- predicted label
- confidence and/or probabilities
- optional `intelligence` report

---

## 8) Intelligence pipeline (intel_service) used by /api/predict raw logs

The intelligence pipeline is implemented in [intel_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/intel_service.py).

What it does:
- Produces a “SOC-style” report for a raw log string.
- Stores reports in a local SQLite DB at `logs/intelligence.db`.
- Provides an API to fetch stored reports: [dashboard.py /api/intel/reports](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/dashboard.py#L13-L26).

Important note:
- This pipeline is intentionally “always functional” by using mocked ML primitives for severity/threat and random embeddings if needed. That keeps demos stable even on low-end environments.

---

## 9) Log triage pipeline (PipelineEngine) — /api/logs/pipeline/run

The primary log triage pipeline is implemented in [log_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/log_service.py) and is called via:
- [logs.py pipeline endpoint](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/logs.py#L270-L298)

Key stages:
1. Severity classification (`DistilBERTLogClassifier`)
2. Threat type classification (`DistilBERTLogClassifier`)
3. Embedding generation (`MiniLMEmbedder`)
4. Optional vector ingest + similarity search (`FaissVectorIndex` or `InMemoryVectorIndex`)
5. MITRE ATT&CK mapping + history (`MITREAttckMapper`)
6. Risk scoring (`RiskScoringEngine`) including frequency + anomaly scoring
7. Optional SOC report (`SOCReportGenerator`)

The pipeline returns a single JSON “analysis bundle”.

---

## 10) Storage: where data goes

### 10.1 Trend/events DB (SQLite by default, Postgres optional)
The logs router uses:
- `TrendStore(db_path)` if `DATABASE_URL` is not set (SQLite).
- `PGTrendStore(DATABASE_URL)` if set (Postgres).

This stores:
- recorded events (severity, threat_type, risk, timestamp)
- trend aggregates (queries computed from stored events)
- MITRE mapping history (also stored under the SQLite db path used by the mapper)

Code pointers:
- Store + queries: [TrendStore](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/log_service.py)
- Router endpoints: [logs.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/logs.py)

### 10.2 SOC report DB from intelligence pipeline
- Stored in `logs/intelligence.db`
- Read via `/api/intel/reports`

Code pointers:
- DB writes: [intel_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/intel_service.py)
- DB reads: [dashboard.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/dashboard.py#L13-L26)

### 10.3 JSONL logs for API calls/performance
Paths come from config:
- [config.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/configs/config.py)

Written by:
- `/api/predict` and several NeuralFort handlers.

---

## 11) NeuralFort subsystem

NeuralFort has two broad capabilities:

1. **Website analysis**: analyze a target website and return security score, threat breakdown, recommendations, risk estimate.
2. **Resilience framework**: maintain a framework state (system metrics, anomalies, healing actions) and expose it via API.

Code pointers:
- API endpoints: [neuralfort.py router](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/neuralfort.py)
- Core engine: [neuralfort.py service](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/neuralfort.py)
- Analysis helpers: [website_analysis.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/website_analysis.py)

---

## 12) Batch workflow processing

The logs router includes a batch workflow trigger:
- `POST /api/logs/workflow/batch-process`

Behavior:
- If `RENDER=true`, it uses Render workflows SDK to start a task.
- Otherwise, it calls the workflow function locally.

Worker implementation:
- [render_workflows.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/scripts/render_workflows.py)

---

## 13) Retraining loop (scheduled)

The project includes a background asyncio loop that periodically calls:
- `scripts.retrain.daily_retrain()`

Code pointers:
- Scheduler loop: [scheduler.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/tasks/scheduler.py)
- Retrain implementation: [retrain.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/scripts/retrain.py)

---

## 14) “Light mode” (memory constrained environments)

Environment variable:
- `SENTIENTSHIELD_LIGHT_MODE=true`

Purpose:
- Avoid loading heavy transformer pipelines and embeddings when RAM is limited.

Implementation:
- [log_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/log_service.py)
- [neuralfort.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/neuralfort.py)

---

## 15) How to run

### 15.1 Local (two terminals)

FastAPI:
```bash
SENTIENTSHIELD_LIGHT_MODE=true uvicorn src.main:app --host 0.0.0.0 --port 10000
```

Streamlit:
```bash
API_URL=http://127.0.0.1:10000 python -m streamlit run src/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

### 15.2 Docker Compose
Compose file: [docker-compose.yml](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docker/docker-compose.yml)

```bash
docker compose -f docker/docker-compose.yml up --build
```

### 15.3 HF Spaces (single public port)
Startup + proxy:
- [start.sh](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docker/start.sh)
- [nginx.conf](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docker/nginx.conf)

### 15.4 Live demo without hosting (Cloudflare Tunnel)
Tunnel your local API:
```bash
cloudflared tunnel --url http://localhost:10000
```

---

## 16) Summary: “where to look first”

- If the UI looks broken: [app.js](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/static/app.js) + browser console + API `/api/status`.
- If prediction breaks: [predict.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/predict.py) + [loader.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/models/loader.py).
- If pipeline analysis breaks: [logs.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/api/routers/logs.py) + [log_service.py](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/src/services/log_service.py).
- If dashboard charts are empty: verify TrendStore DB is writable and `/api/logs/record-event` writes rows.

