"""
Planner 路由：任务规划 HTTP 入口。

POST /planner/plan 接收用户问题，调用 planner_services 完成任务分类与步骤生成，
返回 PlannerResponse。
"""
from fastapi import APIRouter

from schemas.planner import PlannerRequest, PlannerResponse
from services.planner_services import create_plan


planner_router = APIRouter(prefix="/planner")


@planner_router.get("")
async def planner_status():
    """Planner 模块探活，返回存活状态。"""
    return {"status": "ok", "module": "planner"}


@planner_router.post("/plan", response_model=PlannerResponse)
async def planner(request: PlannerRequest):
    """根据用户问题生成任务分类与执行步骤规划。"""
    return await create_plan(request)
