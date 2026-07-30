"""
Redis 记忆存储：Agent 状态与工具结果持久化。

按 KEY_PREFIX 分桶，save/get_agent_state 存任务状态快照，
save/get_tool_result 按 task_id + tool_name 存工具产物；统一 TTL 与 JSON 序列化。
"""
import json
from typing import Any

from memory.redis_client import get_redis_client
from utils.env_util import memory_ttl_seconds, redis_db
from utils.logger import setup_logger


logger = setup_logger(__name__)
KEY_PREFIX = "data_agent"


def _int_value(raw_value: str | None, default: int) -> int:
    """将环境变量解析为 int，缺省或非正返回默认值。"""
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _selected_db() -> int:
    """根据环境变量选取 Redis DB 编号，越界抛 RuntimeError。"""
    db = _int_value(redis_db, 0)
    if db < 0 or db > 15:
        raise RuntimeError("Redis DB must be between 0 and 15")
    return db


def _redis_client():
    """返回当前选中 DB 的 Redis 客户端。"""
    return get_redis_client(_selected_db())


def _json_dumps(value: Any) -> str:
    """将对象 JSON 序列化为字符串，保留中文且兜底转 str。"""
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: str | None) -> Any:
    """将 JSON 字符串反序列化为对象，空值返回 None。"""
    if value is None:
        return None
    return json.loads(value)


def memory_status() -> dict[str, Any]:
    """返回 Redis 连接状态与记忆分桶信息。"""
    client = _redis_client()
    pong = client.ping()
    return {
        "status": "ok" if pong else "failed",
        "redis_db": _selected_db(),
        "key_prefix": KEY_PREFIX,
    }


def save_agent_state(task_id: str, state: dict[str, Any]) -> None:
    """按 task_id 持久化 Agent 状态快照，带 TTL。"""
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    client.setex(f"{KEY_PREFIX}:agent_state:{task_id}", ttl, _json_dumps(state))


def get_agent_state(task_id: str) -> dict[str, Any] | None:
    """按 task_id 读取 Agent 状态快照。"""
    client = _redis_client()
    return _json_loads(client.get(f"{KEY_PREFIX}:agent_state:{task_id}"))


def save_tool_result(task_id: str, tool_name: str, result: dict[str, Any]) -> None:
    """按 task_id 与 tool_name 持久化工具产物，带 TTL。"""
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    key = f"{KEY_PREFIX}:tool_result:{task_id}:{tool_name}"
    client.setex(key, ttl, _json_dumps(result))


def get_tool_result(task_id: str, tool_name: str) -> dict[str, Any] | None:
    """按 task_id 与 tool_name 读取工具产物。"""
    client = _redis_client()
    key = f"{KEY_PREFIX}:tool_result:{task_id}:{tool_name}"
    return _json_loads(client.get(key))


def save_session_context(session_id: str, context_name: str, context: dict[str, Any]) -> None:
    """Save reusable session-scoped context, such as the latest SQL result."""
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    key = f"{KEY_PREFIX}:session_context:{session_id}:{context_name}"
    client.setex(key, ttl, _json_dumps(context))


def get_session_context(session_id: str, context_name: str) -> dict[str, Any] | None:
    """Read reusable session-scoped context."""
    client = _redis_client()
    key = f"{KEY_PREFIX}:session_context:{session_id}:{context_name}"
    return _json_loads(client.get(key))
