from fastapi import APIRouter

from schemas.planner import PlannerRequest, PlannerResponse
from services.planner_services import create_plan


planner_router = APIRouter(prefix="/planner")


@planner_router.get("")
async def planner_status():
    return {"status": "ok", "module": "planner"}


@planner_router.post("/plan", response_model=PlannerResponse)
async def planner(request: PlannerRequest):
    return create_plan(request)
