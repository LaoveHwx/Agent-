from fastapi import APIRouter

from utils.env_util import app_env


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app_env": app_env,
        "service": "data-agent",
    }
