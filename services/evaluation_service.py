"""
评测服务层：在 evaluation_router 与 runner 间做薄封装。

run_evaluation_suite 按请求指定的套件调用 run_evaluation，返回 EvaluationRunResponse。
"""
from evaluation.runner import run_evaluation
from schemas.evaluation import EvaluationRunRequest, EvaluationRunResponse


async def run_evaluation_suite(request: EvaluationRunRequest) -> EvaluationRunResponse:
    """按请求指定的套件运行评测并返回结果。"""
    result = await run_evaluation(request.suites)
    return EvaluationRunResponse(**result)
