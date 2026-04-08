from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import EvaluationRequest

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.get("")
async def list_evaluations():
    return {"success": True, "data": [item.model_dump() for item in harness_lab_services.improvement.list_evaluations()]}


@router.get("/{evaluation_id}")
async def get_evaluation(evaluation_id: str):
    try:
        report = harness_lab_services.improvement.get_evaluation(evaluation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": report.model_dump()}


@router.post("/replay")
async def create_replay_evaluation(request: EvaluationRequest):
    report = harness_lab_services.improvement.evaluate_candidate(
        suite="replay",
        candidate_id=request.candidate_id,
        trace_refs=request.trace_refs,
        suite_config=request.suite_config,
    )
    return {"success": True, "data": report.model_dump()}


@router.post("/benchmark")
async def create_benchmark_evaluation(request: EvaluationRequest):
    report = harness_lab_services.improvement.evaluate_candidate(
        suite="benchmark",
        candidate_id=request.candidate_id,
        trace_refs=request.trace_refs,
        suite_config=request.suite_config,
    )
    return {"success": True, "data": report.model_dump()}
