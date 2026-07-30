"""
记忆服务层：状态、会话历史、Agent 状态读取。

read_memory_status 探活 Redis；read_conversation 从 checkpointer 按 thread_id 取对话历史；
read_agent_state 取任务状态快照。
"""
from langchain_core.messages import AIMessage, HumanMessage

from graph.center_graph import build_agent_graph
from memory.redis_memory import get_agent_state, memory_status
from schemas.memory import AgentStateResponse, ConversationResponse, MemoryStatusResponse


def read_memory_status() -> MemoryStatusResponse:
    """探活 Redis 记忆层并返回状态。"""
    return MemoryStatusResponse(**memory_status())


async def read_conversation(session_id: str) -> ConversationResponse:
    """从 checkpointer 读取指定会话（thread_id）的对话历史。

    对话历史现由 LangGraph checkpointer 按 thread_id 自动续接存储，
    不再从 redis_memory 的 conversation 列表读取。
    graph 全程走 ainvoke + 异步 checkpointer，故用 aget_state。
    """
    app = await build_agent_graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await app.aget_state(config)

    messages = []
    if snapshot and snapshot.values:
        for message in snapshot.values.get("messages", []):
            role = "assistant" if isinstance(message, AIMessage) else "user"
            messages.append({"role": role, "content": getattr(message, "content", "")})

    return ConversationResponse(session_id=session_id, messages=messages)


def read_agent_state(task_id: str) -> AgentStateResponse:
    """读取指定任务在记忆层的状态快照。"""
    return AgentStateResponse(task_id=task_id, state=get_agent_state(task_id))
