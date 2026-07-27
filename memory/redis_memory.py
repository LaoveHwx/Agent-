import json
from typing import Any
from urllib.parse import urlparse

import redis

from utils.env_util import memory_max_messages, memory_ttl_seconds, redis_db, redis_url
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
    db = _int_value(redis_db, 2)
    if db == 1:
        raise RuntimeError("Redis DB 1 is reserved. Please set REDIS_DB to 0 or 2-15")
    if db < 0 or db > 15:
        raise RuntimeError("Redis DB must be between 0 and 15")
    return db


def _url_has_db(url: str) -> bool:
    path = urlparse(url).path.strip("/")
    return path.isdigit()


def _redis_client() -> redis.Redis:
    if not redis_url:
        raise RuntimeError("Redis URL is not configured. Please set REDIS_URL in .env")

    if _url_has_db(redis_url):
        url_db = int(urlparse(redis_url).path.strip("/"))
        if url_db == 1:
            raise RuntimeError("Redis DB 1 is reserved. Please use another Redis DB")
        return redis.from_url(redis_url, decode_responses=True)

    return redis.from_url(redis_url, db=_selected_db(), decode_responses=True)


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
        "redis_db": _selected_db() if not _url_has_db(redis_url or "") else int(urlparse(redis_url or "").path.strip("/")),
        "key_prefix": KEY_PREFIX,
    }


def save_agent_state(task_id: str, state: dict[str, Any]) -> None:
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    client.setex(f"{KEY_PREFIX}:agent_state:{task_id}", ttl, _json_dumps(state))


def get_agent_state(task_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    return _json_loads(client.get(f"{KEY_PREFIX}:agent_state:{task_id}"))


def append_conversation_message(session_id: str, message: dict[str, Any]) -> None:
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    max_messages = _int_value(memory_max_messages, 20)
    key = f"{KEY_PREFIX}:conversation:{session_id}"

    client.rpush(key, _json_dumps(message))
    client.ltrim(key, -max_messages, -1)
    client.expire(key, ttl)


def get_conversation(session_id: str) -> list[dict[str, Any]]:
    client = _redis_client()
    values = client.lrange(f"{KEY_PREFIX}:conversation:{session_id}", 0, -1)
    return [_json_loads(value) for value in values]


def save_tool_result(task_id: str, tool_name: str, result: dict[str, Any]) -> None:
    client = _redis_client()
    ttl = _int_value(memory_ttl_seconds, 604800)
    key = f"{KEY_PREFIX}:tool_result:{task_id}:{tool_name}"
    client.setex(key, ttl, _json_dumps(result))


def get_tool_result(task_id: str, tool_name: str) -> dict[str, Any] | None:
    client = _redis_client()
    key = f"{KEY_PREFIX}:tool_result:{task_id}:{tool_name}"
    return _json_loads(client.get(key))
