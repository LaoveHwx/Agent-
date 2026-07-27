import re

from tools.postgres_tool import get_schema_summary, query_database, validate_readonly_sql
from utils.llm_client import chat_completion


SQL_SYSTEM_PROMPT = """
你是企业数据分析系统中的 SQL Agent。
你只能输出一条 PostgreSQL 只读 SELECT SQL。
不要输出 Markdown，不要解释，不要输出多条 SQL。
禁止 INSERT、UPDATE、DELETE、DROP、ALTER、TRUNCATE、CREATE。
"""


def _extract_sql(text: str) -> str:
    match = re.search(r"```sql\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()

    return text.strip()


def generate_sql(question: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []

    try:
        schema_summary = get_schema_summary()
    except Exception as exc:
        return None, [f"读取数据库表结构失败: {exc}"]

    user_prompt = f"""
数据库表结构如下：
{schema_summary}

用户问题：
{question}

请生成一条 PostgreSQL SELECT SQL。
"""
    content = chat_completion(SQL_SYSTEM_PROMPT, user_prompt)
    if not content:
        return None, ["SQL Agent 未生成 SQL：请先配置 API_KEY、BASE_URL 和 MODEL_NAME"]

    sql = _extract_sql(content)
    try:
        validate_readonly_sql(sql)
    except ValueError as exc:
        errors.append(f"SQL安全校验失败: {exc}")
        return None, errors

    return sql, errors


def run_sql_agent(question: str) -> dict:
    sql, errors = generate_sql(question)
    if not sql:
        return {"sql": None, "sql_result": None, "errors": errors}

    try:
        result = query_database(sql)
        return {"sql": sql, "sql_result": result, "errors": errors}
    except Exception as exc:
        return {
            "sql": sql,
            "sql_result": None,
            "errors": errors + [f"SQL执行失败: {exc}"],
        }
