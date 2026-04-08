from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import ApprovalDecisionRequest

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(status: str = None):
    approvals = harness_lab_services.runtime.list_approvals(status=status)
    return {"success": True, "data": [approval.model_dump() for approval in approvals]}


@router.post("/{approval_id}/decision")
async def resolve_approval(approval_id: str, request: ApprovalDecisionRequest):
    try:
        approval = await harness_lab_services.runtime.resolve_approval(approval_id, request.decision)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": approval.model_dump()}

