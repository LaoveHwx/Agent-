"""
PostgreSQL connection pool.

The project uses psycopg directly, so psycopg_pool keeps the existing query
code style while avoiding a new database connection for every SQL/RAG call.
"""
from functools import lru_cache

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from utils.env_util import (
    connection_string,
    connectioned_string,
    postgres_pool_max_lifetime,
    postgres_pool_max_size,
    postgres_pool_min_size,
    postgres_pool_timeout,
    ps_dsn,
)


def _dsn() -> str:
    """解析已配置的 PostgreSQL DSN"""
    dsn = ps_dsn or connection_string or connectioned_string
    if not dsn:
        raise RuntimeError("PostgreSQL DSN is not configured. Please set PS_DSN in .env")
    return dsn


def _int_value(raw_value: str | None, default: int) -> int:
    """解析一个正整数配置值，如果失败就使用默认值。"""
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


@lru_cache
def get_postgres_pool() -> ConnectionPool:
    """构建并缓存本地进程的 PostgreSQL 连接池"""
    min_size = _int_value(postgres_pool_min_size, 1)
    max_size = _int_value(postgres_pool_max_size, 10)
    timeout = _int_value(postgres_pool_timeout, 10)
    max_lifetime = _int_value(postgres_pool_max_lifetime, 3600)

    if min_size > max_size:
        min_size = max_size

    return ConnectionPool(
        conninfo=_dsn(),
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        max_lifetime=max_lifetime,
        kwargs={"row_factory": dict_row},
    )


def get_connection():
    """从连接池借一个 PostgreSQL 连接"""
    return get_postgres_pool().connection()


def close_postgres_pool() -> None:
    """如果缓存的 PostgreSQL 连接池已经创建，就关闭它。"""
    if get_postgres_pool.cache_info().currsize == 0:
        return
    get_postgres_pool().close()
    get_postgres_pool.cache_clear()
