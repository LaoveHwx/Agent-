import json
from typing import Annotated

import psycopg
from langchain_core.tools import tool

from tools.postgres_tool import get_schema_summary, query_database, validate_readonly_sql


@tool
def list_tables_tool() -> str:
    """获取当前 PostgreSQL 数据库中可用的数据表和字段摘要。"""
    schema_summary = get_schema_summary()
    if not schema_summary:
        return "未发现可用业务表。"
    return schema_summary


@tool
def table_schema_tool(
    table_name: Annotated[str, "需要查看结构的表名，可以包含 schema，例如 public.sales"],
) -> str:
    """查看指定 PostgreSQL 表的字段结构。"""
    if "." in table_name:
        schema_name, raw_table_name = table_name.split(".", 1)
    else:
        schema_name, raw_table_name = "public", table_name

    sql = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
    """

    from tools.postgres_tool import _dsn

    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (schema_name, raw_table_name))
            rows = cur.fetchall()

    if not rows:
        return f"未找到表结构：{table_name}"

    lines = [f"表名：{schema_name}.{raw_table_name}"]
    for column_name, data_type, is_nullable in rows:
        lines.append(f"- {column_name}: {data_type}, nullable={is_nullable}")
    return "\n".join(lines)


@tool
def check_sql_tool(
    query: Annotated[str, "需要检查的 PostgreSQL SELECT/WITH 只读 SQL"],
) -> str:
    """检查 SQL 是否满足只读、安全、单语句要求。"""
    try:
        readonly_sql = validate_readonly_sql(query)
        return f"SQL检查通过：{readonly_sql}"
    except Exception as exc:
        return f"SQL检查失败：{exc}"


@tool
def execute_sql_tool(
    query: Annotated[str, "需要执行的 PostgreSQL SELECT/WITH 只读 SQL"],
) -> str:
    """执行 PostgreSQL 只读 SQL，并返回结构化查询结果。"""
    result = query_database(query)
    return json.dumps(result, ensure_ascii=False, default=str)


SQL_TOOLS = [
    list_tables_tool,
    table_schema_tool,
    check_sql_tool,
    execute_sql_tool,
]
