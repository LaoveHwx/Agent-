"""
LLM 单例：ChatOpenAI 惰性创建，挂载可观测性回调。

get_llm 用 lru_cache 延迟实例化，避免 import 期环境变量未配置就拖垮 FastAPI 启动；
配置缺失在首次调用时抛 RuntimeError，给出明确提示。
LLMObservabilityHandler 自动记录模型输入输出与 Token 消耗，所有调用点共享单例回调。
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from utils.env_util import api_key, api_key2, base_url, base_url2, model_max_tokens, model_name, model_name2
from utils.llm_callback import LLMObservabilityHandler


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


@lru_cache
def get_llm() -> ChatOpenAI:
    """惰性创建 ChatOpenAI 单例。

    模块导入时不实例化，避免环境变量未配置时 import 即崩、拖垮 FastAPI 启动。
    配置缺失会在首次调用（运行 agent）时抛 RuntimeError，给出明确提示。
    callbacks 挂载 LLMObservabilityHandler，统一埋点模型 IO 与 Token 消耗；
    bind_tools / create_agent 复用该单例时回调自动继承。
    """
    return ChatOpenAI(
        model=_require(model_name, "MODEL_NAME"),
        api_key=_require(api_key, "API_KEY"),
        base_url=_require(base_url, "BASE_URL"),
        temperature=0.2,
        max_tokens=int(model_max_tokens),
        callbacks=[LLMObservabilityHandler()],
    )


@lru_cache
def get_llm2() -> ChatOpenAI:
    """惰性创建第二个 ChatOpenAI 单例。

    用于低成本、低温度的前置识别类任务，例如用户问题分类、记忆路由判断。
    与主模型隔离配置，避免识别任务挤占主模型的上下文和限流预算。
    """
    return ChatOpenAI(
        model=_require(model_name2, "MODEL_NAME2"),
        api_key=_require(api_key2, "API_KEY2"),
        base_url=_require(base_url2, "BASE_URL2"),
        temperature=0,
        max_tokens=1024,
        callbacks=[LLMObservabilityHandler()],
    )
