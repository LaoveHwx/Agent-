"""
工具服务层：SQL 执行、Schema 读取、演示数据播种。

在 tool_router 与底层 postgres_tool / demo_business_seed 之间做薄封装，
统一返回 Pydantic 响应模型。
"""
from database.demo_business_seed import seed_demo_business_data
from schemas.tool import BusinessSeedResponse, SchemaSummaryResponse, SqlQueryRequest, SqlQueryResponse
from tools.postgres_tool import get_schema_summary, query_database


def execute_sql_query(request: SqlQueryRequest) -> SqlQueryResponse:
    """执行只读 SQL 查询并返回结果。"""
    result = query_database(request.sql)
    return SqlQueryResponse(**result)


def read_schema_summary() -> SchemaSummaryResponse:
    """读取数据库表结构摘要。"""
    return SchemaSummaryResponse(schema_summary=get_schema_summary())


def seed_business_demo_data() -> BusinessSeedResponse:
    """播种演示用业务数据。"""
    return BusinessSeedResponse(**seed_demo_business_data())
