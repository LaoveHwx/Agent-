from redis import Redis

from utils.env_util import redis_db, redis_host, redis_password, redis_port


def _int_value(raw_value: str | None, default: int) -> int:
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value


def get_redis_client(db: int | None = None) -> Redis:
    return Redis(
        host=redis_host,
        port=_int_value(redis_port, 6379),
        db=_int_value(redis_db, 0) if db is None else db,
        password=redis_password,
        decode_responses=True,
    )
