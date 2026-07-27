from typing import Any

from pydantic import BaseModel, Field


class SqlQueryRequest(BaseModel):
    sql: str = Field(..., min_length=1)


class SqlQueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    max_rows: int


class SchemaSummaryResponse(BaseModel):
    schema_summary: str
