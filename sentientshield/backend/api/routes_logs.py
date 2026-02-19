from fastapi import APIRouter
from api.routers.logs import router as _router

router = APIRouter()
router.include_router(_router)
