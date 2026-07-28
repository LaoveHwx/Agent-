from typing import Any

from pydantic import BaseModel, Field


class AgentAnalyzeRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)


class AgentAnalyzeResponse(BaseModel):
    task_id: str
    session_id: str
    question: str
    task_type: str | None = None
    route: str | None = None
    plan: list[str] = Field(default_factory=list)
    sql: str | None = None
    sql_result: dict[str, Any] | None = None
    rag_context: list[dict[str, Any]] = Field(default_factory=list)
    analysis: str | None = None
    final_answer: str | None = None
    status: str | None = None
    errors: list[str] = Field(default_factory=list)
