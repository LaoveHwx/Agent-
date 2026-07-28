from database.demo_business_seed import seed_demo_business_data
from schemas.tool import BusinessSeedResponse, SchemaSummaryResponse, SqlQueryRequest, SqlQueryResponse
from tools.postgres_tool import get_schema_summary, query_database


def execute_sql_query(request: SqlQueryRequest) -> SqlQueryResponse:
    result = query_database(request.sql)
    return SqlQueryResponse(**result)


def read_schema_summary() -> SchemaSummaryResponse:
    return SchemaSummaryResponse(schema_summary=get_schema_summary())


def seed_business_demo_data() -> BusinessSeedResponse:
    return BusinessSeedResponse(**seed_demo_business_data())
