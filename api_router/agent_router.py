from fastapi import APIRouter

from schemas.agent import AgentAnalyzeRequest, AgentAnalyzeResponse
from services.agent_service import analyze_question


agent_router = APIRouter(prefix="/agent")


@agent_router.get("")
async def agent_status():
    return {"status": "ok", "module": "agent"}


@agent_router.post("/analyze", response_model=AgentAnalyzeResponse)
async def analyze(request: AgentAnalyzeRequest):
    return analyze_question(request)
