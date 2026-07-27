"""
数据契约
"""
from pydantic import BaseModel, Field


class PlannerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class PlannerResponse(BaseModel):
    question: str
    task_type: str
    steps: list[str]
