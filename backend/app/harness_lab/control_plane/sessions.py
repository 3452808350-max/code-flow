from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import SessionRequest

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(limit: int = 50):
    return {"success": True, "data": [session.model_dump() for session in harness_lab_services.runtime.list_sessions(limit=limit)]}


@router.post("")
async def create_session(request: SessionRequest):
    session = harness_lab_services.runtime.create_session(request)
    return {"success": True, "data": session.model_dump()}


@router.get("/{session_id}")
async def get_session(session_id: str):
    try:
        session = harness_lab_services.runtime.get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    runs = [run.model_dump() for run in harness_lab_services.runtime.list_runs(limit=100) if run.session_id == session_id]
    events = [event.model_dump() for event in harness_lab_services.runtime.list_events(session_id=session_id)]
    workflow = (
        harness_lab_services.improvement.get_workflow(session.workflow_template_id)
        if session.workflow_template_id
        else None
    )
    active_policy = harness_lab_services.optimizer.get_policy(session.active_policy_id)
    return {
        "success": True,
        "data": session.model_dump(),
        "workflow_template": workflow.model_dump() if workflow else None,
        "active_policy": active_policy.model_dump(),
        "runs": runs,
        "events": events,
    }
