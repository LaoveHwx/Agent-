import uuid
import json
from collections.abc import AsyncIterator
import asyncio

from graph.center_graph import run_agent_workflow
from memory.redis_memory import append_conversation_message, get_conversation, save_agent_state, save_tool_result
from schemas.agent import AgentAnalyzeRequest, AgentAnalyzeResponse
from utils.logger import setup_logger
logger = setup_logger(__name__) # 做日志


def _safe_get_conversation(session_id: str) -> tuple[list[dict], list[str]]:
    """
    读取指定session_id的历史
    """
    try:
        return get_conversation(session_id), []
    except Exception as exc:
        logger.warning("memory read skipped: %s", exc)
        return [], [f"Memory读取失败: {exc}"]


def _safe_append_message(session_id: str, message: dict) -> list[str]:
    """
    保存消息，失败返回 [错误]
    """
    try:
        append_conversation_message(session_id, message)
        return []
    except Exception as exc:
        logger.warning("memory append skipped: %s", exc)
        return [f"Memory写入失败: {exc}"]


def _safe_save_state(task_id: str, result: dict) -> list[str]:
    """
    存 agent 状态 + tool 结果，失败返回 [错误]
    """
    errors: list[str] = []
    try:
        save_agent_state(task_id, result)
    except Exception as exc:
        logger.warning("memory state save skipped: %s", exc)
        errors.append(f"Agent状态保存失败: {exc}")

    if result.get("sql_result"):
        try:
            save_tool_result(task_id, "sql", result["sql_result"])
        except Exception as exc:
            logger.warning("tool result save skipped: %s", exc)
            errors.append(f"Tool结果保存失败: {exc}")

    return errors


def analyze_question(request: AgentAnalyzeRequest) -> AgentAnalyzeResponse:
    """
     agent 模块的指挥官，
     生成追踪 ID → 读写记忆 → 调工作流 → 汇总错误 → 回写记忆
    """
    session_id = request.session_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    question = request.question.strip()

    history, memory_errors = _safe_get_conversation(session_id)

    memory_errors.extend(_safe_append_message(
        session_id,
        {
            "role": "user",
            "content": question,
            "task_id": task_id,
        },
    ))

    result = run_agent_workflow(question,
                                session_id=session_id,
                                task_id=task_id,
                                history=history
                                )# 问题备份
    result["errors"] = result.get("errors", []) + memory_errors
    result["errors"].extend(_safe_save_state(task_id, result))

    result["errors"].extend(_safe_append_message(
        session_id,
        {
            "role": "assistant",
            "content": result.get("final_answer"),
            "task_id": task_id,
        },
    ))

    return AgentAnalyzeResponse(**result) #解包


async def stream_analyze_question(request: AgentAnalyzeRequest) -> AsyncIterator[str]:
    yield json.dumps({"event": "start"}, ensure_ascii=False) + "\n"
    response = await asyncio.to_thread(analyze_question, request)
    yield json.dumps(
        {
            "event": "metadata",
            "task_id": response.task_id,
            "session_id": response.session_id,
            "task_type": response.task_type,
            "route": response.route,
            "status": response.status,
            "errors": response.errors,
        },
        ensure_ascii=False,
    ) + "\n"

    content = response.final_answer or ""
    chunk_size = 80
    for start in range(0, len(content), chunk_size):
        yield json.dumps({"event": "chunk", "content": content[start:start + chunk_size]}, ensure_ascii=False) + "\n"

    yield json.dumps({"event": "done"}, ensure_ascii=False) + "\n"
