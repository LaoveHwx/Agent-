"""
用 LLM 把问题分为 knowledge_query / data_query / complex_analysis，
并给出对应执行步骤（RAG / SQL / 全链路），返回 PlannerResponse。

LLM 不可用或解析失败时回退到关键词粗分类，保证规划节点不硬崩。
"""
import asyncio

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from models.llm import get_llm, get_llm2
from schemas.planner import MemoryRoute, PlannerRequest, PlannerResponse, TaskType
from utils.prompt_loader import load_prompt


class TaskClassification(BaseModel):
    """LLM 结构化分类输出契约。"""
    task_type: TaskType


class MemoryIntentClassification(BaseModel):
    """用户问题的记忆来源路由输出契约。"""
    memory_route: MemoryRoute = Field(
        description="short_term_redis 表示依赖本轮会话上下文；long_term_vector 表示依赖沉淀到 PG+向量库的知识；hybrid 表示短期和长期都可能需要；none 表示无需记忆。"
    )
    reason: str = Field(default="", description="简短说明为什么选择该记忆来源。")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

# 三个任务分别的步骤提示词
_STEPS_BY_TASK_TYPE: dict[str, list[str]] = {
    "knowledge_query": [
        "识别业务知识问题",
        "检索企业知识库",
        "整理来源并生成回答",
    ],
    "data_query": [
        "识别结构化数据查询问题",
        "读取数据库表结构",
        "生成并执行只读 SQL",
        "整理查询结果",
    ],
    "complex_analysis": [
        "理解用户业务问题",
        "拆解复杂分析任务",
        "准备调用 SQL 和 RAG 工具",
        "汇总分析结论",
    ],
}


_VALID_TASK_TYPES = set(_STEPS_BY_TASK_TYPE)
CLASSIFY_TIMEOUT_SECONDS = 12

_KNOWLEDGE_KEYWORDS = (
    "是什么意思", "定义", "口径", "规则", "制度", "政策", "流程", "说明",
    "文档", "知识库", "数据字典", "怎么规定", "如何规定", "怎么算", "如何计算", "计算公式",
)
_DATA_KEYWORDS = (
    "查询", "统计", "排名", "最高", "最低", "多少", "销售额", "订单数",
    "同比", "环比", "趋势", "明细", "总计", "合计", "平均",
)

# 防御函数
def _steps_for(task_type: str) -> list[str]:
    """返回任务类型对应的执行步骤，未知类型回退到复杂分析。"""
    return _STEPS_BY_TASK_TYPE.get(task_type, _STEPS_BY_TASK_TYPE["complex_analysis"])

_CLASSIFY_SYSTEM = load_prompt("planner")
async def _classify_by_llm(question: str) -> str:
    """用 LLM 做意图分类，返回 task_type。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _CLASSIFY_SYSTEM),
        ("user", "{question}"),
    ])
    chain = prompt | get_llm().with_structured_output(TaskClassification)
    result = await chain.ainvoke({"question": question})
    return result.task_type


_MEMORY_INTENT_SYSTEM = """你是企业 Agent 的记忆调度器，只做路由判断，不回答用户问题。
请判断用户问题最需要哪类记忆来源：
1. short_term_redis：用户使用“刚才、上面、继续、这个结果、上一轮、前面”等表达，依赖当前会话短期上下文或 Redis checkpointer 中的上一轮状态。
2. long_term_vector：用户询问指标口径、业务规则、数据字典、公司制度、历史沉淀知识，应该调用 PostgreSQL + pgvector 的 RAG 知识库。
3. hybrid：用户只说“之前、以前、历史上、过往”等模糊指代，既可能指本会话之前，也可能指沉淀知识或历史规则；或问题同时依赖短期上下文和长期知识。
4. none：问题可以直接通过结构化数据库查询或普通推理完成，不依赖记忆。
不要把“之前”一律判成短期上下文；只有出现“刚才、上一轮、上面这个结果、继续这个”等明确会话指代时，才选 short_term_redis。"""


async def _classify_memory_intent_by_llm(question: str) -> MemoryIntentClassification:
    """用第二模型识别记忆来源路由。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _MEMORY_INTENT_SYSTEM),
        ("user", "{question}"),
    ])
    chain = prompt | get_llm2().with_structured_output(MemoryIntentClassification)
    return await chain.ainvoke({"question": question})

