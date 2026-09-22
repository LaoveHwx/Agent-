"""数据分析节点：基于上游真实结果调用一次模型生成最终答案。"""
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from models.llm import get_llm


ANALYST_SYSTEM_PROMPT = """你是企业数据分析助手。根据给定 SQL 结果和知识上下文直接回答用户。
要求：先给结论，再给简洁表格或关键数据和依据来源；禁止编造；数据不足时说明缺口；不要输出内部调度过程；不要自行画 Mermaid 图。回答控制在 800 字以内。"""


async def run_analyst_agent(state: dict, config: RunnableConfig | None = None) -> dict:
    """只调用一次模型，避免工具 Agent 与最终节点重复生成。"""
    recent_messages = []
    if state.get("memory_route") in {"short_term_redis", "hybrid"}:
        for message in list(state.get("messages", []))[-6:]:
            recent_messages.append({
                "role": message.__class__.__name__,
                "content": str(getattr(message, "content", ""))[:1500],
            })
    payload = {
        "question": state.get("question", ""),
        "sql": state.get("sql"),
        "sql_result": state.get("sql_result"),
        "rag_context": state.get("rag_context", [])[:5],
        "memory_route": state.get("memory_route", "none"),
        "recent_messages": recent_messages,
        "errors": state.get("errors", []),
    }
    response = await get_llm().bind(max_tokens=1000).ainvoke(
        [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)[:16000]),
        ],
        config=config,
    )
    return {"analysis": str(response.content)}
