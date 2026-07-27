import re
from typing import Any

import psycopg
from psycopg.rows import dict_row

from utils.env_util import connection_string, connectioned_string, ps_dsn, sql_max_rows, sql_query_timeout


FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|execute|merge)\b",
    re.IGNORECASE,
)


def _dsn() -> str:
    dsn = ps_dsn or connection_string or connectioned_string
    if not dsn:
        raise RuntimeError("PostgreSQL DSN is not configured. Please set PS_DSN in .env")
    return dsn


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


def query_database(sql: str) -> dict[str, Any]:
    readonly_sql = validate_readonly_sql(sql)
    max_rows = _int_value(sql_max_rows, 200)
    timeout_ms = _int_value(sql_query_timeout, 10) * 1000
    wrapped_sql = f"SELECT * FROM ({readonly_sql}) AS agent_query LIMIT %s"

    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout_ms),))
            cur.execute(wrapped_sql, (max_rows,))
            rows = list(cur.fetchall())
            columns = [column.name for column in cur.description] if cur.description else []

    return {
        "sql": readonly_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "max_rows": max_rows,
    }


def get_schema_summary() -> str:
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

    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = list(cur.fetchall())

    grouped: dict[str, list[str]] = {}
    for row in rows:
        table = f"{row['table_schema']}.{row['table_name']}"
        grouped.setdefault(table, []).append(f"{row['column_name']} {row['data_type']}")

    return "\n".join(f"{table}: {', '.join(columns)}" for table, columns in grouped.items())
