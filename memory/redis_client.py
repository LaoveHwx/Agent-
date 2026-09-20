"""
Redis 客户端工厂：同步 + 异步双客户端。

get_redis_client / get_async_redis_client 按 env 配置构建 Redis / AsyncRedis，
decode_responses=True 直接返回字符串；异步客户端供 AsyncRedisSaver 等 async-only 组件使用。
"""
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from utils.env_util import redis_db, redis_host, redis_password, redis_port


def _int_value(raw_value: str | None, default: int) -> int:
    """将环境变量解析为 int，缺省或非正返回默认值。"""
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def get_redis_client(db: int | None = None) -> Redis:
    """构建同步 Redis 客户端，按 env 配置连接并 decode_responses。"""
    return Redis(
        host=redis_host,
        port=_int_value(redis_port, 6379),
        db=_int_value(redis_db, 0) if db is None else db,
        password=redis_password,
        decode_responses=True,
    )


def get_async_redis_client(db: int | None = None) -> AsyncRedis:
    """异步 Redis 客户端，供 AsyncRedisSaver 等 async-only 组件使用。"""
    return AsyncRedis(
        host=redis_host,
        port=_int_value(redis_port, 6379),
        db=_int_value(redis_db, 0) if db is None else db,
        password=redis_password,
        decode_responses=True,
    )
