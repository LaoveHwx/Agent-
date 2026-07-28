import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage


def last_ai_content(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return str(message.content)
    return ""


def tool_messages(result: dict[str, Any], tool_name: str) -> list[ToolMessage]:
    messages = result.get("messages", [])
    return [
        message
        for message in messages
        if isinstance(message, ToolMessage) and getattr(message, "name", None) == tool_name
    ]


def load_tool_json(result: dict[str, Any], tool_name: str) -> Any | None:
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
