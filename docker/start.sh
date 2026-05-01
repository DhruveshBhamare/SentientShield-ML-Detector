#!/bin/bash

# 0. Initialize production environment (directories, dataset, model)
echo "Initializing Production Environment..."
export PYTHONPATH=$PYTHONPATH:.
python -m scripts.setup_production

# 1. Start the FastAPI Backend in the background
echo "Starting FastAPI Backend..."
# We use nohup to keep it running, and redirect logs
# For HF Spaces, we run on 8000 internally
nohup uvicorn src.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &

# 2. Start Nginx reverse proxy (public port 7860)
echo "Starting Nginx Reverse Proxy..."
# Create temporary directories for Nginx (as non-root)
mkdir -p /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp
exec nginx -c /app/docker/nginx.conf -g "daemon off;"
