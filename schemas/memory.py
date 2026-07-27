from typing import Any

from pydantic import BaseModel


class MemoryStatusResponse(BaseModel):
    status: str
    redis_db: int
    key_prefix: str


class ConversationResponse(BaseModel):
    session_id: str
    messages: list[dict[str, Any]]


class AgentStateResponse(BaseModel):
    task_id: str
    state: dict[str, Any] | None
