"""
SQL Agent：企业数据分析的取数节点。

通过 LangChain create_agent 绑定 SQL_TOOLS，让模型自主完成
「读表结构 -> 生成 SQL -> 安全校验 -> 执行」的只读查询流程。
"""
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from agents.langchain_utils import last_ai_content, load_tool_json
from models.llm import get_llm
from tools.langchain_sql_tools import SQL_TOOLS


SQL_SYSTEM_PROMPT = """
你是企业数据分析系统中的 SQL Agent。
你的职责是根据用户问题查询 PostgreSQL 业务数据库。
必须遵守：
1. 先使用 list_tables_tool 或 table_schema_tool 理解表结构。
2. 生成 SQL 后，先调用 check_sql_tool 检查。
3. 检查通过后，调用 execute_sql_tool 执行。
4. 只能执行 SELECT/WITH 只读 SQL。
5. 只能使用 list_tables_tool 暴露的业务表。
6. 不允许查询 rag_documents、checkpoint、memory、information_schema、pg_catalog 等非业务表。
7. 最终回答需要简洁说明查询结论。
"""


@lru_cache
def get_sql_agent_chain():
    agent = create_agent(
        model=get_llm(),
        tools=SQL_TOOLS,
        system_prompt=SQL_SYSTEM_PROMPT,
    )
    prompt_template = ChatPromptTemplate.from_messages([
        ("human", "{question}")
    ])
    return prompt_template | agent


def run_sql_agent(question: str, config: RunnableConfig | None = None) -> dict[str, Any]:
    result = get_sql_agent_chain().invoke({"question": question}, config=config)
    sql_result = load_tool_json(result, "execute_sql_tool")

    return {
        "sql": sql_result.get("sql") if isinstance(sql_result, dict) else None,
        "sql_result": sql_result if isinstance(sql_result, dict) else None,
        "analysis": last_ai_content(result),
        "errors": [],
    }
