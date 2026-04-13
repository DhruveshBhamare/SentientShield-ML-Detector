# Cloudflare Tunnel (Permanent Live Links)

This guide documents how to make **SentientShield** accessible over the internet using a **named Cloudflare Tunnel**.

Important reality check:
- This is only “permanent” if the machine (or server) running the tunnel stays on.
- If you want true always-on hosting without your machine running, use the cloud options in [DEPLOY.md](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docs/DEPLOY.md) (Render / Railway / HuggingFace Spaces).

## What you get

- Public HTTPS domain for the API (FastAPI) on port `10000`
- Public HTTPS domain for Analytics (Streamlit) on port `8501`
- No port-forwarding / router config

## Option A (Recommended): Run everything with Docker + Tunnel

### 1) Prerequisites

- A Cloudflare account
- A domain added to Cloudflare (DNS managed by Cloudflare)
- `cloudflared` installed on your machine (for the one-time tunnel creation/login)

### 2) Create a named tunnel (one-time)

From your machine (not inside Docker):

```powershell
cloudflared login
cloudflared tunnel create sentientshield
```

This creates:
- A tunnel UUID (shown in the output)
- A credentials JSON file in your user profile (Cloudflare-managed)

### 3) Add DNS routes (one-time)

Pick hostnames you want (examples below) and route them to the tunnel:

```powershell
cloudflared tunnel route dns sentientshield api.YOUR_DOMAIN
cloudflared tunnel route dns sentientshield analytics.YOUR_DOMAIN
```

### 4) Put tunnel credentials into the repo (DO NOT COMMIT)

Copy the generated credentials file into `docker/cloudflared/`:

- Source (typical Windows path): `%HOMEPATH%\.cloudflared\<TUNNEL_UUID>.json`
- Destination: `docker/cloudflared/<TUNNEL_UUID>.json`

### 5) Create the tunnel config used by Docker

Copy the example and fill in your values:

- Copy `docker/cloudflared/config.yml.example` to `docker/cloudflared/config.yml`
- Replace:
  - `TUNNEL_UUID`
  - `api.YOUR_DOMAIN`
  - `analytics.YOUR_DOMAIN`

### 6) Start SentientShield + Tunnel

From the repo root:

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.cloudflare.yml up -d --build
```

### 7) Verify

- API: `https://api.YOUR_DOMAIN/api/status`
- Streamlit: `https://analytics.YOUR_DOMAIN`

## Option B: Tunnel a locally-running dev setup (no Docker)

If you already run:
- API at `http://127.0.0.1:10000`
- Streamlit at `http://127.0.0.1:8501`

You can create a config file in your user profile (preferred by cloudflared) and run:

```powershell
cloudflared tunnel run sentientshield
```

Use the same ingress structure as in `docker/cloudflared/config.yml.example`, but point `service:` targets to `http://127.0.0.1:10000` and `http://127.0.0.1:8501`.

## Keeping it running after reboot

- Cloudflared supports installing itself as a Windows Service:

```powershell
cloudflared service install
```

This is best paired with:
- Docker Desktop “Start Docker Desktop when you log in”, and
- running the compose stack with `restart: always` (already set for API/Streamlit).

If you run without Docker, you can also register Windows startup tasks for the API + Streamlit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\install_startup_tasks.ps1
```
