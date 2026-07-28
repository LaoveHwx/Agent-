from fastapi import APIRouter, HTTPException

from schemas.evaluation import EvaluationRunRequest, EvaluationRunResponse
from services.evaluation_service import run_evaluation_suite


evaluation_router = APIRouter(prefix="/evaluation")


@evaluation_router.get("")
async def evaluation_status():
    return {"status": "ok", "module": "evaluation"}


@evaluation_router.post("/run", response_model=EvaluationRunResponse)
async def run(request: EvaluationRunRequest):
    try:
        return run_evaluation_suite(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
