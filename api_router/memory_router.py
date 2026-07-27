from fastapi import APIRouter, HTTPException

from schemas.memory import AgentStateResponse, ConversationResponse, MemoryStatusResponse
from services.memory_service import read_agent_state, read_conversation, read_memory_status


memory_router = APIRouter(prefix="/memory")


@memory_router.get("", response_model=MemoryStatusResponse)
async def status():
    try:
        return read_memory_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@memory_router.get("/sessions/{session_id}", response_model=ConversationResponse)
async def conversation(session_id: str):
    try:
        return read_conversation(session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@memory_router.get("/tasks/{task_id}", response_model=AgentStateResponse)
async def agent_state(task_id: str):
    try:
        return read_agent_state(task_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
