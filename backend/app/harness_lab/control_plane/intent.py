from __future__ import annotations

from fastapi import APIRouter

from ..bootstrap import harness_lab_services
from ..types import IntentRequest

router = APIRouter(prefix="/api/intent", tags=["intent"])


@router.post("/declare")
async def declare_intent(request: IntentRequest):
    intent = harness_lab_services.runtime.declare_intent(request)
    return {"success": True, "data": intent.model_dump()}

