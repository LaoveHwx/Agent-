from functools import lru_cache

from langchain_openai import ChatOpenAI

from utils.env_util import api_key, base_url, model_name


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


@lru_cache
def get_llm() -> ChatOpenAI:
    """惰性创建 ChatOpenAI 单例。

    模块导入时不实例化，避免环境变量未配置时 import 即崩、拖垮 FastAPI 启动。
    配置缺失会在首次调用（运行 agent）时抛 RuntimeError，给出明确提示。
    """
    return ChatOpenAI(
        model=_require(model_name, "MODEL_NAME"),
        api_key=_require(api_key, "API_KEY"),
        base_url=_require(base_url, "BASE_URL"),
        temperature=0.2,
        max_tokens=2048,
    )
