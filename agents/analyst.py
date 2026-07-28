"""
Analyst Agent：企业数据分析的汇总节点。

结合 SQL 查询结果、RAG 知识上下文与跨轮对话历史，输出可追溯的最终分析结论。
对话历史来自 state.messages（checkpointer 自动续接），不再手动传入 history。
"""
from functools import lru_cache
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agents.langchain_utils import last_ai_content
from models.llm import get_llm
from tools.langchain_memory_tools import MEMORY_TOOLS


ANALYST_SYSTEM_PROMPT = """你是企业数据分析系统中的 Analyst Agent。工作流程：
1. 结合 SQL 查询结果和 RAG 业务知识，输出清晰、可解释、可追溯的分析结论；
2. 信息不足时明确说明缺口，不要编造数据；
3. 回答企业问题前，可调用 get_company_memory_tool 获取公司级长期记忆；
4. 涉及用户偏好、常用指标、常看区域时，可调用 get_user_memory_tool；
5. 用户明确提供新的个人偏好或公司规则时，调用对应 save 工具保存。
"""

MAX_HISTORY_MESSAGES = 20


@lru_cache
def get_analyst_agent():
    return create_agent(
        model=get_llm(),
        tools=MEMORY_TOOLS,
        system_prompt=ANALYST_SYSTEM_PROMPT,
    )


def run_analyst_agent(state: dict, config: RunnableConfig | None = None) -> dict:
    """汇总节点：结合跨轮对话历史 + 当轮结构化上下文，输出最终分析结论。

    对话历史来自 state["messages"]（由 checkpointer 按 thread_id 自动续接），
    不再依赖手动传入的 history 字段。
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

    result = get_analyst_agent().invoke({"messages": messages}, config=config)
    return {"analysis": last_ai_content(result)}
