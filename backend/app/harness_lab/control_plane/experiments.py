from __future__ import annotations

from fastapi import APIRouter

from ..bootstrap import harness_lab_services
from ..types import ExperimentRequest

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
async def list_experiments():
    return {"success": True, "data": [experiment.model_dump() for experiment in harness_lab_services.optimizer.list_experiments()]}


@router.post("")
async def create_experiment(request: ExperimentRequest):
    experiment = harness_lab_services.optimizer.create_experiment(
        scenario_suite=request.scenario_suite,
        harness_ids=request.harness_ids,
        trace_refs=request.trace_refs,
    )
    return {"success": True, "data": experiment.model_dump()}

