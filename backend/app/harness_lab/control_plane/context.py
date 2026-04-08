from __future__ import annotations

from fastapi import APIRouter

from ..bootstrap import harness_lab_services
from ..types import ContextAssembleRequest

router = APIRouter(prefix="/api/context", tags=["context"])


@router.get("/profiles")
async def list_context_profiles():
    return {"success": True, "data": [profile.model_dump() for profile in harness_lab_services.runtime.list_context_profiles()]}


@router.post("/assemble")
async def assemble_context(request: ContextAssembleRequest):
    return {"success": True, "data": harness_lab_services.runtime.assemble_context(request)}

