from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import WorkerHeartbeatRequest, WorkerRegisterRequest

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.get("")
async def list_workers():
    return {"success": True, "data": [worker.model_dump() for worker in harness_lab_services.workers.list_workers()]}


@router.post("")
async def register_worker(request: WorkerRegisterRequest):
    worker = harness_lab_services.workers.register_worker(request)
    return {"success": True, "data": worker.model_dump()}


@router.post("/{worker_id}/heartbeat")
async def heartbeat(worker_id: str, request: WorkerHeartbeatRequest):
    try:
        worker = harness_lab_services.workers.heartbeat(worker_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": worker.model_dump()}
