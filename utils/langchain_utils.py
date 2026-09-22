"""
LangChain 结果解析工具：从 agent 返回的 messages 中抽取内容。

last_ai_content 取最后一条 AIMessage；tool_messages / load_tool_json 按工具名
定位 ToolMessage 并解析 JSON 结果，供各 agent 节点提取结构化产物。
"""
import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage


def last_ai_content(result: dict[str, Any]) -> str:
    """取结果中最后一条 AIMessage 的文本内容。"""
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return str(message.content)
    return ""


def tool_messages(result: dict[str, Any], tool_name: str) -> list[ToolMessage]:
    """按工具名筛选结果中的 ToolMessage 列表。"""
    messages = result.get("messages", [])
    return [
        message
        for message in messages
        if isinstance(message, ToolMessage) and getattr(message, "name", None) == tool_name
    ]


def load_tool_json(result: dict[str, Any], tool_name: str) -> Any | None:
    """取指定工具最后一条 ToolMessage 内容并解析为 JSON，失败返回 None。"""
    messages = tool_messages(result, tool_name)
    if not messages:
        return None

    content = messages[-1].content
    if isinstance(content, list):
        content = "".join(str(item) for item in content)

    try:
        return json.loads(str(content))
    except json.JSONDecodeError:
        return None
