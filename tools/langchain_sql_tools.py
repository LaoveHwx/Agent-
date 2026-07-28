import json
from typing import Annotated

from langchain_core.tools import tool

from tools.postgres_tool import (
    get_schema_summary,
    get_table_columns,
    query_business_database,
    validate_business_sql,
)


@tool
def list_tables_tool() -> str:
    """List business tables and columns available to the SQL Agent."""
    schema_summary = get_schema_summary(include_internal=False)
    if not schema_summary:
        return "No business tables are available. Ask the developer to seed or connect business data first."
    return schema_summary


@tool
def table_schema_tool(
    table_name: Annotated[str, "Business table name, optionally qualified with schema, for example public.biz_sales_orders"],
) -> str:
    """Show columns for one business table."""
    try:
        rows = get_table_columns(table_name, include_internal=False)
    except Exception as exc:
        return f"Table schema unavailable: {exc}"

    if not rows:
        return f"Table schema not found: {table_name}"

    normalized = table_name.strip().strip('"')
    display_name = normalized if "." in normalized else f"public.{normalized}"
    lines = [f"Table: {display_name}"]
    for row in rows:
        lines.append(f"- {row['column_name']}: {row['data_type']}, nullable={row['is_nullable']}")
    return "\n".join(lines)


@tool
def check_sql_tool(
    query: Annotated[str, "Readonly PostgreSQL SELECT/WITH SQL to validate before execution"],
) -> str:
    """Validate readonly business SQL before execution."""
    try:
        readonly_sql = validate_business_sql(query)
        return f"SQL check passed: {readonly_sql}"
    except Exception as exc:
        return f"SQL check failed: {exc}"


@tool
def execute_sql_tool(
    query: Annotated[str, "Readonly PostgreSQL SELECT/WITH SQL to execute against business tables"],
) -> str:
    """Execute readonly business SQL and return structured rows."""
    try:
        result = query_business_database(query)
    except Exception as exc:
        result = {
            "sql": query,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "max_rows": 0,
            "error": str(exc),
        }
    return json.dumps(result, ensure_ascii=False, default=str)


SQL_TOOLS = [
    list_tables_tool,
    table_schema_tool,
    check_sql_tool,
    execute_sql_tool,
]
