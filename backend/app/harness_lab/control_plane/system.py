from __future__ import annotations

from fastapi import APIRouter

from ..bootstrap import harness_lab_services

router = APIRouter(tags=["system"])


@router.get("/api/settings/catalog")
async def settings_catalog():
    provider_settings = harness_lab_services.runtime.get_model_provider_settings()
    return {
        "success": True,
        "data": {
            "constraints": [item.model_dump() for item in harness_lab_services.constraint_engine.list_documents()],
            "context_profiles": [item.model_dump() for item in harness_lab_services.runtime.list_context_profiles()],
            "prompt_templates": [item.model_dump() for item in harness_lab_services.runtime.list_prompt_templates()],
            "model_profiles": [item.model_dump() for item in harness_lab_services.runtime.list_model_profiles()],
            "workflow_templates": [item.model_dump() for item in harness_lab_services.improvement.list_workflows()],
            "workers": [item.model_dump() for item in harness_lab_services.workers.list_workers()],
            "tools": [item.model_dump(by_alias=True) for item in harness_lab_services.tool_gateway.list_tools()],
            "model_provider": {
                "provider": provider_settings.provider,
                "base_url": provider_settings.base_url,
                "model_ready": provider_settings.model_ready,
                "fallback_mode": provider_settings.fallback_mode,
                "default_model_name": provider_settings.model_name,
            },
        },
    }


@router.get("/api/health")
async def health():
    doctor = harness_lab_services.doctor_report()
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "mode": "multi_agent_platform",
            "sessions": doctor["control_plane"]["sessions"],
            "runs": doctor["control_plane"]["runs"],
            "policies": doctor["control_plane"]["policies"],
            "workflows": doctor["control_plane"]["workflows"],
            "workers": doctor["workers"]["count"],
            "doctor_ready": doctor["doctor_ready"],
            "warnings": doctor["warnings"],
            "model_provider": doctor["provider"]["provider"],
            "model_ready": doctor["provider"]["model_ready"],
            "fallback_mode": doctor["provider"]["fallback_mode"],
            "model_profile": doctor["provider"]["model_name"],
            "base_url": doctor["provider"]["base_url"],
        },
    }
