from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from memory.redis_client import get_redis_client


USER_MEMORY_PREFIX = "data_agent:long_memory:user"
COMPANY_MEMORY_KEY = "data_agent:long_memory:company"


def _user_id_from_config(config: RunnableConfig) -> str:
    configurable = config.get("configurable", {}) if config else {}
    return configurable.get("user_id") or configurable.get("thread_id") or "anonymous"


@tool
def save_user_memory_tool(
    category: Annotated[str, "用户记忆类别，例如 name、region、metric、preference"],
    content: Annotated[str, "需要保存的用户事实或偏好内容"],
    config: RunnableConfig,
) -> str:
    """保存用户个性化长期记忆。"""
    user_id = _user_id_from_config(config)
    key = f"{USER_MEMORY_PREFIX}:{user_id}"
    client = get_redis_client()
    client.hset(key, category, content)
    return f"已保存用户长期记忆：{category}={content}"


@tool
def get_user_memory_tool(
    query: Annotated[str, "用于检索用户长期记忆的问题或关键词"],
    config: RunnableConfig,
) -> str:
    """读取当前用户的长期记忆，用于个性化回答。"""
    user_id = _user_id_from_config(config)
    key = f"{USER_MEMORY_PREFIX}:{user_id}"
    client = get_redis_client()
    memories = client.hgetall(key)
    if not memories:
        return "没有找到该用户的长期记忆。"
    return "\n".join(f"- {category}: {content}" for category, content in memories.items())


@tool
def save_company_memory_tool(
    category: Annotated[str, "公司记忆类别，例如 metric_rule、business_rule、table_dictionary"],
    content: Annotated[str, "需要保存的公司情况、指标口径或业务规则"],
) -> str:
    """保存公司级长期记忆。"""
    client = get_redis_client()
    client.hset(COMPANY_MEMORY_KEY, category, content)
    return f"已保存公司长期记忆：{category}"


@tool
def get_company_memory_tool(
    query: Annotated[str, "用于检索公司情况、指标口径或业务规则的问题"],
) -> str:
    """读取公司级长期记忆，用于回答企业业务问题。"""
    client = get_redis_client()
    memories = client.hgetall(COMPANY_MEMORY_KEY)
    if not memories:
        return "没有找到公司长期记忆。"
    return "\n".join(f"- {category}: {content}" for category, content in memories.items())


MEMORY_TOOLS = [
    save_user_memory_tool,
    get_user_memory_tool,
    save_company_memory_tool,
    get_company_memory_tool,
]
