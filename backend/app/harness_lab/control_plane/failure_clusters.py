from __future__ import annotations

from fastapi import APIRouter

from ..bootstrap import harness_lab_services

router = APIRouter(prefix="/api/failure-clusters", tags=["failure-clusters"])


@router.get("")
async def list_failure_clusters():
    return {
        "success": True,
        "data": [cluster.model_dump() for cluster in harness_lab_services.improvement.list_failure_clusters()],
    }
