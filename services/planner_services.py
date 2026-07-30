"""
用 LLM 把问题分为 knowledge_query / data_query / complex_analysis，
并给出对应执行步骤（RAG / SQL / 全链路），返回 PlannerResponse。

LLM 不可用或解析失败时回退到关键词粗分类，保证规划节点不硬崩。
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from models.llm import get_llm
from schemas.planner import PlannerRequest, PlannerResponse, TaskType


class TaskClassification(BaseModel):
    """LLM 结构化分类输出契约。"""
    task_type: TaskType

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

# 防御函数
def _steps_for(task_type: str) -> list[str]:
    """返回任务类型对应的执行步骤，未知类型回退到复杂分析。"""
    return _STEPS_BY_TASK_TYPE.get(task_type, _STEPS_BY_TASK_TYPE["complex_analysis"])

_CLASSIFY_SYSTEM = """你是一个企业数据分析系统的任务分类助手，根据用户问题判断任务类型。

任务类型说明：
- knowledge_query：询问业务概念、定义、口径、规则等知识性问题。例如"销售额的口径是什么""客户状态是什么意思""排名规则是怎样的"
- data_query：明确的结构化数据查询/统计/排名。例如"上月各区域销售额排名""订单数最多的客户""本月销售额多少"
- complex_analysis：既需查数据又需结合知识做综合分析，或表述模糊需要拆解的问题。例如"分析最近销售下滑的原因"

判断要点：问"是什么/定义/口径/规则"的归 knowledge_query；要"查/统计/排名/多少"具体数据的归 data_query；需要综合分析的归 complex_analysis。
只返回 knowledge_query / data_query / complex_analysis 三者之一。"""
async def _classify_by_llm(question: str) -> str:
    """用 LLM 做意图分类，返回 task_type。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _CLASSIFY_SYSTEM),
        ("user", "{question}"),
    ])
    chain = prompt | get_llm().with_structured_output(TaskClassification)
    result = await chain.ainvoke({"question": question})
    return result.task_type

# 防御函数
def _classify_by_keywords(question: str) -> str:
    """关键词粗分类，作为 LLM 不可用时的兜底。"""
    if any(k in question for k in ("是什么意思", "定义", "口径", "规则")):
        return "knowledge_query"
    if any(k in question for k in ("查询", "统计", "排名", "最高", "最低", "多少", "销售额", "订单数")):
        return "data_query"
    return "complex_analysis"


async def create_plan(request: PlannerRequest):
    """用 LLM 分类并给出对应执行步骤，LLM 不可用或解析失败时回退关键词粗分类。"""
    question = request.question.strip()

    try:
        task_type = await _classify_by_llm(question)
    except Exception:
        task_type = ""
    # 防御措施
    if task_type not in _VALID_TASK_TYPES:
        task_type = _classify_by_keywords(question)
  # 指定格式
    return PlannerResponse(
        question=question,
        task_type=task_type,
        steps=_steps_for(task_type),
    )
