from functools import lru_cache

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from agents.langchain_utils import last_ai_content
from models.llm import qwen_llm
from tools.langchain_memory_tools import MEMORY_TOOLS

ANALYST_SYSTEM_PROMPT = """
你是企业数据分析系统中的 Analyst Agent。
你需要结合 SQL 查询结果和 RAG 业务知识，输出清晰、可解释、可追溯的业务分析结论。
如果信息不足，要明确说明缺口，不要编造数据。
"""


@lru_cache
def get_analyst_chain():
    agent = create_agent(
        model=qwen_llm,
        tools=MEMORY_TOOLS,
        system_prompt=ANALYST_SYSTEM_PROMPT
        + """
回答企业问题前，可以调用 get_company_memory_tool 获取公司级长期记忆。
涉及用户偏好、常用指标、常看区域时，可以调用 get_user_memory_tool。
当用户明确提供新的个人偏好或公司规则时，可以调用对应 save 工具保存。
""",
    )
    prompt_template = ChatPromptTemplate.from_messages([
        (
            "human",
            """
用户问题：
{question}

短期会话上下文：
{history}

SQL Agent 结果：
{sql_result}

RAG Agent 结果：
{rag_context}

已有错误：
{errors}

请输出最终分析结论。
""",
        ),
    ])
    return prompt_template | agent


def run_analyst_agent(state: dict, config: RunnableConfig | None = None) -> dict:
    result = get_analyst_chain().invoke(
        {
            "question": state.get("question", ""),
            "history": state.get("history", []),
            "sql_result": state.get("sql_result"),
            "rag_context": state.get("rag_context", []),
            "errors": state.get("errors", []),
        },
        config=config,
    )
    return {"analysis": last_ai_content(result)}
