from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.analyst import run_analyst_agent
from agents.planner import run_planner
from agents.rag_agent import run_rag_agent
from agents.sql_agent import run_sql_agent


class AgentState(TypedDict, total=False):
    task_id: str
    session_id: str
    question: str
    history: list[dict]
    task_type: str
    route: str
    plan: list[str]
    sql: str | None
    sql_result: dict | None
    rag_context: list[dict]
    analysis: str | None
    final_answer: str | None
    status: str
    errors: list[str]


def planner_node(state: AgentState) -> AgentState:
    plan = run_planner(state["question"])
    return {
        **state,
        "task_type": plan["task_type"],
        "route": plan["task_type"],
        "plan": plan["plan"],
        "errors": state.get("errors", []),
    }


def sql_node(state: AgentState) -> AgentState:
    result = run_sql_agent(state["question"])
    return {
        **state,
        "sql": result.get("sql"),
        "sql_result": result.get("sql_result"),
        "errors": state.get("errors", []) + result.get("errors", []),
    }


def rag_node(state: AgentState) -> AgentState:
    result = run_rag_agent(state["question"])
    return {
        **state,
        "rag_context": result.get("rag_context", []),
        "errors": state.get("errors", []) + result.get("errors", []),
    }


def analyst_node(state: AgentState) -> AgentState:
    result = run_analyst_agent(state)
    return {**state, "analysis": result["analysis"]}


def final_node(state: AgentState) -> AgentState:
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


def build_fixed_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("sql", sql_node)
    graph.add_node("rag", rag_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("final", final_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "sql")
    graph.add_edge("sql", "rag")
    graph.add_edge("rag", "analyst")
    graph.add_edge("analyst", "final")
    graph.add_edge("final", END)
    return graph.compile()


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
    return graph.compile()


def run_agent_workflow(question: str, session_id: str, task_id: str, history: list[dict] | None = None) -> AgentState:
    app = build_agent_graph()
    return app.invoke(
        {
            "task_id": task_id,
            "session_id": session_id,
            "question": question.strip(),
            "history": history or [],
            "errors": [],
            "rag_context": [],
        }
    )
