import os
import numpy as np
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "web_threat_dataset.csv")

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "curl/8.5.0",
    "python-requests/2.31",
    "Chrome/124.0",
    "Safari/605.1.15",
]
ATTACK_TYPES = [
    "sql_injection",
    "xss",
    "ddos",
    "brute_force",
    "credential_stuffing",
]

np.random.seed(42)


def _random_url():
    base = np.random.choice([
        "/", "/login", "/search", "/api/data", "/admin", "/index", "/profile", "/products"
    ])
    q = "".join(np.random.choice(list("abcdefghijklmnopqrstuvwxyz0123456789"), size=np.random.randint(0, 15)))
    return f"{base}?q={q}" if np.random.rand() < 0.7 else base


def _attack_signatures(attack_type: str, url: str, headers: str, payload: float, resp_time: float, anomaly: float):
    if attack_type == "sql_injection":
        url += ("' OR '1'='1" if np.random.rand() < 0.7 else "")
        headers += "; X-SQL-Test: ' OR '1'='1"
        payload *= np.random.uniform(1.2, 1.6)
        anomaly = max(anomaly, np.random.uniform(0.7, 0.95))
    elif attack_type == "xss":
        url += ("<script>alert('x')</script>" if np.random.rand() < 0.6 else "")
        headers += "; X-XSS-Test: <img src=x onerror=alert(1)>"
        anomaly = max(anomaly, np.random.uniform(0.65, 0.9))
    elif attack_type == "ddos":
        resp_time *= np.random.uniform(1.5, 2.5)
        payload *= np.random.uniform(1.1, 1.5)
        anomaly = max(anomaly, np.random.uniform(0.75, 0.98))
    elif attack_type == "brute_force":
        payload *= np.random.uniform(0.8, 1.1)
        anomaly = max(anomaly, np.random.uniform(0.6, 0.85))
    elif attack_type == "credential_stuffing":
        headers += "; X-Auth-Attempt: multiple"
        anomaly = max(anomaly, np.random.uniform(0.65, 0.9))
    return url, headers, payload, resp_time, anomaly


def generate(n_total: int = 50000, normal_ratio: float = 0.5):
    os.makedirs(DATA_DIR, exist_ok=True)

    n_normal = int(n_total * normal_ratio)
    n_threat = n_total - n_normal
    n_per_attack = n_threat // len(ATTACK_TYPES)

    rows = []

    # Normal traffic
    for _ in range(n_normal):
        method = np.random.choice(HTTP_METHODS, p=[0.55, 0.35, 0.05, 0.05])
        payload = float(np.random.gamma(shape=2.0, scale=400.0))
        resp_time = float(np.random.gamma(shape=2.0, scale=100.0))
        ip_rep = float(np.clip(np.random.normal(70, 20), 0, 100))
        anomaly = float(np.clip(np.random.normal(0.2, 0.1), 0, 1))
        headers = "; ".join([
            f"User-Agent: {np.random.choice(USER_AGENTS)}",
            "Accept: application/json",
            f"X-Forwarded-For: 10.{np.random.randint(0,255)}.{np.random.randint(0,255)}.{np.random.randint(0,255)}",
            f"Content-Type: {np.random.choice(['application/json','text/html','application/x-www-form-urlencoded'])}"
        ])
        url = _random_url()
        ua = np.random.choice(USER_AGENTS)
        rows.append({
            "request_type": method,
            "headers": headers,
            "payload_size": payload,
            "response_time": resp_time,
            "ip_reputation": ip_rep,
            "url": url,
            "user_agent": ua,
            "anomaly_score": anomaly,
            "label": 0,
            "attack_type": "normal",
            "timestamp": datetime.utcnow().isoformat(),
            "source_ip": f"192.168.{np.random.randint(0,255)}.{np.random.randint(0,255)}",
            "response_code": np.random.choice([200, 201, 204, 302], p=[0.6, 0.1, 0.2, 0.1]),
        })

    # Threat traffic, balanced across attack types
    for attack in ATTACK_TYPES:
        for _ in range(n_per_attack):
            method = np.random.choice(HTTP_METHODS, p=[0.45, 0.45, 0.05, 0.05])
            payload = float(np.random.gamma(shape=2.2, scale=500.0))
            resp_time = float(np.random.gamma(shape=2.0, scale=140.0))
            ip_rep = float(np.clip(np.random.normal(40, 30), 0, 100))
            anomaly = float(np.clip(np.random.normal(0.7, 0.15), 0, 1))
            headers = "; ".join([
                f"User-Agent: {np.random.choice(USER_AGENTS)}",
                "Accept: application/json",
                f"X-Forwarded-For: 172.{np.random.randint(0,255)}.{np.random.randint(0,255)}.{np.random.randint(0,255)}",
                f"Content-Type: {np.random.choice(['application/json','text/html','application/x-www-form-urlencoded'])}"
            ])
            url = _random_url()
            ua = np.random.choice(USER_AGENTS)
            url, headers, payload, resp_time, anomaly = _attack_signatures(attack, url, headers, payload, resp_time, anomaly)
            rows.append({
                "request_type": method,
                "headers": headers,
                "payload_size": payload,
                "response_time": resp_time,
                "ip_reputation": ip_rep,
                "url": url,
                "user_agent": ua,
                "anomaly_score": anomaly,
                "label": 1,
                "attack_type": attack,
                "timestamp": datetime.utcnow().isoformat(),
                "source_ip": f"203.0.{np.random.randint(0,255)}.{np.random.randint(0,255)}",
                "response_code": np.random.choice([200, 400, 403, 404, 429, 500], p=[0.25,0.15,0.2,0.1,0.2,0.1]),
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved synthetic dataset: {OUTPUT_PATH} with {len(df)} rows")


if __name__ == "__main__":
    generate()