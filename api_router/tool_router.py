"""
Tools 路由：SQL 执行与表结构 HTTP 入口。

GET /tools/sql/schema 读表结构、POST /tools/sql/query 执行只读 SQL、
POST /tools/sql/demo-data 播种演示业务数据；异常转 HTTP 状态码。
"""
from fastapi import APIRouter, HTTPException

from schemas.tool import BusinessSeedResponse, SchemaSummaryResponse, SqlQueryRequest, SqlQueryResponse
from services.tool_service import execute_sql_query, read_schema_summary, seed_business_demo_data


tool_router = APIRouter(prefix="/tools")


@tool_router.get("")
async def tool():
    """Tools 模块探活，返回存活状态。"""
    return {"status": "ok", "module": "tools"}


@tool_router.get("/sql/schema", response_model=SchemaSummaryResponse)
async def sql_schema():
    """读取数据库表结构摘要，供前端了解可用字段。"""
    try:
        return read_schema_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@tool_router.post("/sql/query", response_model=SqlQueryResponse)
async def sql_query(request: SqlQueryRequest):
    """执行只读 SQL 查询并返回结果。"""
    try:
        return execute_sql_query(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@tool_router.post("/sql/demo-data", response_model=BusinessSeedResponse)
async def sql_demo_data():
    """播种演示业务数据到数据库，用于快速体验场景。"""
    try:
        return seed_business_demo_data()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
