"""
Agent 路由：问答分析 HTTP 入口。

POST /agent/analyze 同步返回完整分析；POST /agent/stream 以 NDJSON 流式推送
节点状态与最终答案分片。
"""
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from schemas.agent import AgentAnalyzeRequest, AgentAnalyzeResponse
from services.agent_service import analyze_question, stream_analyze_question


agent_router = APIRouter(prefix="/agent")


@agent_router.get("")
async def agent_status(): # 测试探针一枚 :调试用
    """Agent 模块探活，返回存活状态。"""
    return {"status": "ok", "module": "agent"}

# 同步执行企业问题分析，用来测试的。
@agent_router.post("/analyze", response_model=AgentAnalyzeResponse)
async def analyze(request: AgentAnalyzeRequest):
    return await analyze_question(request)
# 同步执行企业问题分析，用来测试的。

@agent_router.post("/stream")
async def stream(request: AgentAnalyzeRequest):
    """流式执行企业问题分析，以 NDJSON 推送节点状态与答案分片。"""
    return StreamingResponse(
        stream_analyze_question(request),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
