# Deployment Guide for SentientShield

This project is containerized using Docker, making it easy to deploy to any cloud provider that supports Docker (e.g., Render, Railway, AWS, DigitalOcean) or run locally in a production-like environment.

## 🚀 Quick Start (Local Docker)

1.  **Install Docker Desktop**: Ensure Docker is installed and running.
2.  **Build and Run**:
    ```bash
    docker-compose up --build
    ```
3.  **Access the App**:
    *   **Dashboard (Streamlit):** [http://localhost:8501](http://localhost:8501)
    *   **API & Premium UI:** [http://localhost:8000](http://localhost:8000)
    *   **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ☁️ Cloud Deployment Options

### Option 1: Render.com (Recommended for ease)

1.  **Create a New Web Service** for the API:
    *   Connect your GitHub repository.
    *   **Runtime**: Docker
    *   **Build Command**: (Docker handles this)
    *   **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port 10000` (Render uses port 10000 by default, update Dockerfile or env var `PORT` if needed).
    *   **Environment Variables**:
        *   `JWT_SECRET`: Generate a secure random string.
        *   `TRUSTED_ORIGINS`: Add your frontend URL (e.g., `https://your-streamlit-app.onrender.com`).

2.  **Create a New Web Service** for Streamlit:
    *   Connect the same repository.
    *   **Runtime**: Docker
    *   **Environment Variables**:
        *   `API_URL`: The URL of your deployed API (e.g., `https://sentientshield-api.onrender.com`).
    *   **Start Command**: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`

### Option 2: Railway.app

1.  **New Project** -> **Deploy from GitHub Repo**.
2.  Railway will detect the `Dockerfile`.
3.  You might need to configure two separate services (one for API, one for Streamlit) or use a `railway.json` config.
4.  Set the `API_URL` variable in the Streamlit service to point to the API service internal domain.

### Option 3: VPS (AWS EC2 / DigitalOcean Droplet)

1.  SSH into your server.
2.  Clone the repository.
3.  Install Docker & Docker Compose.
4.  Run `docker-compose up -d --build`.
5.  Configure Nginx/Traefik as a reverse proxy if you want custom domains and HTTPS.

## 📦 Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `JWT_SECRET` | Secret key for JWT token generation | `change-me-in-prod` |
| `API_URL` | URL of the backend API (for Streamlit) | `http://api:8000` (internal) |
| `TRUSTED_ORIGINS` | CORS allowed origins (comma separated) | `http://localhost,...` |
| `RETRAIN_INTERVAL_SECONDS` | Interval for model retraining task | `86400` (24h) |

## ⚠️ Important Notes

*   **Models**: The heavy ML models are downloaded at build time or runtime. Ensure your deployment environment has at least **2GB - 4GB RAM**.
*   **Persistence**: Docker containers are ephemeral. If you need to persist the `artifacts/` (retrained models) or `data/` (logs), ensure you mount volumes (Docker) or use persistent disks (Cloud).
