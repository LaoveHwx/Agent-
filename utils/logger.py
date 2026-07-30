"""
日志与请求中间件：统一 logger 配置 + 请求 ID 透传 + 敏感信息脱敏。

setup_logger 提供带 request_id 的控制台 logger；request_log_middleware 给每个
HTTP 请求注入 X-Request-ID 并记录耗时与状态；SensitiveDataFilter 在日志落盘前对
api_key、Authorization、数据库连接串做掩码，避免敏感信息泄漏。
"""
import logging
import re
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

SENSITIVE_PATTERNS = (
    (re.compile(r"(api[_-]?key\s*=\s*)[^,\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(authorization:\s*bearer\s+)[^,\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(postgresql://[^:]+:)[^@]+(@)", re.IGNORECASE), r"\1***\2"),
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """给日志记录注入当前请求 ID。"""
        record.request_id = request_id_context.get()
        return True


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """对日志消息中的 api_key、Authorization、数据库连接串做掩码脱敏。"""
        message = record.getMessage()
        for pattern, replacement in SENSITIVE_PATTERNS:
            message = pattern.sub(replacement, message)

        record.msg = message
        record.args = ()
        return True


def setup_logger(name: str = "data_agent") -> logging.Logger:
    """配置带请求 ID 与脱敏过滤的控制台 logger。"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [request_id=%(request_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger


async def request_log_middleware(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """给 HTTP 请求注入请求 ID 并记录耗时与状态的中间件。"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    logger = setup_logger("http")
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        cost_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed method=%s path=%s status_code=%s cost_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            cost_ms,
        )
        return response
    except Exception:
        cost_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "request failed method=%s path=%s cost_ms=%.2f",
            request.method,
            request.url.path,
            cost_ms,
        )
        raise
    finally:
        request_id_context.reset(token)
