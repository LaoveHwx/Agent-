"""
Agent 服务层：问答分析的指挥官。

analyze_question 生成追踪 ID -> 调工作流 -> 汇总错误 -> 存状态；
stream_analyze_question 以 NDJSON 流式推送 start / status / metadata / chunk / done 事件。
对话历史由 checkpointer 按 thread_id 自动续接，不再手动读写。
"""
import asyncio
import uuid
import json
from collections.abc import AsyncIterator

from graph.center_graph import run_agent_workflow, run_agent_workflow_stream
from memory.redis_memory import save_agent_state, save_session_context, save_tool_result
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
        session_id = result.get("session_id")
        if session_id:
            try:
                save_session_context(
                    session_id,
                    "last_sql",
                    {
                        "task_id": task_id,
                        "question": result.get("question"),
                        "sql": result.get("sql"),
                        "sql_result": result.get("sql_result"),
                        "analysis": result.get("analysis") or result.get("final_answer"),
                    },
                )
            except Exception as exc:
                logger.warning("session SQL context save skipped: %s", exc)
                errors.append(f"会话SQL上下文保存失败: {exc}")
    return errors

# 测试脚本的时候写的
async def analyze_question(request: AgentAnalyzeRequest) -> AgentAnalyzeResponse:
    """
     agent 模块的指挥官：生成追踪 ID -> 调工作流 -> 汇总错误 -> 存状态
     对话历史由 checkpointer 按 thread_id 自动续接，不再手动读写。
     graph 全程走 ainvoke，故本函数为 async。
    """
    session_id = request.session_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    question = request.question.strip()

    result = await run_agent_workflow(question,
                                session_id=session_id,
                                task_id=task_id
                                )# 问题备份

    # messages 是 LangChain Message 对象列表，不进 redis 状态快照、也不进响应
    result.pop("messages", None)

    result["errors"] = result.get("errors", []) + _safe_save_state(task_id, result)

    return AgentAnalyzeResponse(**result) #解包

# 改进为流式回答
async def _legacy_stream_analyze_question(request: AgentAnalyzeRequest) -> AsyncIterator[str]:
    """流式回答：先按节点推送"正在 X"状态，再流式输出最终答案（NDJSON）。

    事件序列：start -> status(多条) -> metadata(含 errors) -> chunk(多条) -> done。
    status 来自 run_agent_workflow_stream 按节点推进；chunk 是最终答案分片。
    """
    session_id = request.session_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    question = request.question.strip()

    yield json.dumps({"event": "start"}, ensure_ascii=False) + "\n"

    final_state: dict = {}
    try:
        async for kind, payload in run_agent_workflow_stream(question, session_id, task_id):
            if kind == "status":
                yield json.dumps({"event": "status", "content": payload}, ensure_ascii=False) + "\n"
            elif kind == "final":
                final_state = payload or {}
    except Exception as exc:
        logger.warning("stream workflow failed: %s", exc)
        final_state = {"errors": [f"工作流执行失败: {exc}"]}
        yield json.dumps({"event": "status", "content": "执行出错，请查看后端日志"}, ensure_ascii=False) + "\n"

    # 收尾：存 agent 状态 + 汇总错误（与 analyze_question 一致）
    final_state.pop("messages", None)
    errors = final_state.get("errors", []) + _safe_save_state(task_id, final_state)

    yield json.dumps(
        {
            "event": "metadata",
            "task_id": task_id,
            "session_id": session_id,
            "task_type": final_state.get("task_type"),
            "route": final_state.get("route"),
            "status": final_state.get("status"),
            "errors": errors,
        },
        ensure_ascii=False,
    ) + "\n"

    content = final_state.get("final_answer") or ""
    chunk_size = 30
    for start in range(0, len(content), chunk_size):
        yield json.dumps({"event": "chunk", "content": content[start:start + chunk_size]}, ensure_ascii=False) + "\n"
        await asyncio.sleep(0)

    yield json.dumps({"event": "done"}, ensure_ascii=False) + "\n"


# Event-based stream implementation. This definition intentionally overrides
# the legacy final-answer slicing version above.
async def stream_analyze_question(request: AgentAnalyzeRequest) -> AsyncIterator[str]:
    """透传 LangGraph 事件流，并输出最终回答 token（NDJSON）。"""
    session_id = request.session_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    question = request.question.strip()

    yield json.dumps(
        {"event": "start", "task_id": task_id, "session_id": session_id},
        ensure_ascii=False,
    ) + "\n"

    final_state: dict = {}
    streamed_answer = False
    try:
        async for kind, payload in run_agent_workflow_stream(question, session_id, task_id):
            if kind == "final":
                final_state = payload or {}
                streamed_answer = bool(final_state.pop("_streamed_answer", False))
                continue

            event_payload = payload if isinstance(payload, dict) else {"content": payload}
            if kind == "chunk":
                streamed_answer = True
            yield json.dumps({"event": kind, **event_payload}, ensure_ascii=False) + "\n"
    except Exception as exc:
        logger.warning("stream workflow failed: %s", exc)
        final_state = {"errors": [f"工作流执行失败: {exc}"]}
        yield json.dumps(
            {"event": "error", "message": "执行出错，请查看后端日志"},
            ensure_ascii=False,
        ) + "\n"

    final_state.pop("messages", None)
    errors = final_state.get("errors", []) + _safe_save_state(task_id, final_state)

    yield json.dumps(
        {
            "event": "metadata",
            "task_id": task_id,
            "session_id": session_id,
            "task_type": final_state.get("task_type"),
            "route": final_state.get("route"),
            "status": final_state.get("status"),
            "errors": errors,
        },
        ensure_ascii=False,
    ) + "\n"

    if not streamed_answer and final_state.get("final_answer"):
        content = final_state["final_answer"]
        for start in range(0, len(content), 80):
            yield json.dumps(
                {"event": "chunk", "node": "final", "content": content[start:start + 80]},
                ensure_ascii=False,
            ) + "\n"
            await asyncio.sleep(0)

    yield json.dumps({"event": "done"}, ensure_ascii=False) + "\n"
