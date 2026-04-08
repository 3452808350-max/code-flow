from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import WorkflowCompareRequest

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
async def list_workflows():
    return {"success": True, "data": [workflow.model_dump() for workflow in harness_lab_services.improvement.list_workflows()]}


@router.post("/compare")
async def compare_workflows(request: WorkflowCompareRequest):
    try:
        diff = harness_lab_services.improvement.compare_workflows(request.workflow_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": diff}
