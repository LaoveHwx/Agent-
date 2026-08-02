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

from utils.langchain_utils import last_ai_content, load_tool_json
from utils.prompt_loader import load_prompt
from models.llm import get_llm
from tools.langchain_sql_tools import SQL_TOOLS


SQL_SYSTEM_PROMPT = load_prompt("sql_agent")


@lru_cache
def get_sql_agent_chain():
    """构建并缓存 SQL Agent 链，绑定只读查询工具与系统提示。"""
    agent = create_agent(
        model=get_llm(),
        tools=SQL_TOOLS,
        system_prompt=SQL_SYSTEM_PROMPT,
    )
    prompt_template = ChatPromptTemplate.from_messages([
        ("human", "{question}")
    ])
    return prompt_template | agent


async def run_sql_agent(question: str, config: RunnableConfig | None = None) -> dict[str, Any]:
    """执行 SQL Agent 链，返回 SQL 语句、查询结果与简要分析。"""
    result = await get_sql_agent_chain().ainvoke({"question": question}, config=config)
    sql_result = load_tool_json(result, "execute_sql_tool")

    return {
        "sql": sql_result.get("sql") if isinstance(sql_result, dict) else None,
        "sql_result": sql_result if isinstance(sql_result, dict) else None,
        "analysis": last_ai_content(result),
        "errors": [],
    }
