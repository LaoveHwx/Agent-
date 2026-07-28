from evaluation.runner import run_evaluation
from schemas.evaluation import EvaluationRunRequest, EvaluationRunResponse


def run_evaluation_suite(request: EvaluationRunRequest) -> EvaluationRunResponse:
    result = run_evaluation(request.suites)
    return EvaluationRunResponse(**result)
