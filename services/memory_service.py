from memory.redis_memory import get_agent_state, get_conversation, memory_status
from schemas.memory import AgentStateResponse, ConversationResponse, MemoryStatusResponse


def read_memory_status() -> MemoryStatusResponse:
    return MemoryStatusResponse(**memory_status())


def read_conversation(session_id: str) -> ConversationResponse:
    return ConversationResponse(session_id=session_id, messages=get_conversation(session_id))


def read_agent_state(task_id: str) -> AgentStateResponse:
    return AgentStateResponse(task_id=task_id, state=get_agent_state(task_id))
