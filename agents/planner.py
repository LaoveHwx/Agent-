from schemas.planner import PlannerRequest
from services.planner_services import create_plan


def run_planner(question: str) -> dict:
    plan = create_plan(PlannerRequest(question=question))
    return {
        "question": plan.question,
        "task_type": plan.task_type,
        "plan": plan.steps,
    }
