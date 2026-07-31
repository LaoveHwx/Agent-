"""
PostgreSQL 工具：只读 SQL 校验 + 执行 + 表结构读取。

validate_readonly_sql / validate_business_sql 做关键词黑名单与业务表隔离校验；
query_* 包一层 LIMIT 与 statement_timeout 防爆；get_schema_summary / get_table_columns
供 SQL Agent 理解表结构。
"""
import re
from typing import Any

from utils.env_util import sql_max_rows, sql_query_timeout
from utils.postgres_pool import get_connection

# 内部表，系统表
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
# 危险关键词集合，免得改表
FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|execute|merge)\b",
    re.IGNORECASE,
)
INTERNAL_SQL_PATTERN = re.compile(
    r"\b(rag_documents|information_schema|pg_catalog|checkpoints?|checkpoint_blobs|checkpoint_writes)\b",
    re.IGNORECASE,
)


def _int_value(raw_value: str | None, default: int) -> int:
    """把环境变量字符串解析为正整数，非法或非正时回退默认值。"""
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _normalize_sql(sql: str) -> str:
    """去除 SQL 首尾空白与结尾分号，空串抛错。"""
    normalized = sql.strip().rstrip(";").strip()
    if not normalized:
        raise ValueError("SQL cannot be empty")
    return normalized

# 第一层防御
def validate_readonly_sql(sql: str) -> str:
    """校验 SQL 为只读 SELECT/WITH，拒绝多语句与危险关键字。"""
    normalized = _normalize_sql(sql)
    lowered = normalized.lower()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT/WITH readonly SQL is allowed")

    if ";" in normalized:
        raise ValueError("Multiple SQL statements are not allowed")

    if FORBIDDEN_SQL_PATTERN.search(normalized):
        raise ValueError("Dangerous SQL keyword is not allowed")

    return normalized

# 第二层防御
def validate_business_sql(sql: str) -> str:
    """在只读校验基础上额外禁止访问内部表。"""
    readonly_sql = validate_readonly_sql(sql)
    if INTERNAL_SQL_PATTERN.search(readonly_sql):
        raise ValueError("Agent SQL cannot access RAG, memory, checkpoint, or system metadata tables")
    return readonly_sql


def is_internal_table(table_schema: str, table_name: str) -> bool:
    """判断表是否属于系统 schema 或 RAG/记忆等内部表。"""
    schema = table_schema.lower()
    table = table_name.lower()
    return (
        schema in SYSTEM_SCHEMAS
        or table in INTERNAL_TABLE_NAMES
        or any(table.startswith(prefix) for prefix in INTERNAL_TABLE_PREFIXES)
    )

def is_business_table(table_schema: str, table_name: str) -> bool:
    """判断表是否为业务表（即非内部表）。"""
    return not is_internal_table(table_schema, table_name)
# 第三层防御
def _execute_readonly_query(readonly_sql: str) -> dict[str, Any]:
    """执行已校验的只读 SQL，套 LIMIT 与 statement_timeout 防爆。"""
    max_rows = _int_value(sql_max_rows, 200)
    timeout_ms = _int_value(sql_query_timeout, 10) * 1000
    wrapped_sql = f"SELECT * FROM ({readonly_sql}) AS agent_query LIMIT {max_rows}" # 强行包装限制行数上去

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

# 权限更多的读用于管理员。运维等。
def query_database(sql: str) -> dict[str, Any]:
    """校验并执行只读 SQL，返回结构化结果。"""
    return _execute_readonly_query(validate_readonly_sql(sql))

def query_business_database(sql: str) -> dict[str, Any]:
    """校验为业务只读 SQL 后执行，返回结构化结果。"""
    return _execute_readonly_query(validate_business_sql(sql))


def get_table_list_summary(include_internal: bool = False) -> str:
    """汇总业务表的表名与注释（不含列），供模型先挑选相关表，避免一次塞入全部列。"""
    sql = """
    SELECT
        n.nspname AS table_schema,
        c.relname AS table_name,
        pg_catalog.obj_description(c.oid, 'pg_class') AS table_comment
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY n.nspname, c.relname
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = list(cur.fetchall())

    lines = []
    for row in rows:
        if not include_internal and not is_business_table(row["table_schema"], row["table_name"]):
            continue
        comment = row["table_comment"] or "无注释"
        lines.append(f"{row['table_schema']}.{row['table_name']}: {comment}")

    return "\n".join(lines)


def get_schema_summary(include_internal: bool = False) -> str:
    """汇总业务表的表名与列定义，默认不含内部表。"""
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
    """读取指定表的列名、类型与可空性，默认仅业务表。"""
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
