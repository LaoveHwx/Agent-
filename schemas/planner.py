"""
Planner 数据契约：任务规划请求/响应模型。

PlannerRequest 校验用户问题（长度 1-1000），
PlannerResponse 回复任务类型与执行步骤列表。
"""
from typing import Literal

from pydantic import BaseModel, Field

# 任务类型三选一：约束 LLM 结构化输出与 PlannerResponse 契约
TaskType = Literal["knowledge_query", "data_query", "complex_analysis"]
MemoryRoute = Literal["short_term_redis", "long_term_vector", "hybrid", "none"]


class PlannerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class PlannerResponse(BaseModel):
    question: str
    task_type: TaskType
    steps: list[str]
    memory_route: MemoryRoute = "none"
    memory_reason: str = ""
    memory_confidence: float = 0.0
