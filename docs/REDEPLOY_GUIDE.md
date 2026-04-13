# SentientShield Redeploy Guide (Perfect Repeatable Steps)

This guide is optimized for **re-deploying quickly** after you’ve already run SentientShield once.

Pick one path:
- **A. Quick public demo links (temporary)**: `trycloudflare.com` URLs (fastest)
- **B. Permanent hostnames (recommended)**: Named Cloudflare Tunnel on your own domain
- **C. Always-on cloud hosting**: Render / Railway / HuggingFace Spaces (no PC required)

---

## 0) One-time setup commands (do once per machine)

If you already have a working environment, skip this section.

### 0.1) Create a virtual environment

From repo root:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 0.2) Install Python dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 0.3) Initialize runtime artifacts (recommended)

This creates required folders and prepares baseline artifacts.

```powershell
python -m scripts.setup_production
```

### 0.4) (Optional) Install Cloudflare Tunnel CLI

If `cloudflared` is not already installed:

```powershell
winget install Cloudflare.cloudflared
```

Verify:

```powershell
cloudflared --version
```

## A) Quick public demo links (temporary) — repeat anytime

This creates new public URLs each time (not stable), but is the fastest “go live now”.

### A1) Start the API (FastAPI) on `127.0.0.1:10000`

From repo root:

```powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 10000
```

If you want to pin a specific Python executable:

```powershell
& "C:\\Path\\To\\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 10000
```

Verify the UI is served:
- Open `http://127.0.0.1:10000/static/premium.html`

Verify the API is reachable (protected endpoint example):

```powershell
$token = (Invoke-RestMethod http://127.0.0.1:10000/api/dev-token).token
Invoke-RestMethod http://127.0.0.1:10000/api/status -Headers @{ Authorization = "Bearer $token" }
```

If you want to verify API authentication:
- Get a dev token: `http://127.0.0.1:10000/api/dev-token`
- Then call `/api/status` with header `Authorization: Bearer <token>`

### A2) Start Streamlit (Analytics) on `127.0.0.1:8501`

In a second terminal:

```powershell
$env:API_URL='http://127.0.0.1:10000'
$env:PUBLIC_BASE_URL=''
python -m streamlit run src/streamlit_app.py --server.port 8501 --server.address 127.0.0.1
```

If you want to pin a specific Python executable:

```powershell
& "C:\\Path\\To\\python.exe" -m streamlit run src/streamlit_app.py --server.port 8501 --server.address 127.0.0.1
```

Verify:
- Open `http://127.0.0.1:8501`

### A3) Create the public links (2 tunnels)

In two more terminals:

```powershell
cloudflared tunnel --url http://127.0.0.1:10000 --edge-ip-version 4 --protocol http2
```

```powershell
cloudflared tunnel --url http://127.0.0.1:8501 --edge-ip-version 4 --protocol http2
```

Cloudflared prints:
- **Command Center (FastAPI UI)**: `https://<random>.trycloudflare.com/static/premium.html`
- **Streamlit**: `https://<random>.trycloudflare.com`

### A4) Stop everything

In each terminal, press `Ctrl + C`.

If you need to kill the processes by port:

```powershell
$p = (Get-NetTCPConnection -LocalPort 10000 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($p) { Stop-Process -Id $p -Force }

$p = (Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($p) { Stop-Process -Id $p -Force }
```

---

## B) Permanent public hostnames (recommended) — named Cloudflare Tunnel

Use this if you want stable URLs like:
- `https://api.yourdomain.com`
- `https://analytics.yourdomain.com`

This requires:
- Cloudflare account + domain on Cloudflare DNS
- Named tunnel created once, then reused forever

Follow the dedicated guide:
- [CLOUDFLARE_TUNNEL.md](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docs/CLOUDFLARE_TUNNEL.md)

### B0) One-time: create tunnel + DNS routes (Windows)

```powershell
cloudflared login
cloudflared tunnel create sentientshield
cloudflared tunnel route dns sentientshield api.YOUR_DOMAIN
cloudflared tunnel route dns sentientshield analytics.YOUR_DOMAIN
```

Get the tunnel UUID (optional helper):

```powershell
cloudflared tunnel list
```

### B0.1) One-time: run named tunnel locally (without Docker)

If you prefer a named tunnel without Docker:

```powershell
cloudflared tunnel run sentientshield
```

### B1) After you already created the tunnel once: redeploy is 1 command

### B1) After you already created the tunnel once: redeploy is 1 command

From repo root:

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.cloudflare.yml up -d --build
```

Check containers:

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.cloudflare.yml ps
```

View logs:

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.cloudflare.yml logs -f --tail 200
```

Verify:
- API: `https://api.YOUR_DOMAIN/api/dev-token`
- Command Center: `https://api.YOUR_DOMAIN/static/premium.html`
- Streamlit: `https://analytics.YOUR_DOMAIN`

Stop the stack:

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.cloudflare.yml down
```

### B2) Keep it running after reboot

Two common approaches:
- **Docker path**: Docker Desktop auto-start + Compose services set to `restart: always`
- **Non-Docker path**: install Windows startup tasks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\install_startup_tasks.ps1
```

Remove those startup tasks later:

```powershell
schtasks /Delete /F /TN "SentientShield API"
schtasks /Delete /F /TN "SentientShield Streamlit"
```

Install cloudflared as a Windows service (optional):

```powershell
cloudflared service install
```

---

## C) Always-on cloud hosting (PC can be off)

If you want true “live permanently” without maintaining a machine, use the cloud options in:
- [DEPLOY.md](file:///c:/Users/Dhruv/Documents/Projectss/SentientShield-ML-Detector/docs/DEPLOY.md)

Recommended picks:
- **Render Blueprint**: easiest always-on for the full stack
- **HuggingFace Spaces (Docker)**: best for ML demos

Render quick commands (git push triggers deploy):

```powershell
git status
git add -A
git commit -m "deploy"
git push
```

---

## Troubleshooting (fast fixes)

### “Unauthorized: Tunnel not found”

You’re trying to run a named tunnel that doesn’t exist on your Cloudflare account (or you’re not logged in).

Fix:
- Run `cloudflared login`
- Ensure you created the tunnel and routed DNS:

```powershell
cloudflared tunnel create sentientshield
cloudflared tunnel route dns sentientshield api.YOUR_DOMAIN
cloudflared tunnel route dns sentientshield analytics.YOUR_DOMAIN
```

### “Unable to reach the origin service … actively refused it”

Cloudflared can’t connect to your local port.

Fix:
- Make sure the origin is `127.0.0.1` (not `localhost` if IPv6 causes issues)
- Confirm API is running on `127.0.0.1:10000` and Streamlit on `127.0.0.1:8501`

Quick check:

```powershell
Test-NetConnection 127.0.0.1 -Port 10000
Test-NetConnection 127.0.0.1 -Port 8501
```

### API returns `403 {"detail":"Not authenticated"}`

This is expected for protected endpoints.

Fix:
- Open UI: `/static/premium.html`
- Or fetch a dev token at `/api/dev-token` and include `Authorization: Bearer <token>`

Example:

```powershell
$token = (Invoke-RestMethod http://127.0.0.1:10000/api/dev-token).token
Invoke-RestMethod http://127.0.0.1:10000/api/status -Headers @{ Authorization = "Bearer $token" }
```
