import pytest
from fastapi.testclient import TestClient
from src.main import app
import os

client = TestClient(app)

def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert "pong" in response.text

@pytest.mark.skipif(not os.path.exists("artifacts/best_model.joblib"), reason="Models not downloaded")
def test_predict_endpoint_exists():
    # Basic check to see if the endpoint is reachable, 
    # even if it returns 500 because of missing models
    response = client.post("/api/predict", json={
        "request_type": "GET",
        "payload_size": 100,
        "response_time": 50,
        "ip_reputation": 99,
        "anomaly_score": 0.01
    })
    # If models are missing, it might 500, but the route exists. 
    # It might return 401 or 403 because we don't provide a token.
    assert response.status_code in [200, 401, 403, 500]
