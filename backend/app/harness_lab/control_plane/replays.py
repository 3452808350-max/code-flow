from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services

router = APIRouter(prefix="/api/replays", tags=["replays"])


@router.get("/{replay_id}")
async def get_replay(replay_id: str):
    try:
        replay = harness_lab_services.runtime.get_replay(replay_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": replay}

