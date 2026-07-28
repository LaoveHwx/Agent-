import json
from typing import Any

from memory.redis_client import get_redis_client
from utils.env_util import memory_ttl_seconds, redis_db
from utils.logger import setup_logger


logger = setup_logger(__name__)
KEY_PREFIX = "data_agent"


def _int_value(raw_value: str | None, default: int) -> int:
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _selected_db() -> int:
    db = _int_value(redis_db, 0)
    if db < 0 or db > 15:
        raise RuntimeError("Redis DB must be between 0 and 15")
    return db


def _redis_client():
    return get_redis_client(_selected_db())


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


def memory_status() -> dict[str, Any]:
    client = _redis_client()
    pong = client.ping()
    return {
        "status": "ok" if pong else "failed",
        "redis_db": _selected_db(),
        "key_prefix": KEY_PREFIX,
    }


def save_agent_state(task_id: str, state: dict[str, Any]) -> None:
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    client.setex(f"{KEY_PREFIX}:agent_state:{task_id}", ttl, _json_dumps(state))


def get_agent_state(task_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    return _json_loads(client.get(f"{KEY_PREFIX}:agent_state:{task_id}"))


def save_tool_result(task_id: str, tool_name: str, result: dict[str, Any]) -> None:
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    key = f"{KEY_PREFIX}:tool_result:{task_id}:{tool_name}"
    client.setex(key, ttl, _json_dumps(result))


def get_tool_result(task_id: str, tool_name: str) -> dict[str, Any] | None:
    client = _redis_client()
    key = f"{KEY_PREFIX}:tool_result:{task_id}:{tool_name}"
    return _json_loads(client.get(key))
