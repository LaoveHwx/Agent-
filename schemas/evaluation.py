from typing import Any

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    suites: list[str] | None = Field(default=None)


class EvaluationRunResponse(BaseModel):
    summary: dict[str, Any]
    suites: dict[str, Any]
