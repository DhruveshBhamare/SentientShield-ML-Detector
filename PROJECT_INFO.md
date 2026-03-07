# SentientShield & NeuralFort: Complete Project Guide

## 1. Project Overview
**SentientShield** is a next-generation cybersecurity platform that combines classical Machine Learning with Generative AI to detect, analyze, and mitigate web-based threats in real-time. It features **NeuralFort**, an autonomous infrastructure resilience framework that ensures system stability through self-healing actions.

### Key Capabilities
- **Real-Time Threat Detection**: Identifies SQL Injection, XSS, DDoS, Brute Force, and more using XGBoost.
- **Generative AI Analysis**: Uses LLMs (Llama 3) to generate human-readable SOC incident reports.
- **Semantic Search (RAG)**: Retrieves relevant CVEs and past incidents using vector embeddings.
- **Autonomous Response**: The NeuralFort framework automatically blocks IPs and restarts services upon detecting anomalies.
- **Interactive Dashboards**: Cinematic, particle-effect driven UI for real-time monitoring.

---

## 2. System Architecture

### **Backend (API)**
- **Framework**: FastAPI (Python)
- **Performance**: Asynchronous non-blocking I/O.
- **Security**: JWT Authentication, CORS protection.
    
### **Machine Learning Engine**
- **Structured Data Model**: **XGBoost Classifier** (Best performing) & Random Forest.
    - Features: Payload size, headers, response time, IP reputation, etc.
    - Metrics: ~95% Accuracy, ~92% F1-Score.
- **NLP Models**:
    - **DistilBERT**: For log severity classification.
    - **MiniLM**: For vector embeddings (Semantic Search).
    - **BART (Zero-Shot)**: For dynamic threat labeling.
    - **Llama 3**: For generating text-based insights and reports.

### **Frontend**
- **Technology**: Vanilla JS, HTML5, CSS3 (No heavy frameworks).
- **Features**: Real-time WebSockets (`/ws/realtime`), Particle Animations, Glassmorphism UI.

### **Resilience (NeuralFort)**
- **Monitoring**: Tracks CPU, RAM, Disk, and Network I/O.
- **Self-Healing**: Automatically mitigates risks (e.g., stopping high-load processes).

---

## 3. Installation & Setup

### **Prerequisites**
- Python 3.8 or higher
- Git

### **Step-by-Step Guide**

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Train Models** (Required before first run)
    This script generates the necessary ML artifacts in the `artifacts/` directory.
    ```bash
    python scripts/train.py
    ```

3.  **Start the Application**
    ```bash
    # Option A: Using the provided script (Windows)
    scripts\start_uvicorn.bat

    # Option B: Manual command
    python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
    ```

---

## 4. Usage Guide (Live Deployment)

