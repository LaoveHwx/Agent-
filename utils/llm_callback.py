"""
LLM 可观测性回调：模型输入输出与 Token 消耗埋点。

LLMObservabilityHandler 挂在 get_llm() 单例上，自动捕获所有 LLM 调用：
on_llm_start 记录模型输入，on_llm_end 记录输出与 token 用量并按模型累加，
on_tool_start/end 记录工具调用。供「全链路可观测」与 Token 成本核算。

累加器为类变量、线程安全，get_token_usage 可供观测接口查询。
"""
import threading
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from utils.logger import setup_logger

logger = setup_logger("llm_observability")

# 单条 IO 日志的截断长度，避免大 prompt / 大结果撑爆日志
_LOG_BREVITY_LIMIT = 500


class LLMObservabilityHandler(BaseCallbackHandler):
    """记录 LLM 输入输出、Token 消耗与工具调用，Token 按模型累加。"""

    _lock = threading.Lock()
    _totals: dict[str, dict[str, int]] = {}  # {model: {input, output, total, calls}}

    @classmethod
    def get_token_usage(cls) -> dict[str, dict[str, int]]:
        """返回各模型累计 token 用量快照。"""
        with cls._lock:
            return {model: dict(slot) for model, slot in cls._totals.items()}

    @classmethod
    def reset_token_usage(cls) -> None:
        """清空累计 token 用量（评测/统计周期重置用）。"""
        with cls._lock:
            cls._totals.clear()

    @staticmethod
    def _brevity(text: Any, limit: int = _LOG_BREVITY_LIMIT) -> str:
        """把任意内容归一为单行字符串并截断，控制日志体积。"""
        s = text if isinstance(text, str) else str(text)
        s = s.replace("\n", " ")
        return s if len(s) <= limit else s[:limit] + "...(truncated)"

    @staticmethod
    def _model_name(serialized: dict | None, llm_output: dict | None = None) -> str:
        if llm_output:
            name = llm_output.get("model_name") or llm_output.get("model")
            if name:
                return str(name)
        if serialized:
            name = serialized.get("name") or serialized.get("model")
            if name:
                return str(name)
        return "unknown"

    def _accumulate(self, model: str, input_t: int, output_t: int, total_t: int) -> None:
        with self._lock:
            slot = self._totals.setdefault(
                model, {"input": 0, "output": 0, "total": 0, "calls": 0}
            )
            slot["input"] += input_t
            slot["output"] += output_t
            slot["total"] += total_t
            slot["calls"] += 1

    @staticmethod
    def _extract_usage(response) -> tuple[int, int, int]:
        """从 LLMResult 提取 (input, output, total) token，兼容新旧两版返回结构。"""
        # 1) llm_output.token_usage（OpenAI 旧式 prompt_tokens / completion_tokens）
        llm_output = getattr(response, "llm_output", None) or {}
        token_usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
        if token_usage:
            return (
                int(token_usage.get("prompt_tokens", 0) or 0),
                int(token_usage.get("completion_tokens", 0) or 0),
                int(token_usage.get("total_tokens", 0) or 0),
            )
        # 2) generations[0][0].message.usage_metadata（新版 LangChain input/output_tokens）
        try:
            message = response.generations[0][0].message
            usage_metadata = getattr(message, "usage_metadata", None) or {}
            if usage_metadata:
                return (
                    int(usage_metadata.get("input_tokens", 0) or 0),
                    int(usage_metadata.get("output_tokens", 0) or 0),
                    int(usage_metadata.get("total_tokens", 0) or 0),
                )
        except Exception:
            pass
        return 0, 0, 0

    def on_llm_start(
        self,
        serialized: dict | None,
        prompts: list[str] | None,
        **kwargs: Any,
    ) -> None:
        model = self._model_name(serialized)
        prompt_text = prompts[0] if prompts else ""
        # INFO 只记长度，提示词正文降级 DEBUG（避免刷屏淹没其他日志）。
        # 需要排查提示词时用 DEBUG 级别运行即可看到。
        logger.info("llm_start model=%s prompt_len=%d", model, len(prompt_text))
        logger.debug("llm_start prompt=%s", self._brevity(prompt_text))

    def on_llm_end(self, response, **kwargs: Any) -> None:
        input_t, output_t, total_t = self._extract_usage(response)
        output_text = ""
        try:
            output_text = response.generations[0][0].text or ""
        except Exception:
            pass
        llm_output = getattr(response, "llm_output", None) or {}
        model = self._model_name(None, llm_output)
        self._accumulate(model, input_t, output_t, total_t)
        logger.info(
            "llm_end model=%s input_tokens=%d output_tokens=%d total_tokens=%d output=%s",
            model,
            input_t,
            output_t,
            total_t,
            self._brevity(output_text),
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.exception("llm_error: %s", error)

    def on_tool_start(
        self,
        serialized: dict | None,
        input_str: str,
        **kwargs: Any,
    ) -> None:
        name = (serialized or {}).get("name", "unknown")
        logger.info("tool_start name=%s input=%s", name, self._brevity(input_str))

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        logger.info("tool_end output=%s", self._brevity(output))

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.exception("tool_error: %s", error)
