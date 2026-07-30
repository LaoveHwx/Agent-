"""
Redis checkpointer：LangGraph 异步状态续接。

get_redis_saver 惰性创建 AsyncRedisSaver 单例并 asetup，graph 全程走 ainvoke 故必须
用异步 saver；同一事件循环内复用，TTL 来自 env。
"""
from langgraph.checkpoint.redis import AsyncRedisSaver

from memory.redis_client import get_async_redis_client
from utils.env_util import memory_ttl_seconds


def _int_value(raw_value: str | None, default: int) -> int:
    """将环境变量解析为 int，缺省或非正返回默认值。"""
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


# 异步 checkpointer 单例。
# graph 全程走 ainvoke，必须用 AsyncRedisSaver：同步 RedisSaver 的 aget_tuple 会抛
# NotImplementedError。asetup() 需捕获运行中的事件循环，故 get_redis_saver 为 async，
# 首次调用时建好并缓存（同一 uvicorn 事件循环内复用）。
_async_saver: AsyncRedisSaver | None = None


async def get_redis_saver() -> AsyncRedisSaver:
    """惰性创建并缓存 AsyncRedisSaver 单例，供 LangGraph 异步状态续接。"""
    global _async_saver
    if _async_saver is None:
        saver = AsyncRedisSaver(
            redis_client=get_async_redis_client(),
            ttl={"default": _int_value(memory_ttl_seconds, 604800)},
        )
        await saver.asetup()
        _async_saver = saver
    return _async_saver
