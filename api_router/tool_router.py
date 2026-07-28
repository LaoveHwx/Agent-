from fastapi import APIRouter, HTTPException

from schemas.tool import BusinessSeedResponse, SchemaSummaryResponse, SqlQueryRequest, SqlQueryResponse
from services.tool_service import execute_sql_query, read_schema_summary, seed_business_demo_data


tool_router = APIRouter(prefix="/tools")


@tool_router.get("")
async def tool():
    return {"status": "ok", "module": "tools"}


@tool_router.get("/sql/schema", response_model=SchemaSummaryResponse)
async def sql_schema():
    try:
        return read_schema_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@tool_router.post("/sql/query", response_model=SqlQueryResponse)
async def sql_query(request: SqlQueryRequest):
    try:
        return execute_sql_query(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@tool_router.post("/sql/demo-data", response_model=BusinessSeedResponse)
async def sql_demo_data():
    try:
        return seed_business_demo_data()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
