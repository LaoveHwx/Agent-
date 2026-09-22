"""
企业数据分析 Agent 状态图（LangGraph 编排）。

拓扑（条件路由）：
    知识问答:    planner -> rag -> final
    数据查询:   planner -> sql -> analyst -> mcp -> final
    复杂分析:   planner -> sql -> rag -> analyst -> mcp -> final

mcp 节点用「绑定 MCP 工具的大模型」对数据做可视化（柱状/折线/饼图/表格等）或
数值计算（统计描述/增长率/数值格式化）；MCP 工具为 async-only，故所有节点统一 async、graph 全程走 ainvoke。

对话历史：
    state.messages 由 RedisSaver checkpointer 按 thread_id 自动续接，
    final_node 把最终答案作为 AIMessage 累积进 messages，实现多轮上下文。

节点约定：
    每个节点读 state -> 调对应 agent -> 返回 dict 更新 state；
    错误累积进 state.errors，由 final_node 统一收口。
"""
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph, add_messages

from agents.analyst import run_analyst_agent
from agents.planner import run_planner
from agents.rag_agent import run_rag_agent
from agents.sql_agent import run_sql_agent
from memory.redis_checkpointer import get_redis_saver
from memory.redis_memory import get_session_context
from models.llm import get_llm
from tools.mcp_tools import get_mcp_tools
from utils.langchain_utils import last_ai_content
from utils.prompt_loader import load_prompt


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    task_id: str          # 任务唯一ID
    session_id: str       # 会话唯一ID
    question: str         # 用户提问内容
    task_type: str        # 任务类型标识
    plan: list[str]       # 计划步骤列表
    sql: str | None       # 生成的SQL查询
    sql_result: dict | None  # SQL查询结果
    rag_context: list[dict]  # 检索增强上下文
    analysis: str | None  # 推理分析过程
    final_answer: str | None  # 最终回答内容
    status: str           # 任务执行状态
    errors: list[str]     # 错误信息列表
    route: str            # 当前处理节点
    previous_question: str | None
    context_task_id: str | None
    memory_route: str
    memory_reason: str
    memory_confidence: float


async def planner_node(state: AgentState) -> AgentState:
    """
    返回：task_type + plan
    """
    plan = await run_planner(state["question"])
    return {
        **state,
        "task_type": plan["task_type"],
        "route": plan["task_type"],
        "plan": plan["plan"],
        "memory_route": plan.get("memory_route", "none"),
        "memory_reason": plan.get("memory_reason", ""),
        "memory_confidence": plan.get("memory_confidence", 0.0),
        "errors": state.get("errors", []),
    }


CHART_REQUEST_KEYWORDS = (
    "画图", "画个图", "画张图", "生成图", "做图", "出图", "图表", "可视化",
    "柱状图", "折线图", "饼图", "条形图", "散点图",
    "chart", "visualize", "plot",
)

FOLLOWUP_REFERENCE_KEYWORDS = (
    "刚才", "上面", "上一轮", "前面", "这个结果", "这些数据", "当前结果",
    "把这个", "把这些", "现在", "继续", "再",
)

GENERIC_CHART_FOLLOWUPS = {
    "画图", "画个图", "画张图", "做图", "出图", "生成图", "生成图表",
    "可视化", "现在画图", "现在画个图",
}


def _is_chart_followup_question(question: str) -> bool:
    normalized = question.strip().lower()
    has_chart_intent = any(keyword.lower() in normalized for keyword in CHART_REQUEST_KEYWORDS)
    if not has_chart_intent:
        return False
    if normalized in {item.lower() for item in GENERIC_CHART_FOLLOWUPS}:
        return True
    return any(keyword.lower() in normalized for keyword in FOLLOWUP_REFERENCE_KEYWORDS)