# 防御函数
def _classify_by_keywords(question: str) -> str:
    """关键词粗分类，作为 LLM 不可用时的兜底。"""
    if any(k in question for k in ("是什么意思", "定义", "口径", "规则")):
        return "knowledge_query"
    if any(k in question for k in ("查询", "统计", "排名", "最高", "最低", "多少", "销售额", "订单数")):
        return "data_query"
    return "complex_analysis"


def _classify_confidently(question: str) -> str:
    """只处理意图明确的问题；模糊问题继续交给 LLM 判断。"""
    has_knowledge = any(keyword in question for keyword in _KNOWLEDGE_KEYWORDS)
    has_data = any(keyword in question for keyword in _DATA_KEYWORDS)

    # “环比怎么算”是在问知识口径，不需要真的查询业务数据。
    if any(keyword in question for keyword in ("怎么算", "如何计算", "计算公式")):
        return "knowledge_query"
    if has_knowledge and has_data:
        return "complex_analysis"
    if has_knowledge:
        return "knowledge_query"
    if has_data:
        return "data_query"
    return ""


def _classify_memory_intent_by_keywords(question: str) -> MemoryIntentClassification:
    """记忆路由关键词兜底。"""
    if any(k in question for k in ("刚才", "上面", "上一轮", "前面这个", "这个结果", "这些数据", "继续", "再")):
        return MemoryIntentClassification(
            memory_route="short_term_redis",
            reason="问题包含跨轮指代表达，需要优先读取当前会话短期上下文。",
            confidence=0.7,
        )
    if any(k in question for k in ("之前", "以前", "历史上", "过往", "过去")):
        return MemoryIntentClassification(
            memory_route="hybrid",
            reason="问题包含模糊时间/记忆指代，既可能指短期会话上下文，也可能指长期沉淀知识。",
            confidence=0.6,
        )
    if any(k in question for k in _KNOWLEDGE_KEYWORDS + ("公司", "业务知识")):
        return MemoryIntentClassification(
            memory_route="long_term_vector",
            reason="问题涉及沉淀业务知识，适合检索 PG+向量库知识库。",
            confidence=0.7,
        )
    return MemoryIntentClassification(memory_route="none", reason="未发现明确记忆依赖。", confidence=0.5)


async def create_plan(request: PlannerRequest):
    """用 LLM 分类并给出对应执行步骤，LLM 不可用或解析失败时回退关键词粗分类。"""
    question = request.question.strip()

    task_type = _classify_confidently(question)
    if not task_type:
        try:
            task_type = await asyncio.wait_for(
                _classify_by_llm(question),
                timeout=CLASSIFY_TIMEOUT_SECONDS,
            )
        except Exception:
            task_type = ""

    keyword_memory_intent = _classify_memory_intent_by_keywords(question)
    if keyword_memory_intent.memory_route != "none" or task_type:
        memory_intent = keyword_memory_intent
    else:
        try:
            memory_intent = await asyncio.wait_for(
                _classify_memory_intent_by_llm(question),
                timeout=CLASSIFY_TIMEOUT_SECONDS,
            )
        except Exception:
            memory_intent = keyword_memory_intent

    # 防御措施
    if task_type not in _VALID_TASK_TYPES:
        task_type = _classify_by_keywords(question)
  # 指定格式
    return PlannerResponse(
        question=question,
        task_type=task_type,
        steps=_steps_for(task_type),
        memory_route=memory_intent.memory_route,
        memory_reason=memory_intent.reason,
        memory_confidence=memory_intent.confidence,
    )
