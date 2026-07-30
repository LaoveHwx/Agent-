"""
RAG Agent：企业知识库检索节点。

先确定性检索（search_documents）保证有来源，再由 create_agent 决定是否补充检索；
最终 rag_context 必须带可追溯来源。
"""
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from utils.langchain_utils import last_ai_content, load_tool_json
from models.llm import get_llm
from rag.retriever import search_documents
from tools.langchain_rag_tools import RAG_TOOLS


RAG_SYSTEM_PROMPT = """你是企业知识库 RAG Agent。工作流程：
1. 调用 retrieve_company_knowledge_tool 获取指标口径、业务规则、数据字典等知识片段；
2. 最终回答必须包含可追溯来源；
3. 信息不足时可多次检索。
"""


@lru_cache
def get_rag_agent_chain():
    """构建并缓存 RAG Agent 链，绑定知识库检索工具与系统提示。"""
    agent = create_agent(
        model=get_llm(),
        tools=RAG_TOOLS,
        system_prompt=RAG_SYSTEM_PROMPT,
    )
    prompt_template = ChatPromptTemplate.from_messages([
        ("human", "{question}")
    ])
    return prompt_template | agent


async def run_rag_agent(question: str, config: RunnableConfig | None = None) -> dict[str, Any]:
    """执行 RAG Agent 链，先确定性检索兜底再交由模型补充，返回带来源的上下文。"""
    # RAG 检索是企业问答的确定性步骤，节点先执行，避免模型跳过工具导致无来源回答。
    deterministic_context = search_documents(question, top_k=5)
    result = await get_rag_agent_chain().ainvoke({"question": question}, config=config)
    rag_context = load_tool_json(result, "retrieve_company_knowledge_tool")
    # 安全判断
    if not isinstance(rag_context, list):
        rag_context = deterministic_context

    return {
        "rag_context": rag_context,
        "analysis": last_ai_content(result),
        "errors": [],
    }