async def restore_context_node(state: AgentState) -> AgentState:
    """恢复会话最近一次 SQL 结果，用于“把刚才结果画图”这类追问。"""
    session_id = state.get("session_id")
    errors = state.get("errors", [])
    if not session_id:
        return {
            **state,
            "analysis": "当前请求缺少 session_id，无法复用上一轮结构化查询结果生成图表。",
            "errors": errors,
        }

    context = get_session_context(session_id, "last_sql")
    if not isinstance(context, dict) or not isinstance(context.get("sql_result"), dict):
        return {
            **state,
            "analysis": "当前会话没有可复用的上一轮 SQL 查询结果，请先查询数据后再生成图表。",
            "errors": errors,
        }

    return {
        **state,
        "task_type": "chart_followup",
        "route": "chart_followup",
        "sql": context.get("sql"),
        "sql_result": context.get("sql_result"),
        "analysis": context.get("analysis") or state.get("analysis"),
        "previous_question": context.get("question"),
        "context_task_id": context.get("task_id"),
        "plan": state.get("plan", []) + ["复用上一轮 SQL 查询结果生成图表"],
        "errors": errors,
    }


async def sql_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    生成并执行sql语句并返回查询结果
    """
    question = state["question"]
    if state.get("memory_route") in {"short_term_redis", "hybrid"}:
        recent = _format_recent_messages(list(state.get("messages", [])), limit=6)
        question = f"{question}\n\n最近会话上下文：\n{recent}"
    result = await run_sql_agent(question, config=config)
    return {
        **state,
        "sql": result.get("sql"),
        "sql_result": result.get("sql_result"),
        "analysis": result.get("analysis") or state.get("analysis"),
        "errors": state.get("errors", []) + result.get("errors", []),
    }


async def rag_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """检索企业的知识库，返回 rag_context。"""
    result = await run_rag_agent(state["question"], config=config)
    return {
        **state,
        "rag_context": result.get("rag_context", []),
        "analysis": result.get("analysis") or state.get("analysis"),
        "errors": state.get("errors", []) + result.get("errors", []),
    }


async def analyst_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """汇总 SQL 结果 + RAG 上下文 + 对话历史，输出分析结论。"""
    result = await run_analyst_agent(state, config=config)
    return {**state, "analysis": result["analysis"]}


MCP_SYSTEM_PROMPT = load_prompt("mcp_visualization")

MAX_MCP_STEPS = 3  # 一次选择工具、一次执行、一次整理结果通常足够


def _message_content_text(content: Any) -> str:
    """把 LangChain message/chunk content 归一成可展示文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content) if content else ""


def _format_recent_messages(messages: list, limit: int = 8) -> str:
    """Format recent short-term conversation context for the final answer."""
    rows: list[str] = []
    for message in messages[-limit:]:
        content = _message_content_text(getattr(message, "content", ""))
        if not content:
            continue
        role = message.__class__.__name__.replace("Message", "")
        rows.append(f"- {role}: {content}")
    return "\n".join(rows)


