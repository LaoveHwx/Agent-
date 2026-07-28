from functools import lru_cache

from langgraph.checkpoint.redis import RedisSaver

from memory.redis_client import get_redis_client
from utils.env_util import memory_ttl_seconds


def _int_value(raw_value: str | None, default: int) -> int:
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


@lru_cache
def get_redis_saver() -> RedisSaver:
    redis_saver = RedisSaver(
        redis_client=get_redis_client(),
        ttl={"default": _int_value(memory_ttl_seconds, 604800)},
    )
    redis_saver.setup()
    return redis_saver
