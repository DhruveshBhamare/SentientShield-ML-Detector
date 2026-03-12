import os
import logging
import asyncio
from datetime import datetime

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from .api.routers.neuralfort import router as neuralfort_router
from .api.routers.predict import router as predict_router
from .api.routers.status import router as status_router
from .api.routers.dashboard import router as dashboard_router
from .api.routers.project import router as project_router
from .api.routers.logs import router as logs_router
from .api.tasks.scheduler import start_daily_retrain_task
from .models.loader import load_model_if_needed
from .configs.config import (
    API_LOG_PATH,
    TRUSTED_ORIGINS
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SentientShield-WebAttackPredictor", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Secure Headers Middleware
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
        return response

app.add_middleware(SecureHeadersMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=TRUSTED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include Routers
app.include_router(neuralfort_router, prefix="/neuralfort", tags=["NeuralFort"])
app.include_router(predict_router)
app.include_router(status_router)
app.include_router(dashboard_router)
app.include_router(project_router)
app.include_router(logs_router)

@app.on_event("startup")
async def startup_event():
    # Initialize logging
    os.makedirs(os.path.dirname(API_LOG_PATH), exist_ok=True)
    logging.basicConfig(level=logging.INFO)
    
    try:
        asyncio.create_task(asyncio.to_thread(load_model_if_needed))
    except Exception as e:
        print(f"Startup warning: {e}")
    
    # Start background scheduler
    start_daily_retrain_task()

@app.get("/ping")
def ping():
    return HTMLResponse("pong")

@app.get("/")
async def root_endpoint():
    return RedirectResponse(url="/static/premium.html#bot")

@app.get("/premium.html", response_class=HTMLResponse)
async def premium_page():
    path = os.path.join(STATIC_DIR, "premium.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return RedirectResponse(url="/static/premium.html")

@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard_page():
    path = os.path.join(STATIC_DIR, "dashboard.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return RedirectResponse(url="/static/dashboard.html")

@app.get("/neuralfort_dashboard.html", response_class=HTMLResponse)
async def neuralfort_page():
    path = os.path.join(STATIC_DIR, "neuralfort_dashboard.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return RedirectResponse(url="/static/neuralfort_dashboard.html")
