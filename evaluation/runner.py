import json
import time
from pathlib import Path
from typing import Any

from schemas.agent import AgentAnalyzeRequest
from schemas.rag import RagSearchRequest
from schemas.tool import SqlQueryRequest
from services.agent_service import analyze_question
from services.rag_service import search_rag_documents
from services.tool_service import execute_sql_query


DATASET_DIR = Path(__file__).resolve().parent / "datasets"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _case_result(case: dict[str, Any], passed: bool, elapsed_ms: float, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case.get("id"),
        "passed": passed,
        "elapsed_ms": round(elapsed_ms, 2),
        "detail": detail,
    }


def run_sql_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in _load_jsonl(DATASET_DIR / "sql_cases.jsonl"):
        start = time.perf_counter()
        try:
            response = execute_sql_query(SqlQueryRequest(sql=case["sql"]))
            passed = bool(response.rows) if case.get("expect_non_empty") else True
            detail = {"row_count": response.row_count, "columns": response.columns}
        except Exception as exc:
            passed = False
            detail = {"error": str(exc)}
        results.append(_case_result(case, passed, (time.perf_counter() - start) * 1000, detail))
    return results


def run_rag_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in _load_jsonl(DATASET_DIR / "rag_cases.jsonl"):
        start = time.perf_counter()
        try:
            response = search_rag_documents(
                RagSearchRequest(query=case["query"], top_k=case.get("top_k", 5))
            )
            passed = len(response.results) > 0 if case.get("expect_non_empty") else True
            expected_source = case.get("expected_source")
            if expected_source:
                passed = any(result.source == expected_source for result in response.results)
            detail = {
                "result_count": len(response.results),
                "sources": [result.source for result in response.results],
            }
        except Exception as exc:
            passed = False
            detail = {"error": str(exc)}
        results.append(_case_result(case, passed, (time.perf_counter() - start) * 1000, detail))
    return results


def run_agent_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in _load_jsonl(DATASET_DIR / "agent_cases.jsonl"):
        start = time.perf_counter()
        try:
            response = analyze_question(
                AgentAnalyzeRequest(question=case["question"], session_id=f"eval-{case.get('id')}")
            )
            passed = bool(response.final_answer) if case.get("expect_answer") else True
            expected_task_type = case.get("expected_task_type")
            if expected_task_type:
                passed = passed and response.task_type == expected_task_type
            if not case.get("allow_errors"):
                passed = passed and not response.errors
            detail = {
                "task_id": response.task_id,
                "task_type": response.task_type,
                "route": response.route,
                "has_answer": bool(response.final_answer),
                "error_count": len(response.errors),
            }
        except Exception as exc:
            passed = False
            detail = {"error": str(exc)}
        results.append(_case_result(case, passed, (time.perf_counter() - start) * 1000, detail))
    return results


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    avg_elapsed_ms = sum(result["elapsed_ms"] for result in results) / total if total else 0
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "avg_elapsed_ms": round(avg_elapsed_ms, 2),
    }


def run_evaluation(suites: list[str] | None = None) -> dict[str, Any]:
    selected_suites = suites or ["sql", "rag", "agent"]
    suite_results: dict[str, list[dict[str, Any]]] = {}

    if "sql" in selected_suites:
        suite_results["sql"] = run_sql_cases()
    if "rag" in selected_suites:
        suite_results["rag"] = run_rag_cases()
    if "agent" in selected_suites:
        suite_results["agent"] = run_agent_cases()

    all_results = [result for results in suite_results.values() for result in results]
    return {
        "summary": _summary(all_results),
        "suites": {
            suite: {"summary": _summary(results), "cases": results}
            for suite, results in suite_results.items()
        },
    }
