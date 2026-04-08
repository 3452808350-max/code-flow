from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import PromptRenderRequest

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("/templates")
async def list_prompt_templates():
    return {"success": True, "data": [template.model_dump() for template in harness_lab_services.runtime.list_prompt_templates()]}


@router.post("/render")
async def render_prompt(request: PromptRenderRequest):
    try:
        prompt = harness_lab_services.runtime.render_prompt(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": prompt.model_dump()}

