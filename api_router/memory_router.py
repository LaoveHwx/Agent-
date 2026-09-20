"""
Memory 路由：记忆状态与历史查询 HTTP 入口。

GET /memory 探活、/memory/sessions/{id} 取会话历史、/memory/tasks/{id} 取 Agent 状态快照；
异常转 500。
"""
from fastapi import APIRouter, HTTPException

from schemas.memory import AgentStateResponse, ConversationResponse, MemoryStatusResponse, SessionDeleteResponse
from services.memory_service import delete_conversation, read_agent_state, read_conversation, read_memory_status


memory_router = APIRouter(prefix="/memory")


@memory_router.get("", response_model=MemoryStatusResponse)
async def status():
    """读取记忆模块整体状态，用于探活与诊断。"""
    try:
        return read_memory_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@memory_router.get("/sessions/{session_id}", response_model=ConversationResponse)
async def conversation(session_id: str):
    """按会话 ID 读取历史对话记录。"""
    try:
        return await read_conversation(session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@memory_router.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(session_id: str):
    """删除指定会话的全部短期记忆。"""
    try:
        return await delete_conversation(session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@memory_router.get("/tasks/{task_id}", response_model=AgentStateResponse)
async def agent_state(task_id: str):
    """按任务 ID 读取 Agent 状态快照。"""
    try:
        return read_agent_state(task_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
