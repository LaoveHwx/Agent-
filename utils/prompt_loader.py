"""
Prompt loader: read versioned prompt files from the prompts directory.

Prompt files use JSON so the project does not need an extra YAML dependency.
Each file should contain: name, version, description, content.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache
def load_prompt(prompt_name: str) -> str:
    """加载提示词字段，输入对应prompt_name即可返回"""
    path = PROMPT_DIR / f"{prompt_name}.json"
    with path.open("r", encoding="utf-8") as file:
        payload: dict[str, Any] = json.load(file)

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"Prompt file {path} must contain non-empty string field: content")
    return content.strip()


@lru_cache
def load_prompt_metadata(prompt_name: str) -> dict[str, Any]:
    """Load prompt metadata without the content body."""
    path = PROMPT_DIR / f"{prompt_name}.json"
    with path.open("r", encoding="utf-8") as file:
        payload: dict[str, Any] = json.load(file)

    payload.pop("content", None)
    return payload
