"""
Planner Agent：任务分类 + 步骤生成节点。

根据用户问题做粗分类（knowledge_query / data_query / complex_analysis），
决定后续走 RAG、SQL 还是全链路，并给出执行步骤。
"""
from schemas.planner import PlannerRequest
from services.planner_services import create_plan


def run_planner(question: str) -> dict:
    plan = create_plan(PlannerRequest(question=question))
    return {
        "question": plan.question,
        "task_type": plan.task_type,
        "plan": plan.steps,
    }
