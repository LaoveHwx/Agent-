"""
企业数据分析 Agent 状态图（LangGraph 编排）。

拓扑（条件路由）：
    知识问答:    planner -> rag -> final
    数据查询:   planner -> sql -> analyst -> mcp -> final
    复杂分析:   planner -> sql -> rag -> analyst -> mcp -> final

mcp 节点用「绑定图表 MCP 工具的大模型」对数据做可视化（柱状/折线/饼图/表格等）；
MCP 工具为 async-only，故所有节点统一 async、graph 全程走 ainvoke。

对话历史：
    state.messages 由 RedisSaver checkpointer 按 thread_id 自动续接，
    final_node 把最终答案作为 AIMessage 累积进 messages，实现多轮上下文。

节点约定：
    每个节点读 state -> 调对应 agent -> 返回 dict 更新 state；
    错误累积进 state.errors，由 final_node 统一收口。
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph, add_messages

from agents.analyst import run_analyst_agent
from agents.planner import run_planner
from agents.rag_agent import run_rag_agent
from agents.sql_agent import run_sql_agent
from memory.redis_checkpointer import get_redis_saver
from models.llm import get_llm
from tools.mcp_tools import get_mcp_tools
from utils.langchain_utils import last_ai_content


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
        "errors": state.get("errors", []),
    }


async def sql_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    生成并执行sql语句并返回查询结果
    """
    result = await run_sql_agent(state["question"], config=config)
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


MCP_SYSTEM_PROMPT = """你是企业数据分析系统的数据可视化节点。上游路由已经判断当前结果需要 MCP 可视化，你的职责是选择合适的图表工具并生成可追溯的最终回答。
工作流程：
1. 根据用户问题、SQL 查询结果和已有分析，选择最合适的 MCP 图表工具；
2. 优先调用一个图表工具：柱状/条形用于类别数值比较，折线用于时间趋势，饼图用于占比，散点用于两变量关系，表格/透视表用于明细或汇总，双轴用于两指标同图，直方图用于数据分布，漏斗用于阶段转化，瀑布用于累计增减；
3. 工具返回后，把图表结果和已有分析整合成简洁回答。
要求：图表数据必须来自已有 SQL 查询结果，严禁编造；图表尺寸保持紧凑（宽 450px 左右，工具支持尺寸/width 参数时显式传入小值）；如果数据不足以生成任何图表，说明原因并直接返回已有分析。"""

MAX_MCP_STEPS = 5  # 工具调用循环上限，防止模型反复调工具

async def mcp_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """数据可视化节点：用「绑定图表 MCP 工具的大模型」对数据做可视化。

    是否进入 MCP 由 route_after_analysis 决定；
    bind_tools 只让大模型自主选择合适的图表工具和参数。
    MCP 服务未启动/无工具时降级透传，不阻断主流程。
    """
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
    llm = get_llm().bind_tools(tools)

    messages: list = [
        SystemMessage(content=MCP_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"用户问题：{question}\n\n"
            f"SQL 查询结果：{sql_result}\n\n"
            f"已有分析：{analysis}\n\n"
            "请基于以上真实 SQL 结果选择并调用一个合适的图表 MCP 工具，不得编造数据；"
            "如果 SQL 结果确实不足以支撑图表，请说明原因并直接整理已有分析作答。"
        )),
    ]

    # 工具调用循环：模型出 tool_calls -> 执行 -> 回填 ToolMessage -> 再问，直到无 tool_calls
    for _ in range(MAX_MCP_STEPS):
        ai_msg: AIMessage = await llm.ainvoke(messages, config=config)
        messages.append(ai_msg)
        if not getattr(ai_msg, "tool_calls", None):
            break
        for tc in ai_msg.tool_calls:
            tool = tool_by_name.get(tc.get("name"))
            if tool is None:
                continue
            try:
                observation = await tool.ainvoke(tc.get("args", {}), config=config)
            except Exception as exc:
                observation = f"工具调用失败: {exc}"
            messages.append(ToolMessage(
                content=str(observation),
                tool_call_id=tc.get("id", ""),
                name=tc.get("name", ""),
            ))

    final_analysis = last_ai_content({"messages": messages}) or analysis
    return {**state, "analysis": final_analysis}


