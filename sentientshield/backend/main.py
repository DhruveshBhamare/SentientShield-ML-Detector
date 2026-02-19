from fastapi import FastAPI
from sentientshield.backend.api.routes_logs import router as logs_router

app = FastAPI()
app.include_router(logs_router)
