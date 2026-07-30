"""
对用户消息做粗分类（knowledge_query / data_query / complex_analysis），
决定后续走 RAG、SQL 还是全链路，并给出执行步骤。
"""
from schemas.planner import PlannerRequest
from services.planner_services import create_plan


async def run_planner(question: str):
    """对用户问题做粗分类并生成执行步骤，返回任务类型与计划列表。"""
    plan = await create_plan(PlannerRequest(question=question))
    return {
        "question": plan.question,
        "task_type": plan.task_type,
        "plan": plan.steps,
    }
