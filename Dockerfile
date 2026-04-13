FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for zero-cost deployment (Hugging Face)
ENV SENTIENTSHIELD_LIGHT_MODE="true" \
    NVIDIA_API_KEY="" \
    THREAT_INGEST_PUBLIC_FALLBACK="true" \
    THREAT_INGEST_INTERVAL_SECONDS="60" \
    THREAT_INGEST_ENABLED="true" \
    HF_HUB_REPO_ID="DhruveshBhamare/SentientShield-ML-Model" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user

# Create a non-root user (Hugging Face requirement)
RUN useradd -m -u 1000 user && \
    chown -R user:user /app /var/lib/nginx /var/log/nginx /run

# Grant execution permissions
RUN chmod +x docker/start.sh

# Run setup (as root to ensure directories are created, then fix permissions)
RUN python -m scripts.setup_production && \
    chown -R user:user /app

USER user
ENV PATH=/home/user/.local/bin:$PATH

# Expose the port Hugging Face Spaces expects
EXPOSE 7860

# Run the wrapper script
CMD ["./docker/start.sh"]
