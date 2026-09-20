"""
RAG 工具集：把企业知识检索封装为 LangChain tool。

retrieve_company_knowledge_tool 调 search_documents 返回带来源的知识片段，
供 RAG Agent 调用；RAG_TOOLS 为工具列表。
"""
import json
from typing import Annotated

from langchain_core.tools import tool

from rag.retriever import search_documents


@tool
def retrieve_company_knowledge_tool(
    query: Annotated[str, "需要检索的企业知识、指标口径、数据字典或业务规则问题"],
    top_k: Annotated[int, "返回的知识片段数量，建议 3 到 5"] = 5,
) -> str:
    """检索企业知识库，返回带来源的相关知识片段。"""
    results = search_documents(query, top_k)
    return json.dumps(results, ensure_ascii=False, default=str)


RAG_TOOLS = [retrieve_company_knowledge_tool]
