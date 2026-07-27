from schemas.tool import SchemaSummaryResponse, SqlQueryRequest, SqlQueryResponse
from tools.postgres_tool import get_schema_summary, query_database


def execute_sql_query(request: SqlQueryRequest) -> SqlQueryResponse:
    result = query_database(request.sql)
    return SqlQueryResponse(**result)


def read_schema_summary() -> SchemaSummaryResponse:
    return SchemaSummaryResponse(schema_summary=get_schema_summary())
