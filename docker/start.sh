#!/bin/bash

# 0. Initialize production environment (directories, dataset, model)
echo "Initializing Production Environment..."
export PYTHONPATH=$PYTHONPATH:.
python -m scripts.setup_production

# 1. Start the FastAPI Backend in the background
echo "Starting FastAPI Backend..."
# We use nohup to keep it running, and redirect logs
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# 2. Wait a few seconds for the API to initialize
echo "Waiting for API to launch..."
sleep 5

# 3. Start the Streamlit Frontend
# Hugging Face Spaces expects the app to listen on port 7860
echo "Starting Streamlit Dashboard..."
export API_URL="http://localhost:8000"
streamlit run src/streamlit_app.py --server.port 7860 --server.address 0.0.0.0
