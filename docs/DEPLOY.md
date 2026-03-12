# Deployment Guide for SentientShield

## ☁️ Cloud Deployment Options

### Option 1: Hugging Face Spaces (Recommended for ML)
This is the easiest way to deploy machine learning demos for free.

1.  **Create a Space:**
    *   Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
    *   **Space Name:** `sentientshield-ml`
    *   **SDK:** Select **Docker**.
    *   **Space Hardware:** CPU Basic (Free) is usually sufficient, but upgrade if models are slow.

2.  **Upload Code:**
    *   You can connect your GitHub repository directly if you authorize Hugging Face.
    *   **OR** (Manual Way):
        *   Clone the empty Space repository locally.
        *   Copy all files from this project into that folder.
        *   **Important:** Rename `Dockerfile.hf` to `Dockerfile`. Hugging Face looks for `Dockerfile` by default.
        *   Push the code to the Hugging Face repo.

3.  **Automatic Build:**
    *   Hugging Face will automatically build the container using the `Dockerfile` (which runs `start.sh`).
    *   It will start both the API (port 8000) and Streamlit (port 7860) in the same container.
    *   Your app will be live at `https://huggingface.co/spaces/YOUR_USERNAME/sentientshield-ml`.

---

### Option 2: Railway.app (Easiest Full-Stack)
Railway is a robust alternative to Render that often handles Docker configurations better.

1.  **Login:** Go to [railway.app](https://railway.app/) and login with GitHub.
2.  **New Project:** Click **New Project** -> **Deploy from GitHub repo**.
3.  **Select Repository:** Choose `SentientShield-ML-Detector`.
4.  **Configuration:**
    *   Railway will detect the `docker-compose.yml` file.
    *   It will create two services: `api` and `streamlit`.
    *   **Variables:** Go to the `api` service -> Variables and add `JWT_SECRET`.
    *   **Networking:**
        *   Railway creates internal networking automatically.
        *   Check the `streamlit` service variables. Ensure `API_URL` is set to the **internal service DNS** of the API (e.g., `http://api:8000` or the Railway-provided internal URL).
5.  **Deploy:** Click Deploy.

---

### Option 3: Render.com (Blueprint)
See `render.yaml` in the root directory.
1.  Go to Render Dashboard -> **New Blueprint**.
2.  Connect your repo.
3.  Render will auto-deploy the following services:
    *   **sentientshield-api**: FastAPI backend.
    *   **sentientshield-analytics**: Streamlit dashboard.
    *   **sentientshield-workflows**: Distributed background tasks (Render Workflows SDK).

---

## 🔑 Environment Variables

For a permanent and secure deployment, set the following variables in your cloud provider's dashboard:

| Variable | Description | Recommended Value |
| :--- | :--- | :--- |
| `NVIDIA_API_KEY` | NVIDIA AI Foundation API Key | Your API Key |
| `HF_TOKEN` | HuggingFace Write Token | For model persistence |
| `HF_HUB_MODEL_ID` | HuggingFace Model Repo | e.g. `user/sentientshield-models` |
| `JWT_SECRET` | Secret for Auth | Long random string |
| `TRUSTED_ORIGINS` | CORS Origins | `*` or your domains |
| `NVIDIA_MODEL` | LLM Model ID | `qwen/qwen3.5-397b-a17b` |

---

## 🚀 Local Docker (Testing)

1.  **Build and Run**:
    ```bash
    docker-compose up --build
    ```
2.  **Access**:
    *   Dashboard: [http://localhost:8501](http://localhost:8501)
    *   API: [http://localhost:8000](http://localhost:8000)
