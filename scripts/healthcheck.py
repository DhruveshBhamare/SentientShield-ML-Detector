import requests
import sys
import os

def check_health():
    """Simple healthcheck for Docker and CI/CD monitoring."""
    port = os.getenv("PORT", "10000")
    url = f"http://localhost:{port}/ping"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200 and "pong" in response.text:
            print("Healthcheck PASSED")
            return True
        else:
            print(f"Healthcheck FAILED: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"Healthcheck FAILED: {e}")
        return False

if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
    sys.exit(0)