async def final_node(state: AgentState) -> AgentState:
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
    if state.get("task_type") == "knowledge_query":
        return "rag"
    return "sql"


def route_after_sql(state: AgentState) -> str:
    """sql 之后的条件路由：复杂分析再走 rag，其余直接进 analyst。"""
    if state.get("task_type") == "complex_analysis":
        return "rag"
    return "analyst"


def route_after_rag(state: AgentState) -> str:
    """rag 之后的条件路由：知识问答直接收口，其余进 analyst。"""
    if state.get("task_type") == "knowledge_query":
        return "final"
    return "analyst"

MCP_INTENT_KEYWORDS = (
    "柱状", "柱形", "柱状图", "条形", "条形图", "对比", "比较", "排名", "排行",
    "bar", "column", "compare", "comparison", "rank", "ranking",
    "折线", "折线图", "趋势", "走势", "变化", "时间序列",
    "line", "trend", "time series",
    "饼图", "占比", "比例", "构成", "份额",
    "pie", "share", "proportion", "percentage",
    "散点", "散点图", "相关性", "关系", "两变量",
    "scatter", "correlation", "relationship",
    "表格", "透视表", "明细表", "汇总表",
    "table", "spreadsheet", "pivot",
    "双轴", "双坐标", "双指标", "两个指标", "同图",
    "dual axes", "dual-axis", "two metrics",
    "直方图", "分布", "频率", "频次", "区间分布",
    "histogram", "distribution", "frequency",
    "漏斗", "转化", "转化率", "阶段", "流程",
    "funnel", "conversion", "stage",
    "瀑布", "瀑布图", "累计", "增减", "变动拆解", "财务",
    "waterfall", "cumulative", "increment", "decrement", "financial",
    "图", "图表", "可视化", "画图", "生成图",
    "chart", "visual", "visualize", "plot",
)


def _sql_rows(state: AgentState) -> list:
    sql_result = state.get("sql_result")
    if not isinstance(sql_result, dict):
        return []
    rows = sql_result.get("rows")
    return rows if isinstance(rows, list) else []


def route_after_analysis(state: AgentState) -> str:
    """analyst 之后按需路由：只有结果适合/明确需要可视化时才调用 MCP。"""
    if state.get("task_type") == "knowledge_query":
        return "final"

    sql_result = state.get("sql_result")
    if not isinstance(sql_result, dict) or sql_result.get("error"):
        return "final"

    rows = _sql_rows(state)
    row_count = sql_result.get("row_count")
    if not isinstance(row_count, int):
        row_count = len(rows)
    if row_count <= 1:
        return "final"

    columns = sql_result.get("columns")
    if not isinstance(columns, list) or len(columns) < 2:
        return "final"

    text = f"{state.get('question', '')}\n{state.get('analysis', '')}".lower()
    if any(keyword.lower() in text for keyword in MCP_INTENT_KEYWORDS):
        return "mcp"

    # 复杂分析通常需要比较多行结果，图表能帮助说明；普通明细查询默认不打扰 MCP。
    if state.get("task_type") == "complex_analysis" and row_count > 1:
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
            "configurable": {
                "thread_id": session_id,
                "user_id": session_id,
            }
        },
    )

# 用于向前端汇报转接路口，流式输出
def _next_node(node: str, task_type: str | None, state: AgentState | None = None) -> str | None:
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
    "mcp": "正在调用工具、生成图表...",
    "final": "正在组织最终回答",
}
async def run_agent_workflow_stream(question: str, session_id: str, task_id: str):
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
    config = {"configurable": {"thread_id": session_id, "user_id": session_id}}

    final_state: dict = {}
    task_type: str | None = None
    async for chunk in app.astream(inputs, config=config, stream_mode="updates"):
        for node, update in chunk.items():
            if isinstance(update, dict):
                if update.get("task_type"):
                    task_type = update["task_type"]
                final_state.update(update)
            nxt = _next_node(node, task_type, final_state)
            if nxt in NODE_STATUS:
                yield "status", NODE_STATUS[nxt]
    yield "final", final_state
