"""
数据分析的汇总节点。
结合 SQL 查询结果、RAG 知识上下文与跨轮对话历史，输出最终分析结论。
"""
from functools import lru_cache
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from utils.langchain_utils import last_ai_content
from utils.prompt_loader import load_prompt
from models.llm import get_llm
from tools.langchain_memory_tools import MEMORY_TOOLS


ANALYST_SYSTEM_PROMPT = load_prompt("analyst")

MAX_HISTORY_MESSAGES = 20


@lru_cache
def get_analyst_agent():
    """构建并缓存 Analyst Agent，绑定记忆工具与汇总分析系统提示。"""
    return create_agent(
        model=get_llm(),
        tools=MEMORY_TOOLS,
        system_prompt=ANALYST_SYSTEM_PROMPT,
    )


async def run_analyst_agent(state: dict, config: RunnableConfig | None = None) -> dict:
    """汇总节点：具有跨轮对话历史功能==输出最终分析结论。
    对话历史来自 state["messages"]
    """
    question = state.get("question", "")
    sql_result = state.get("sql_result")
    rag_context = state.get("rag_context", [])
    errors = state.get("errors", [])

    context = f"""
用户问题：
{question}

SQL Agent 结果：
{sql_result}

RAG Agent 结果：
{rag_context}

已有错误：
{errors}

请输出最终分析结论。
"""
    context_message = HumanMessage(content=context)

    messages = list(state.get("messages", []))
    # messages 末尾是当轮的 HumanMessage(question)，替换为带结构化上下文的版本；
    # 取最近 MAX_HISTORY_MESSAGES 条防止 prompt 膨胀。
    if messages:
        messages = messages[:-1]
    messages.append(context_message)
    messages = messages[-MAX_HISTORY_MESSAGES:]

    result = await get_analyst_agent().ainvoke({"messages": messages}, config=config)
    return {"analysis": last_ai_content(result)}
