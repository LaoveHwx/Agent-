"""
Health 路由：服务存活探针。

暴露 GET /health，返回服务名、环境与状态，供前端/网关做健康检查。
"""
from fastapi import APIRouter

from utils.env_util import app_env


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health_check():
    """健康检查探针，返回服务存活状态与环境信息。"""
    return {
        "status": "ok",
        "app_env": app_env,
        "service": "data-agent",
    }
