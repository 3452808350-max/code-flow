from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..bootstrap import harness_lab_services
from ..types import ConstraintCreateRequest, ConstraintVerifyRequest

router = APIRouter(prefix="/api/constraints", tags=["constraints"])


@router.get("")
async def list_constraints():
    return {"success": True, "data": [document.model_dump() for document in harness_lab_services.constraint_engine.list_documents()]}


@router.post("")
async def create_constraint(request: ConstraintCreateRequest):
    document = harness_lab_services.constraint_engine.create_document(request)
    return {"success": True, "data": document.model_dump()}


@router.post("/{document_id}/publish")
async def publish_constraint(document_id: str):
    try:
        document = harness_lab_services.constraint_engine.publish(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": document.model_dump()}


@router.post("/{document_id}/archive")
async def archive_constraint(document_id: str):
    try:
        document = harness_lab_services.constraint_engine.archive(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": document.model_dump()}


@router.post("/verify")
async def verify_constraint(request: ConstraintVerifyRequest):
    verdicts = harness_lab_services.constraint_engine.verify(request.subject, request.payload, request.constraint_set_id)
    final_verdict = harness_lab_services.constraint_engine.final_verdict(verdicts)
    return {
        "success": True,
        "data": {
            "verdicts": [verdict.model_dump() for verdict in verdicts],
            "final_verdict": final_verdict.model_dump(),
        },
    }

