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

# 2. Wait a few seconds for the API to initialize
echo "Waiting for API to launch..."
sleep 5

# 3. Start Streamlit on an internal port (8501)
echo "Starting Streamlit Dashboard..."
export API_URL="http://127.0.0.1:8000"
export PUBLIC_BASE_URL=""
# We set baseUrlPath to analytics to match Nginx config
nohup streamlit run src/streamlit_app.py --server.port 8501 --server.address 127.0.0.1 --server.baseUrlPath analytics > streamlit.log 2>&1 &

# 4. Start Nginx reverse proxy (public port 7860)
echo "Starting Nginx Reverse Proxy..."
# Create temporary directories for Nginx (as non-root)
mkdir -p /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp
exec nginx -c /app/docker/nginx.conf -g "daemon off;"
