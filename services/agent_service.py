import uuid
import json
from collections.abc import AsyncIterator
import asyncio

from graph.center_graph import run_agent_workflow
from memory.redis_memory import save_agent_state, save_tool_result
from schemas.agent import AgentAnalyzeRequest, AgentAnalyzeResponse
from utils.logger import setup_logger
logger = setup_logger(__name__) # 做日志


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
     agent 模块的指挥官：生成追踪 ID -> 调工作流 -> 汇总错误 -> 存状态
     对话历史由 checkpointer 按 thread_id 自动续接，不再手动读写。
    """
    session_id = request.session_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    question = request.question.strip()

    result = run_agent_workflow(question,
                                session_id=session_id,
                                task_id=task_id
                                )# 问题备份

    # messages 是 LangChain Message 对象列表，不进 redis 状态快照、也不进响应
    result.pop("messages", None)

    result["errors"] = result.get("errors", []) + _safe_save_state(task_id, result)

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
