# SentientShield-WebAttackPredictor FastAPI Microservice
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Initialize production environment
RUN python scripts/setup_production.py

# Environment defaults (override at runtime)
ENV JWT_SECRET="change-me-in-prod" \
    JWT_ALG="HS256" \
    JWT_ISSUER="" \
    JWT_AUDIENCE="" \
    TRUSTED_ORIGINS="http://localhost,http://127.0.0.1" \
    RETRAIN_INTERVAL_SECONDS="86400" \
    PYTHONUNBUFFERED=1

# Expose default port (Render will override)
EXPOSE 10000

# Start Uvicorn server with dynamic port pointing to src/main.py
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
