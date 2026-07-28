"""
企业数据分析 Agent 状态图（LangGraph 编排）。

拓扑（条件路由）：
    knowledge_query:    planner -> rag -> final
    data_query:         planner -> sql -> analyst -> final
    complex_analysis:   planner -> sql -> rag -> analyst -> final

对话历史：
    state.messages 由 RedisSaver checkpointer 按 thread_id 自动续接，
    final_node 把最终答案作为 AIMessage 累积进 messages，实现多轮上下文。

节点约定：
    每个节点读 state -> 调对应 agent -> 返回 dict 更新 state；
    错误累积进 state.errors，由 final_node 统一收口。
"""
from functools import lru_cache
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph, add_messages

from agents.analyst import run_analyst_agent
from agents.planner import run_planner
from agents.rag_agent import run_rag_agent
from agents.sql_agent import run_sql_agent
from memory.redis_checkpointer import get_redis_saver


class AgentState(TypedDict, total=False):
    task_id: str          # 任务唯一ID
    session_id: str       # 会话唯一ID
    question: str         # 用户提问内容
    messages: Annotated[list, add_messages]  # 跨轮对话历史（checkpointer 按 thread_id 自动续接）
    task_type: str        # 任务类型标识
    route: str            # 当前处理节点
    plan: list[str]       # 计划步骤列表
    sql: str | None       # 生成的SQL查询
    sql_result: dict | None  # SQL查询结果
    rag_context: list[dict]  # 检索增强上下文
    analysis: str | None  # 推理分析过程
    final_answer: str | None  # 最终回答内容
    status: str           # 任务执行状态
    errors: list[str]     # 错误信息列表


def planner_node(state: AgentState) -> AgentState:
    """
    返回：task_type + plan（分类 + 计划）
    """
    plan = run_planner(state["question"])
    return {
        **state,
        "task_type": plan["task_type"],
        "route": plan["task_type"],
        "plan": plan["plan"],
        "errors": state.get("errors", []),
    }


def sql_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    生成并执行sql语句并返回查询结果
    """
    result = run_sql_agent(state["question"], config=config)
    return {
        **state,
        "sql": result.get("sql"),
        "sql_result": result.get("sql_result"),
        "analysis": result.get("analysis") or state.get("analysis"),
        "errors": state.get("errors", []) + result.get("errors", []),
    }


def rag_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """检索企业知识库，返回 rag_context。"""
    result = run_rag_agent(state["question"], config=config)
    return {
        **state,
        "rag_context": result.get("rag_context", []),
        "analysis": result.get("analysis") or state.get("analysis"),
        "errors": state.get("errors", []) + result.get("errors", []),
    }


def analyst_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """汇总 SQL 结果 + RAG 上下文 + 对话历史，输出分析结论。"""
    result = run_analyst_agent(state, config=config)
    return {**state, "analysis": result["analysis"]}


def final_node(state: AgentState) -> AgentState:
    """收口：确定 final_answer、累积 AIMessage 进对话历史、标记 status。"""
    errors = state.get("errors", [])
    final_answer = state.get("analysis") or state.get("final_answer")

    if not final_answer:
        if state.get("rag_context"):
            snippets = []
            for item in state.get("rag_context", [])[:3]:
                source = item.get("source") or "unknown"
                content = item.get("content") or ""
                snippets.append(f"- 来源：{source}\n  内容：{content}")
            final_answer = "根据知识库检索结果：\n" + "\n".join(snippets)
        elif state.get("sql_result"):
            final_answer = "已完成 SQL 查询，但暂未生成分析结论。"
        else:
            final_answer = "当前没有足够结果生成最终回答。"

    return {
        **state,
        "final_answer": final_answer,
        # 把最终答案作为 AIMessage 累积进对话历史，checkpointer 保存后下一轮可续接
        "messages": [AIMessage(content=final_answer)],
        "status": "failed" if errors else "completed",
        "errors": errors,
    }


def route_after_planner(state: AgentState) -> str:
    if state.get("task_type") == "knowledge_query":
        return "rag"
    return "sql"


def route_after_sql(state: AgentState) -> str:
    if state.get("task_type") == "complex_analysis":
        return "rag"
    return "analyst"


def route_after_rag(state: AgentState) -> str:
    if state.get("task_type") == "knowledge_query":
        return "final"
    return "analyst"


@lru_cache
def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("sql", sql_node)
    graph.add_node("rag", rag_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("final", final_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "sql": "sql",
            "rag": "rag",
        },
    )
    graph.add_conditional_edges(
        "sql",
        route_after_sql,
        {
            "rag": "rag",
            "analyst": "analyst",
        },
    )
    graph.add_conditional_edges(
        "rag",
        route_after_rag,
        {
            "analyst": "analyst",
            "final": "final",
        },
    )
    graph.add_edge("analyst", "final")
    graph.add_edge("final", END)
    return graph.compile(checkpointer=get_redis_saver())


def run_agent_workflow(question: str, session_id: str, task_id: str) -> AgentState:
    app = build_agent_graph()
    return app.invoke(
        {
            "task_id": task_id,
            "session_id": session_id,
            "question": question.strip(),
            "messages": [HumanMessage(content=question.strip())],
            "errors": [],
            "rag_context": [],
        },
        config={
            "configurable": {
                "thread_id": session_id,
                "user_id": session_id,
            }
        },
    )
