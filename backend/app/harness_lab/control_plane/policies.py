from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import PolicyCompareRequest

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("")
async def list_policies():
    return {"success": True, "data": [policy.model_dump() for policy in harness_lab_services.optimizer.list_policies()]}


@router.post("/compare")
async def compare_policies(request: PolicyCompareRequest):
    try:
        diff = harness_lab_services.optimizer.compare_policies(request.policy_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": diff}


@router.post("/{policy_id}/publish")
async def publish_policy(policy_id: str):
    try:
        policy = harness_lab_services.optimizer.publish_policy(policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": policy.model_dump()}

