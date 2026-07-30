"""
工具模块数据契约：SQL 查询与表结构读取的请求/响应模型。

SqlQueryRequest / SqlQueryResponse 约束只读 SQL 入参与结果结构；
SchemaSummaryResponse、BusinessSeedResponse 用于表结构概览与演示数据播种。
"""
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


class BusinessSeedResponse(BaseModel):
    status: str
    tables: list[str]
    rows: dict[str, int]
