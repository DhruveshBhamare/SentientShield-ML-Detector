# SentientShield AI Cybersecurity Platform

**SentientShield** is an advanced AI-powered web threat detection and autonomous infrastructure resilience system.

## 🚀 Production Deployment (Quick Start)

This project is optimized for deployment using **GitHub + HuggingFace Hub + Render**.

### 1. Large Model Hosting (HuggingFace)
To keep the repository size small (< 300MB), the 13GB of ML models are hosted on HuggingFace Hub.
1. Create a repository on [HuggingFace Hub](https://huggingface.co/new) (e.g., `your-username/SentientShield-ML-Model`).
2. Upload the following files to your HF repo:
   - `best_model.joblib`
   - `metadata.json`
3. Set the environment variable `HF_HUB_REPO_ID` to your repository ID in the Render dashboard.

### 2. Deployment to Render
The project includes a `render.yaml` blueprint for automatic deployment.
1. Connect your GitHub repository to [Render](https://render.com/).
2. Render will detect `render.yaml` and create two services:
   - **sentientshield-api**: FastAPI backend.
   - **sentientshield-analytics**: Streamlit dashboard.
3. Configure the following **Environment Variables** on Render:
   - `HF_HUB_REPO_ID`: Your HuggingFace model repo ID.
   - `HF_TOKEN`: (Optional) Required to sync retrained models back to HuggingFace.
   - `JWT_SECRET`: A secure random string for authentication.
   - `NVIDIA_API_KEY`: Your NVIDIA AI Foundation API key.
   - `NVIDIA_MODEL`: Set to `qwen/qwen3.5-397b-a17b` (default).
   - `TRUSTED_ORIGINS`: Set to your production domain or `*`.

### 3. Local Deployment (Docker)
Run the entire stack locally with a single command:
```bash
docker-compose up --build
```
- **Main Dashboard**: `http://localhost:8000/static/premium.html`
- **Analytics Dashboard**: `http://localhost:8501`

---

## 🛠️ Features
- **AI-Powered Threat Detection**: Real-time identification of web attacks (SQLi, XSS, DDoS) using XGBoost.
- **SentientBot 2.0 (Powered by NVIDIA Qwen 3.5)**: Interactive security co-pilot with "Thinking" reasoning capabilities and a 16k token context window.
- **NeuralFort Autonomous Resilience**: Self-healing infrastructure that monitors and mitigates system anomalies.
- **Automated SOC Reports**: Generates professional incident reports using state-of-the-art LLMs.

## 📂 Project Structure
- `api/`: FastAPI backend implementation.
- `frontend/static/`: Cinematic UI with particle animations.
- `streamlit_app.py`: Real-time analytics dashboard.
- `scripts/`: Utilities for training, retraining, and data generation.
- `.github/workflows/`: CI/CD automation for production deployment.

## 📄 License
This project is licensed under the MIT License.