### **Accessing the Live Dashboards**
The project has been deployed via secure tunnels for live access:
- **Main Command Center (Live)**: [https://purple-apples-stare.loca.lt](https://purple-apples-stare.loca.lt)
- **Analytics Dashboard (Live)**: [https://sad-lights-slide.loca.lt](https://sad-lights-slide.loca.lt)

*Note: These links are active as long as the local tunnel is running. If the links expire, run `lt --port 8000` and `lt --port 8502` to regenerate them.*

### **Local Access**
- **Main Dashboard**: [http://localhost:8000/static/premium.html](http://localhost:8000/static/premium.html)
- **NeuralFort Control**: [http://localhost:8000/static/neuralfort_dashboard.html](http://localhost:8000/static/neuralfort_dashboard.html)
- **Analytics Dashboard**: [http://localhost:8502/](http://localhost:8502/)

### **Feature Walkthrough**

#### **1. SentientBot AI Assistant**
- **What it is**: A chatbot powered by RAG and LLMs.
- **How to use**: Type questions like *"Explain the latest SQL injection trends"* or *"What does CVE-2021-44228 mean?"*.

#### **2. Predictive Risk Scoring**
- **What it is**: Calculates a risk score (0-100) for a specific log line.
- **How to use**:
    1. Go to the "Predictive Risk Scoring" card.
    2. Paste a log line.
    3. Set an Asset Value (0.0 - 1.0).
    4. Click "Compute Risk".

#### **3. SOC Report Generator**
- **What it is**: Creates a professional incident report.
- **How to use**: Paste multiple suspicious log lines into the generator and click "Generate". The AI will summarize the attack vector, impact, and remediation steps.

#### **4. Threat Monitor**
- **What it is**: A live feed of detected threats.
- **How to use**: Watch the table at the bottom of the dashboard. It updates in real-time via WebSockets.

---

## 5. NeuralFort Framework Details

NeuralFort is the "immune system" of the platform.

- **Activation**: The framework requires an activation key (simulated in this project).
- **Capabilities**:
    - **Anomaly Detection**: Uses Isolation Forest to detect statistical outliers in system metrics.
    - **Healing Actions**:
        - `BLOCK_IP`: Blocks malicious IP addresses.
        - `RESTART_SERVICE`: Restarts a failing service.
        - `SCALE_RESOURCES`: Simulates resource scaling.
        - `CLEAR_CACHE`: Frees up system memory.

---

## 6. Machine Learning Model Report

*(Consolidated from Model report.txt)*

### **Model Architecture**
The core detection model is an **XGBoost Classifier** trained on synthetic web traffic data.
- **Objective**: `multi:softprob` (Multi-class classification with probability outputs).
- **Hyperparameters**: ~400 trees, Max depth 6, Learning rate 0.1.

### **Features Used**
1.  `request_type`: HTTP Method (GET, POST, etc.) - One-hot encoded.
2.  `headers`: TF-IDF vectorized text.
3.  `payload_size`: Numeric (Imputed & Scaled).
4.  `response_time`: Numeric (Imputed & Scaled).
5.  `ip_reputation`: Numeric (0-100).
6.  `url`: TF-IDF vectorized text.
7.  `user_agent`: TF-IDF vectorized text.
8.  `anomaly_score`: Statistical anomaly score.

### **Performance**
- **Accuracy**: ~95.6%
- **Macro F1-Score**: ~92.7%
- **ROC AUC**: ~99.5%

---

## 7. Deployment (Cloud & Local)

### **Permanent Cloud Hosting (Recommended)**
Since the code is already synchronized with your GitHub repository, you can deploy it permanently using these services:

#### **Option 1: Render.com (Blueprint)**
1.  Log in to [Render.com](https://render.com/) with your GitHub account.
2.  Click **New +** -> **Blueprint**.
3.  Select your `SentientShield-ML-Detector` repository.
4.  Render will automatically detect the `render.yaml` file and create two services:
    *   **sentientshield-api**: The FastAPI backend.
    *   **sentientshield-dashboard**: The Streamlit analytics UI.
5.  Click **Apply**. Your project will be live with a permanent `*.onrender.com` URL.

#### **Option 2: Hugging Face Spaces (Free ML Hosting)**
1.  Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2.  Select **SDK: Docker**.
3.  Connect your GitHub repository.
4.  Rename `Dockerfile.hf` to `Dockerfile` in the root (Hugging Face requires it).
5.  It will build and host both services in a single container for free.

### **Docker (Local Testing)**
If you have Docker installed, you can run the entire stack locally:
```bash
docker-compose up --build
```
*   **API**: [http://localhost:8000](http://localhost:8000)
*   **Analytics**: [http://localhost:8501](http://localhost:8501)

---

## 8. Directory Structure

- `api/`: Backend code.
    - `main.py`: App entry point.
    - `services/`: ML and Logic services.
    - `routers/`: API endpoints.
- `frontend/static/`: UI files.
- `scripts/`: Training and utility scripts.
- `artifacts/`: Saved models and metadata.
- `data/`: Datasets and Knowledge Bases.
