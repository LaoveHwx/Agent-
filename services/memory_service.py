from langchain_core.messages import AIMessage, HumanMessage

from graph.center_graph import build_agent_graph
from memory.redis_memory import get_agent_state, memory_status
from schemas.memory import AgentStateResponse, ConversationResponse, MemoryStatusResponse


def read_memory_status() -> MemoryStatusResponse:
    return MemoryStatusResponse(**memory_status())


def read_conversation(session_id: str) -> ConversationResponse:
    """从 checkpointer 读取指定会话（thread_id）的对话历史。

    对话历史现由 LangGraph checkpointer 按 thread_id 自动续接存储，
    不再从 redis_memory 的 conversation 列表读取。
    """
    app = build_agent_graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = app.get_state(config)

    messages = []
    if snapshot and snapshot.values:
        for message in snapshot.values.get("messages", []):
            role = "assistant" if isinstance(message, AIMessage) else "user"
            messages.append({"role": role, "content": getattr(message, "content", "")})

    return ConversationResponse(session_id=session_id, messages=messages)


def read_agent_state(task_id: str) -> AgentStateResponse:
    return AgentStateResponse(task_id=task_id, state=get_agent_state(task_id))
