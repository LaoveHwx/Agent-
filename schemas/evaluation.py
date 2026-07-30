"""
评测模块数据契约：评测请求/响应模型。

EvaluationRunRequest 指定要跑的测试套件（sql/rag/agent），
EvaluationRunResponse 返回整体汇总指标与各套件明细。
"""
from typing import Any

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    suites: list[str] | None = Field(default=None)


class EvaluationRunResponse(BaseModel):
    summary: dict[str, Any]
    suites: dict[str, Any]
