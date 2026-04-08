from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import RunRequest

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(limit: int = 50):
    return {"success": True, "data": [run.model_dump() for run in harness_lab_services.runtime.list_runs(limit=limit)]}


@router.post("")
async def create_run(request: RunRequest):
    run = await harness_lab_services.runtime.create_run(request)
    return {"success": True, "data": run.model_dump()}


@router.get("/{run_id}")
async def get_run(run_id: str):
    try:
        run = harness_lab_services.runtime.get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session = harness_lab_services.runtime.get_session(run.session_id)
    active_policy = harness_lab_services.optimizer.get_policy(run.policy_id or session.active_policy_id)
    workflow = (
        harness_lab_services.improvement.get_workflow(run.workflow_template_id or session.workflow_template_id)
        if (run.workflow_template_id or session.workflow_template_id)
        else None
    )
    worker = None
    if run.assigned_worker_id:
        try:
            worker = harness_lab_services.workers.get_worker(run.assigned_worker_id).model_dump()
        except ValueError:
            worker = None
    return {
        "success": True,
        "data": run.model_dump(),
        "session": session.model_dump(),
        "active_policy": active_policy.model_dump(),
        "workflow_template": workflow.model_dump() if workflow else None,
        "worker": worker,
        "events": [event.model_dump() for event in harness_lab_services.runtime.list_events(run_id=run_id)],
        "approvals": [approval.model_dump() for approval in harness_lab_services.database.list_approvals(run_id=run_id)],
        "artifacts": [artifact.model_dump() for artifact in harness_lab_services.database.list_artifacts(run_id=run_id)],
    }


@router.post("/{run_id}/resume")
async def resume_run(run_id: str):
    try:
        run = await harness_lab_services.runtime.resume_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": run.model_dump()}
