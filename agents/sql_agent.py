"""SQL Agent：一次生成 SQL，由代码完成校验和执行，失败时最多纠正一次。"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from models.llm import get_llm
from tools.postgres_tool import get_schema_summary, query_business_database, validate_business_sql


class SQLGeneration(BaseModel):
    query: str = Field(description="可直接执行的 PostgreSQL SELECT/WITH 只读 SQL")


SQL_GENERATION_SYSTEM = """你是 PostgreSQL 只读 SQL 生成器。只返回结构化 query。
规则：
1. 只能生成一条 SELECT/WITH，只能使用给定业务表与字段，禁止访问系统表和内部记忆表。
2. 聚合查询必须使用清晰的中文或英文别名。
3. 用户未明确给出日历日期而询问“最近N天/最新/近期”时，以相关业务表中 MAX(日期字段) 为基准回溯，避免演示数据早于系统当前日期导致空结果。
4. “上季度”等明确日历周期按 PostgreSQL CURRENT_DATE 计算。
5. 直接完成用户所需的维度、指标、排序与占比，不要先生成探测 SQL。
"""


async def _generate_sql(question: str, schema: str, error: str = "", config: RunnableConfig | None = None) -> str:
    correction = f"\n上一次 SQL 失败：{error}\n请修正。" if error else ""
    model = get_llm().with_structured_output(SQLGeneration)
    result = await model.ainvoke(
        [
            SystemMessage(content=SQL_GENERATION_SYSTEM),
            HumanMessage(content=f"用户问题：{question}\n\n业务表结构：\n{schema}{correction}"),
        ],
        config=config,
    )
    return result.query


async def run_sql_agent(question: str, config: RunnableConfig | None = None) -> dict[str, Any]:
    """一次生成并执行 SQL；校验或执行失败时最多调用模型纠正一次。"""
    schema = get_schema_summary(include_internal=False)
    errors: list[str] = []
    last_query: str | None = None

    for attempt in range(2):
        try:
            last_query = await _generate_sql(
                question,
                schema,
                error=errors[-1] if errors else "",
                config=config,
            )
            readonly_sql = validate_business_sql(last_query)
            result = query_business_database(readonly_sql)
            return {"sql": readonly_sql, "sql_result": result, "analysis": None, "errors": []}
        except Exception as exc:
            errors.append(str(exc))
            if attempt == 1:
                break

    return {
        "sql": last_query,
        "sql_result": None,
        "analysis": "SQL 查询失败，无法获得可靠数据。",
        "errors": [f"SQL 查询失败: {errors[-1]}"],
    }
