from fastapi import APIRouter
from starlette.responses import StreamingResponse

from schemas.agent import AgentAnalyzeRequest, AgentAnalyzeResponse
from services.agent_service import analyze_question, stream_analyze_question


agent_router = APIRouter(prefix="/agent")


@agent_router.get("")
async def agent_status(): # 测试探针一枚 :调试用
    return {"status": "ok", "module": "agent"}


@agent_router.post("/analyze", response_model=AgentAnalyzeResponse)
async def analyze(request: AgentAnalyzeRequest):
    return analyze_question(request)


@agent_router.post("/stream")
async def stream(request: AgentAnalyzeRequest):
    return StreamingResponse(
        stream_analyze_question(request),
        media_type="application/x-ndjson",
    )