async def mcp_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """根据明确意图直接调用 MCP，再用一次短模型调用整理成品答案。"""
    question = state.get("question", "")
    analysis = state.get("analysis") or ""
    sql_result = state.get("sql_result")
    errors = state.get("errors", [])

    try:
        tools = await get_mcp_tools()
    except Exception as exc:
        return {**state, "analysis": analysis, "errors": errors + [f"MCP工具拉取失败: {exc}"]}
    if not tools:
        return {**state, "analysis": analysis}

    tool_by_name = {t.name: t for t in tools}
    rows = _sql_rows(state)[:50]
    columns = sql_result.get("columns", []) if isinstance(sql_result, dict) else []
    normalized_rows = [row if isinstance(row, dict) else dict(zip(columns, row)) for row in rows]

    def number(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    numeric_columns = [
        column for column in columns
        if any(number(row.get(column)) is not None for row in normalized_rows)
    ]
    category_columns = [column for column in columns if column not in numeric_columns]
    category = category_columns[0] if category_columns else (columns[0] if columns else None)
    numeric = numeric_columns[0] if numeric_columns else None
    observation: Any = ""

    try:
        if any(word in question for word in NUMERIC_ANALYSIS_KEYWORDS) and numeric:
            values = [number(row.get(numeric)) for row in normalized_rows]
            values = [value for value in values if value is not None]
            if any(word in question for word in ("环比", "同比", "增长率", "增速", "变化率")) and len(values) >= 2:
                tool = tool_by_name["station_mcp_calculate_growth_rate"]
                observation = await tool.ainvoke({"current": values[-1], "previous": values[-2]}, config=config)
            elif any(word in question for word in ("千分位", "格式化")) and values:
                tool = tool_by_name["station_mcp_format_number"]
                observation = await tool.ainvoke({"value": values[-1]}, config=config)
            else:
                tool = tool_by_name["station_mcp_compute_statistics"]
                observation = await tool.ainvoke({"numbers": values}, config=config)
        elif normalized_rows and category and numeric:
            title = question[:60]
            common_data = [
                {"category": str(row.get(category, "")), "value": number(row.get(numeric)) or 0}
                for row in normalized_rows
            ]
            if any(word in question for word in ("饼图", "占比", "比例", "份额")):
                tool = tool_by_name["chart_mcp_generate_pie_chart"]
                observation = await tool.ainvoke({"data": common_data, "title": title}, config=config)
            elif any(word in question for word in ("折线", "趋势", "走势", "变化")):
                if len(numeric_columns) >= 2 and "chart_mcp_generate_dual_axes_chart" in tool_by_name:
                    tool = tool_by_name["chart_mcp_generate_dual_axes_chart"]
                    series = [
                        {"type": "column" if index == 0 else "line", "data": [number(row.get(col)) or 0 for row in normalized_rows], "axisYTitle": col}
                        for index, col in enumerate(numeric_columns[:2])
                    ]
                    observation = await tool.ainvoke({"categories": [str(row.get(category, "")) for row in normalized_rows], "series": series, "title": title}, config=config)
                else:
                    tool = tool_by_name["chart_mcp_generate_line_chart"]
                    data = [{"time": str(row.get(category, "")), "value": number(row.get(numeric)) or 0} for row in normalized_rows]
                    observation = await tool.ainvoke({"data": data, "title": title}, config=config)
            elif "条形图" in question:
                tool = tool_by_name["chart_mcp_generate_bar_chart"]
                observation = await tool.ainvoke({"data": common_data, "title": title, "stack": False}, config=config)
            else:
                tool = tool_by_name["chart_mcp_generate_column_chart"]
                observation = await tool.ainvoke({"data": common_data, "title": title, "group": False}, config=config)
    except Exception as exc:
        errors = errors + [f"MCP工具调用失败: {exc}"]

    tool_text = ""
    if isinstance(observation, list):
        tool_text = "\n".join(str(item.get("text", "")) for item in observation if isinstance(item, dict))
    elif observation:
        tool_text = str(observation)

    response = await get_llm().bind(max_tokens=1800).ainvoke(
        [
            SystemMessage(content="根据真实 SQL 结果和工具结果直接回答用户。保留工具返回的图片 URL，并写成 Markdown 图片；给出简洁数据表和2至4条结论；禁止编造；800字以内。"),
            HumanMessage(content=f"用户问题：{question}\nSQL结果：{sql_result}\n工具结果：{tool_text}\n已有错误：{errors}"),
        ],
        config=config,
    )
    return {**state, "analysis": str(response.content), "errors": errors}


FINAL_SYSTEM_PROMPT = load_prompt("final")


async def final_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """直接透传上游成品答案，避免重复调用模型改写。"""
    errors = state.get("errors", [])
    analysis = state.get("analysis") or state.get("final_answer") or ""
    final_answer = analysis.strip()

    if not final_answer:
        if state.get("rag_context"):
            snippets = []
            for item in state.get("rag_context", [])[:3]:
                source = item.get("source") or "unknown"
                content = item.get("content") or ""
                snippets.append(f"- 来源：{source}\n  内容：{content}")
            final_answer = "根据知识库检索结果：\n" + "\n".join(snippets)
        elif state.get("sql_result"):
            final_answer = "已完成 SQL 查询"
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
    """planner 之后的条件路由：知识问答走 rag，其余走 sql。"""
    if _is_chart_followup_question(state.get("question", "")):
        return "restore_context"
    if state.get("task_type") == "knowledge_query":
        return "rag"
    return "sql"


def route_after_restore_context(state: AgentState) -> str:
    """恢复到上一轮 SQL 结果后直接绘图；没有可用上下文则收口提示。"""
    sql_result = state.get("sql_result")
    if isinstance(sql_result, dict) and sql_result.get("rows"):
        return "mcp"
    return "final"


def route_after_sql(state: AgentState) -> str:
    """sql 之后的条件路由：复杂分析再走 rag，其余直接进 analyst。"""
    if state.get("task_type") == "complex_analysis":
        return "rag"
    if _has_explicit_mcp_intent(state.get("question", "")):
        return "mcp"
    return "analyst"


def route_after_rag(state: AgentState) -> str:
    """rag 之后的条件路由：知识问答直接收口，其余进 analyst。"""
    if state.get("task_type") == "knowledge_query":
        return "final"
    if _has_explicit_mcp_intent(state.get("question", "")) and state.get("sql_result"):
        return "mcp"
    return "analyst"

MCP_INTENT_KEYWORDS = (
    "柱状图", "柱形图", "条形图", "折线图", "饼图", "散点图", "双轴图", "直方图",
    "透视表", "生成表格", "图表", "可视化", "画图", "生成图", "做图", "出图",
    "chart", "visualize", "plot",
)

# 数值计算意图：纯数值问题(无画图诉求)也走 mcp，用自建数值计算 Skill 做统计/增长率/格式化。
NUMERIC_ANALYSIS_KEYWORDS = (
    "计算环比", "计算同比", "计算增长率", "计算增速", "计算变化率",
    "计算均值", "计算平均值", "计算中位数", "计算众数", "计算标准差", "计算方差",
    "中位数", "众数", "标准差", "方差", "分位数", "四分位",
    "描述统计", "统计描述", "千分位", "格式化数值",
)


def _has_explicit_mcp_intent(question: str) -> bool:
    text = question.lower()
    return any(keyword.lower() in text for keyword in MCP_INTENT_KEYWORDS + NUMERIC_ANALYSIS_KEYWORDS)


def _sql_rows(state: AgentState) -> list:
    sql_result = state.get("sql_result")
    if not isinstance(sql_result, dict):
        return []
    rows = sql_result.get("rows")
    return rows if isinstance(rows, list) else []


def route_after_analysis(state: AgentState) -> str:
    """analyst 之后按需路由：图表可视化或数值计算意图时调用 MCP。"""
    if state.get("task_type") == "knowledge_query":
        return "final"

    sql_result = state.get("sql_result")
    if not isinstance(sql_result, dict) or sql_result.get("error"):
        return "final"

    # 只依据用户原话决定是否调用工具，避免分析文本中的“趋势”等词误触发 MCP。
    text = state.get("question", "").lower()

    # 数值计算意图(环比/统计/格式化等)走 MCP：工具直接消费 SQL 数值，不受多行多列限制。
    if any(keyword.lower() in text for keyword in NUMERIC_ANALYSIS_KEYWORDS):
        return "mcp"

    rows = _sql_rows(state)
    row_count = sql_result.get("row_count")
    if not isinstance(row_count, int):
        row_count = len(rows)
    if row_count <= 1:
        return "final"

    columns = sql_result.get("columns")
    if not isinstance(columns, list) or len(columns) < 2:
        return "final"

    if any(keyword.lower() in text for keyword in MCP_INTENT_KEYWORDS):
        return "mcp"

    return "final"

# build 为 async（需 await get_redis_saver() 做 asetup），
# 个请求在事件循环内建好后复用
_compiled_graph = None

async def build_agent_graph():
    """构建并编译企业数据分析状态图，缓存编译后的图单例。"""
    global _compiled_graph
    if _compiled_graph is None:
        checkpointer = await get_redis_saver()
        graph = StateGraph(AgentState)
        graph.add_node("planner", planner_node)
        graph.add_node("restore_context", restore_context_node)
        graph.add_node("sql", sql_node)
        graph.add_node("rag", rag_node)
        graph.add_node("analyst", analyst_node)
        graph.add_node("mcp", mcp_node)
        graph.add_node("final", final_node)

        graph.set_entry_point("planner")
        graph.add_conditional_edges(
            "planner",
            route_after_planner,
            {
                "restore_context": "restore_context",
                "sql": "sql",
                "rag": "rag",
            },
        )
        graph.add_conditional_edges(
            "restore_context",
            route_after_restore_context,
            {
                "mcp": "mcp",
                "final": "final",
            },
        )
        graph.add_conditional_edges(
            "sql",
            route_after_sql,
            {
                "rag": "rag",
                "analyst": "analyst",
                "mcp": "mcp",
            },
        )
        graph.add_conditional_edges(
            "rag",
            route_after_rag,
            {
                "analyst": "analyst",
                "final": "final",
                "mcp": "mcp",
            },
        )
        graph.add_conditional_edges(
            "analyst",
            route_after_analysis,
            {
                "mcp": "mcp",
                "final": "final",
            },
        )
        graph.add_edge("mcp", "final")
        graph.add_edge("final", END)
        _compiled_graph = graph.compile(checkpointer=checkpointer)
    return _compiled_graph

# 调试用的，非流式的
async def run_agent_workflow(question: str, session_id: str, task_id: str) -> AgentState:
    """运行一次完整 Agent 工作流，按 session_id 续接对话历史并返回最终状态。"""
    app = await build_agent_graph()
    return await app.ainvoke(
        {
            "task_id": task_id,
            "session_id": session_id,
            "question": question.strip(),
            "messages": [HumanMessage(content=question.strip())],
            "errors": [],
            "rag_context": [],
        },
        config={
            "recursion_limit": 40,
            "configurable": {
                "thread_id": session_id,
                "user_id": session_id,
            }
        },
    )

# 用于向前端汇报转接路口，流式输出
def _legacy_next_node(node: str, task_type: str | None, state: AgentState | None = None) -> str | None:
    """复刻条件路由：根据当前节点 + 任务类型推断下路由一节点。
    """
    if node == "planner":
        return "rag" if task_type == "knowledge_query" else "sql"
    if node == "sql":
        return "rag" if task_type == "complex_analysis" else "analyst"
    if node == "rag":
        return "final" if task_type == "knowledge_query" else "analyst"
    if node == "analyst":
        return route_after_analysis(state or {}) if state else "final"
    if node == "mcp":
        return "final"
    return None

# 各节点对应的"正在做什么"状态文案，供流式状态推送。
NODE_STATUS = {
    "planner": "正在理解问题、规划任务...",
    "sql": "正在查询数据库...",
    "rag": "正在检索知识库...",
    "analyst": "正在汇总分析...",
    "mcp": "正在调用工具、生成图表与数值计算...",
    "final": "正在组织最终回答",
}
async def _legacy_run_agent_workflow_stream(question: str, session_id: str, task_id: str):
    """流式执行图：按节点 yield NODE_STATUS： ("status", 文案)；
    图结束后 yield ("final", 最终 state)。

    stream_mode="updates" 在每个节点完成时产出其更新；节点完成 = 下一节点开始，
    故此时推送下一节点的状态文案，让用户实时看到"正在 X"。
    首节点 planner 的状态在构图前先推一次，让用户立刻看到反馈。
    """
    yield "status", NODE_STATUS["planner"] # 立刻反馈：正在规划

    app = await build_agent_graph()
    inputs = {
        "task_id": task_id,
        "session_id": session_id,
        "question": question.strip(),
        "messages": [HumanMessage(content=question.strip())],
        "errors": [],
        "rag_context": [],
    }
    config = {"recursion_limit": 40, "configurable": {"thread_id": session_id, "user_id": session_id}}

    final_state: dict = {}
    task_type: str | None = None
    async for chunk in app.astream(inputs, config=config, stream_mode="updates"):
        for node, update in chunk.items():
            if isinstance(update, dict):
                if update.get("task_type"):
                    task_type = update["task_type"]
                final_state.update(update)
            nxt = _legacy_next_node(node, task_type, final_state)
            if nxt in NODE_STATUS:
                yield "status", NODE_STATUS[nxt]
    yield "final", final_state


# Event-based streaming implementation. This definition intentionally overrides
# the legacy NODE_STATUS/update-stream version above.
AGENT_STEP_META = {
    "planner": {"title": "任务规划", "description": "识别问题类型并制定执行步骤"},
    "restore_context": {"title": "恢复上下文", "description": "读取会话最近一次结构化查询结果"},
    "sql": {"title": "数据查询", "description": "生成并执行只读 SQL，获取结构化数据"},
    "rag": {"title": "知识检索", "description": "检索企业知识库，补充指标口径和业务规则"},
    "analyst": {"title": "分析归纳", "description": "汇总 SQL 结果、知识上下文和历史记忆"},
    "mcp": {"title": "工具执行", "description": "按需调用 MCP 图表或数值计算工具生成结果"},
    "final": {"title": "生成回答", "description": "组织最终答复并进行 token 流式输出"},
}

ANSWER_STREAM_NODES = {"final"}


def _event_node(event: dict[str, Any]) -> str | None:
    metadata = event.get("metadata") or {}
    node = metadata.get("langgraph_node")
    return str(node) if node else None


def _step_payload(node: str) -> dict[str, Any]:
    meta = AGENT_STEP_META[node]
    return {"node": node, "title": meta["title"], "description": meta["description"]}


def _merge_state_from_event(final_state: dict, event: dict[str, Any]) -> None:
    data = event.get("data") or {}
    output = data.get("output")
    chunk = data.get("chunk")
    if isinstance(output, dict):
        final_state.update(output)
    if isinstance(chunk, dict):
        for value in chunk.values():
            if isinstance(value, dict):
                final_state.update(value)


async def run_agent_workflow_stream(question: str, session_id: str, task_id: str):
    """基于 LangGraph 事件流输出 Agent 状态与最终回答 token。"""
    yield "workflow_start", {"task_id": task_id, "session_id": session_id}

    app = await build_agent_graph()
    inputs = {
        "task_id": task_id,
        "session_id": session_id,
        "question": question.strip(),
        "messages": [HumanMessage(content=question.strip())],
        "errors": [],
        "rag_context": [],
    }
    config = {"recursion_limit": 40, "configurable": {"thread_id": session_id, "user_id": session_id}}

    final_state: dict = {}
    streamed_answer = False

    async for event in app.astream_events(inputs, config=config, version="v2"):
        event_type = event.get("event")
        event_name = event.get("name")
        node = _event_node(event)

        if event_type == "on_chain_start" and node in AGENT_STEP_META:
            yield "step_start", _step_payload(node)
            continue

        if event_type == "on_chain_stream":
            _merge_state_from_event(final_state, event)
            continue

        if event_type == "on_chain_end":
            _merge_state_from_event(final_state, event)
            if node in AGENT_STEP_META:
                yield "step_end", _step_payload(node)
            elif event_name == "LangGraph":
                output = (event.get("data") or {}).get("output")
                if isinstance(output, dict):
                    final_state.update(output)
            continue

        # 工具调用事件（on_tool_start / on_tool_end）不透传到流式响应：
        # 工具名与入参会暴露内部实现，工具观测已在 utils/llm_callback.py 服务端记录。
        if event_type in ("on_tool_start", "on_tool_end"):
            continue

        if event_type == "on_chat_model_stream" and node in ANSWER_STREAM_NODES:
            chunk = (event.get("data") or {}).get("chunk")
            content = _message_content_text(getattr(chunk, "content", ""))
            if content:
                streamed_answer = True
                yield "chunk", {"node": node, "content": content}

    final_state["_streamed_answer"] = streamed_answer
    yield "workflow_end", {"task_id": task_id, "session_id": session_id}
    yield "final", final_state
