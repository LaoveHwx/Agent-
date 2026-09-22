"""
评测路由：触发评测套件 HTTP 入口。

POST /evaluation/run 按请求的 suites 跑评测并返回汇总与明细，异常转 500。
"""
from fastapi import APIRouter, HTTPException

from schemas.evaluation import EvaluationRunRequest, EvaluationRunResponse
from services.evaluation_service import run_evaluation_suite


evaluation_router = APIRouter(prefix="/evaluation")


@evaluation_router.get("")
async def evaluation_status():
    """评测模块探活，返回存活状态。"""
    return {"status": "ok", "module": "evaluation"}


@evaluation_router.post("/run", response_model=EvaluationRunResponse)
async def run(request: EvaluationRunRequest):
    """按请求的评测套件运行评测，返回汇总与明细。"""
    try:
        return await run_evaluation_suite(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
