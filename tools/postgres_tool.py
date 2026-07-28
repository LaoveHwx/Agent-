import re
from typing import Any

import psycopg
from psycopg.rows import dict_row

from utils.env_util import connection_string, connectioned_string, ps_dsn, sql_max_rows, sql_query_timeout


SYSTEM_SCHEMAS = {"pg_catalog", "information_schema"}
INTERNAL_TABLE_NAMES = {
    "rag_documents",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
}
INTERNAL_TABLE_PREFIXES = (
    "rag_",
    "langgraph_",
)

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|execute|merge)\b",
    re.IGNORECASE,
)
INTERNAL_SQL_PATTERN = re.compile(
    r"\b(rag_documents|information_schema|pg_catalog|checkpoints?|checkpoint_blobs|checkpoint_writes)\b",
    re.IGNORECASE,
)


def _dsn() -> str:
    dsn = ps_dsn or connection_string or connectioned_string
    if not dsn:
        raise RuntimeError("PostgreSQL DSN is not configured. Please set PS_DSN in .env")
    return dsn


def get_connection():
    return psycopg.connect(_dsn(), row_factory=dict_row)


def _int_value(raw_value: str | None, default: int) -> int:
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _normalize_sql(sql: str) -> str:
    normalized = sql.strip().rstrip(";").strip()
    if not normalized:
        raise ValueError("SQL cannot be empty")
    return normalized


def validate_readonly_sql(sql: str) -> str:
    normalized = _normalize_sql(sql)
    lowered = normalized.lower()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT/WITH readonly SQL is allowed")

    if ";" in normalized:
        raise ValueError("Multiple SQL statements are not allowed")

    if FORBIDDEN_SQL_PATTERN.search(normalized):
        raise ValueError("Dangerous SQL keyword is not allowed")

    return normalized


def validate_business_sql(sql: str) -> str:
    readonly_sql = validate_readonly_sql(sql)
    if INTERNAL_SQL_PATTERN.search(readonly_sql):
        raise ValueError("Agent SQL cannot access RAG, memory, checkpoint, or system metadata tables")
    return readonly_sql


def is_internal_table(table_schema: str, table_name: str) -> bool:
    schema = table_schema.lower()
    table = table_name.lower()
    return (
        schema in SYSTEM_SCHEMAS
        or table in INTERNAL_TABLE_NAMES
        or any(table.startswith(prefix) for prefix in INTERNAL_TABLE_PREFIXES)
    )


def is_business_table(table_schema: str, table_name: str) -> bool:
    return not is_internal_table(table_schema, table_name)


def _execute_readonly_query(readonly_sql: str) -> dict[str, Any]:
    max_rows = _int_value(sql_max_rows, 200)
    timeout_ms = _int_value(sql_query_timeout, 10) * 1000
    wrapped_sql = f"SELECT * FROM ({readonly_sql}) AS agent_query LIMIT {max_rows}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout_ms),))
            cur.execute(wrapped_sql)
            rows = list(cur.fetchall())
            columns = [column.name for column in cur.description] if cur.description else []

    return {
        "sql": readonly_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "max_rows": max_rows,
    }


def query_database(sql: str) -> dict[str, Any]:
    return _execute_readonly_query(validate_readonly_sql(sql))


def query_business_database(sql: str) -> dict[str, Any]:
    return _execute_readonly_query(validate_business_sql(sql))


def get_schema_summary(include_internal: bool = False) -> str:
    sql = """
    SELECT
        table_schema,
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name, ordinal_position
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = list(cur.fetchall())

    grouped: dict[str, list[str]] = {}
    for row in rows:
        if not include_internal and not is_business_table(row["table_schema"], row["table_name"]):
            continue
        table = f"{row['table_schema']}.{row['table_name']}"
        grouped.setdefault(table, []).append(f"{row['column_name']} {row['data_type']}")

    return "\n".join(f"{table}: {', '.join(columns)}" for table, columns in grouped.items())


def get_table_columns(table_name: str, include_internal: bool = False) -> list[dict[str, Any]]:
    normalized = table_name.strip().strip('"')
    if "." in normalized:
        schema_name, raw_table_name = normalized.split(".", 1)
    else:
        schema_name, raw_table_name = "public", normalized

    schema_name = schema_name.strip().strip('"')
    raw_table_name = raw_table_name.strip().strip('"')
    if not schema_name or not raw_table_name:
        raise ValueError("Table name cannot be empty")

    if not include_internal and not is_business_table(schema_name, raw_table_name):
        raise ValueError(f"Table is not available for business SQL: {schema_name}.{raw_table_name}")

    sql = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (schema_name, raw_table_name))
            rows = list(cur.fetchall())

    return rows
