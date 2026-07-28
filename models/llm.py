from langchain_openai import ChatOpenAI

from utils.env_util import api_key, base_url, model_name


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


qwen_llm = ChatOpenAI(
    model=_require(model_name, "MODEL_NAME"),
    api_key=_require(api_key, "API_KEY"),
    base_url=_require(base_url, "BASE_URL"),
    temperature=0.2,
    max_tokens=2048,
)
