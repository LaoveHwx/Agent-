"""RAG Agent：固定检索一次，再用一次模型调用生成可追溯答案。"""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from models.llm import get_llm
from rag.retriever import search_documents


RAG_SYSTEM_PROMPT = """你是企业知识库问答助手。只根据给定知识片段回答。
先给结论，再给关键依据；标注知识片段中的来源。知识库未命中时明确说明，不要反复检索，不要把通用知识伪装成企业口径。回答控制在 600 字以内。"""


async def run_rag_agent(question: str, config: RunnableConfig | None = None) -> dict[str, Any]:
    """确定性检索一次并生成一次答案，避免 Agent 自主反复换关键词。"""
    rag_context = search_documents(question, top_k=5)
    context_text = json.dumps(rag_context, ensure_ascii=False, default=str)[:12000]
    response = await get_llm().bind(max_tokens=800).ainvoke(
        [
            SystemMessage(content=RAG_SYSTEM_PROMPT),
            HumanMessage(content=f"用户问题：{question}\n\n知识片段：\n{context_text}"),
        ],
        config=config,
    )
    return {"rag_context": rag_context, "analysis": str(response.content), "errors": []}
