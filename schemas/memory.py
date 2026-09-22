"""
记忆模块数据契约：Pydantic 响应模型。

定义 Redis 记忆状态、会话历史、Agent 状态快照的统一返回格式，
供 memory_router 做响应校验与序列化。
"""
from typing import Any

from pydantic import BaseModel


class MemoryStatusResponse(BaseModel):
    status: str
    redis_db: int
    key_prefix: str


class ConversationResponse(BaseModel):
    session_id: str
    messages: list[dict[str, Any]]


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool


class AgentStateResponse(BaseModel):
    task_id: str
    state: dict[str, Any] | None
