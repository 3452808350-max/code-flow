from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple

from openai import OpenAI

from ..types import (
    ActionPlan,
    IntentDeclaration,
    ModelCallTrace,
    ModelProfile,
    ModelProviderSettings,
    ResearchSession,
)
from ..utils import compact_text, new_id, utc_now


URL_PATTERN = re.compile(r"https?://\S+")
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
ALLOWED_SUGGESTED_ACTIONS = {
    "filesystem",
    "git",
    "http_fetch",
    "knowledge_search",
    "model_reflection",
    "shell",
}


def normalize_base_url(raw_url: str) -> str:
    url = (raw_url or "https://api.deepseek.com").strip().rstrip("/")
    if not url:
        url = "https://api.deepseek.com"
    if url.endswith("/v1"):
        return url
    return f"{url}/v1"


class ProviderBackedModelRegistry:
    """DeepSeek-backed intent and reflection registry with heuristic fallback."""

    def __init__(self, client_factory: Optional[Callable[..., OpenAI]] = None) -> None:
        self._client_factory = client_factory or OpenAI

    def get_provider_settings(self, profile: Optional[ModelProfile] = None) -> ModelProviderSettings:
        default_provider = profile.provider if profile else "deepseek"
        default_model_name = "deepseek-chat"
        if profile:
            default_model_name = str(profile.config.get("model_name") or default_model_name)
        provider = str(os.getenv("HARNESS_LAB_MODEL_PROVIDER", default_provider) or default_provider).strip() or "deepseek"
        base_url = normalize_base_url(os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"))
        model_name = str(os.getenv("HARNESS_LAB_MODEL_NAME", default_model_name) or default_model_name).strip() or default_model_name
        api_key_present = bool((os.getenv("OPENAI_API_KEY", "") or "").strip())
        model_ready = provider == "deepseek" and api_key_present
        return ModelProviderSettings(
            provider=provider,
            api_key_present=api_key_present,
            base_url=base_url,
            model_name=model_name,
            model_ready=model_ready,
            fallback_mode=not model_ready,
        )

    def declare_intent(self, session: ResearchSession, profile: ModelProfile) -> IntentDeclaration:
        intent, _ = self.declare_intent_with_trace(session, profile)
        return intent

    def declare_intent_with_trace(
        self,
        session: ResearchSession,
        profile: ModelProfile,
    ) -> Tuple[IntentDeclaration, ModelCallTrace]:
        settings = self.get_provider_settings(profile)
        heuristic_intent = self._heuristic_declare_intent(session, profile)
        if not settings.model_ready:
            return heuristic_intent, self._fallback_trace(settings, "Model provider is not configured.")

        payload, trace = self._call_provider_json(
            settings,
            [
                {
                    "role": "system",
                    "content": (
                        "You are the intent declaration layer for Harness Lab. "
                        "Return a JSON object only with keys: task_type, intent, confidence, risk_mode, suggested_action. "
                        "suggested_action must be one of: filesystem, git, http_fetch, knowledge_search, model_reflection, shell."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "goal": session.goal,
                            "context": session.context,
                            "instructions": [
                                "Prefer read-only inspection when possible.",
                                "Do not invent tools outside the allowed list.",
                                "Keep confidence between 0 and 1.",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        if payload is None:
            return heuristic_intent, trace
        intent = self._intent_from_payload(payload, session, profile)
        if intent is None:
            trace.used_fallback = True
            trace.failure_reason = trace.failure_reason or "Model returned an invalid intent payload."
            return heuristic_intent, trace
        return intent, trace

    def reflect(self, prompt: str, profile: ModelProfile, extra: Optional[Dict[str, Any]] = None) -> Dict[str, object]:
        reflection, _ = self.reflect_with_trace(prompt, profile, extra=extra)
        return reflection

    def reflect_with_trace(
        self,
        prompt: str,
        profile: ModelProfile,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, object], ModelCallTrace]:
        settings = self.get_provider_settings(profile)
        heuristic_reflection = self._heuristic_reflect(prompt, profile, extra, settings)
        if not settings.model_ready:
            return heuristic_reflection, self._fallback_trace(settings, "Model provider is not configured.")

        payload, trace = self._call_provider_json(
            settings,
            [
                {
                    "role": "system",
                    "content": (
                        "You are the research reflection layer for Harness Lab. "
                        "Return a JSON object only with keys: summary, research_notes, details. "
                        "research_notes must be an array of short strings."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "extra": extra or {},
                            "instructions": [
                                "Summarize the prompt faithfully.",
                                "Keep notes concrete and research-oriented.",
                                "Use details as a structured object.",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        if payload is None:
            return heuristic_reflection, trace
        reflection = self._reflection_from_payload(payload, profile, extra, settings)
        if reflection is None:
            trace.used_fallback = True
            trace.failure_reason = trace.failure_reason or "Model returned an invalid reflection payload."
            return heuristic_reflection, trace
        return reflection, trace

    def _call_provider_json(
        self,
        settings: ModelProviderSettings,
        messages: list[dict[str, str]],
    ) -> Tuple[Optional[Dict[str, Any]], ModelCallTrace]:
        started_at = time.perf_counter()
        try:
            client = self._client_factory(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=settings.base_url,
                timeout=20.0,
                max_retries=1,
            )
            response = client.chat.completions.create(
                model=settings.model_name,
                temperature=0,
                messages=messages,
            )
            content = response.choices[0].message.content if response.choices else ""
            if not content:
                raise ValueError("Provider returned an empty response.")
            payload = self._extract_json_object(content)
            return payload, ModelCallTrace(
                provider=settings.provider,
                model_name=settings.model_name,
                latency_ms=max(1, int((time.perf_counter() - started_at) * 1000)),
                used_fallback=False,
                failure_reason=None,
            )
        except Exception as exc:  # noqa: BLE001
            return None, ModelCallTrace(
                provider=settings.provider,
                model_name=settings.model_name,
                latency_ms=max(1, int((time.perf_counter() - started_at) * 1000)),
                used_fallback=True,
                failure_reason=compact_text(str(exc), 240),
            )

    def _extract_json_object(self, content: str) -> Dict[str, Any]:
        candidate = content.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = JSON_OBJECT_PATTERN.search(content)
        if not match:
            raise ValueError("Provider did not return a JSON object.")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("Provider JSON payload was not an object.")
        return parsed

    def _intent_from_payload(
        self,
        payload: Dict[str, Any],
        session: ResearchSession,
        profile: ModelProfile,
    ) -> Optional[IntentDeclaration]:
        task_type = payload.get("task_type")
        intent = payload.get("intent")
        confidence = payload.get("confidence")
        risk_mode = payload.get("risk_mode")
        suggested_action = payload.get("suggested_action")

        if isinstance(suggested_action, dict):
            suggested_action = suggested_action.get("tool_name") or suggested_action.get("name")
        if not all(isinstance(item, str) and item.strip() for item in [task_type, intent, risk_mode]):
            return None
        if not isinstance(suggested_action, str) or suggested_action not in ALLOWED_SUGGESTED_ACTIONS:
            return None
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            return None
        if not 0 <= confidence_value <= 1:
            return None
        action = self._action_for_tool(suggested_action, session)
        if action is None:
            return None
        return IntentDeclaration(
            intent_id=new_id("intent"),
            task_type=task_type.strip(),
            intent=intent.strip(),
            confidence=round(confidence_value, 3),
            risk_mode=risk_mode.strip().lower(),
            suggested_action=action,
            model_profile_id=profile.model_profile_id,
            created_at=utc_now(),
        )

    def _reflection_from_payload(
        self,
        payload: Dict[str, Any],
        profile: ModelProfile,
        extra: Optional[Dict[str, Any]],
        settings: ModelProviderSettings,
    ) -> Optional[Dict[str, object]]:
        summary = payload.get("summary")
        research_notes = payload.get("research_notes")
        details = payload.get("details")
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(research_notes, list) or not all(isinstance(item, str) for item in research_notes):
            return None
        if details is None:
            details = extra or {}
        if not isinstance(details, dict):
            return None
        return {
            "provider": settings.provider,
            "profile": profile.profile,
            "model_name": settings.model_name,
            "summary": summary.strip(),
            "research_notes": research_notes,
            "details": details,
        }

    def _fallback_trace(self, settings: ModelProviderSettings, reason: str) -> ModelCallTrace:
        return ModelCallTrace(
            provider=settings.provider,
            model_name=settings.model_name,
            latency_ms=0,
            used_fallback=True,
            failure_reason=reason,
        )

    def _heuristic_declare_intent(self, session: ResearchSession, profile: ModelProfile) -> IntentDeclaration:
        goal = session.goal.lower()
        context = session.context
        path_hint = str(context.get("path", "") or "")
        shell_command = str(context.get("shell_command", "") or "")
        if shell_command:
            action = self._action_for_tool("shell", session)
            task_type = "shell_command"
            risk_mode = "high"
            intent = "Execute an explicit shell command under policy preflight."
            confidence = 0.92
        elif URL_PATTERN.search(session.goal):
            action = self._action_for_tool("http_fetch", session)
            task_type = "network_read"
            risk_mode = "medium"
            intent = "Retrieve remote content for research analysis."
            confidence = 0.88
        elif any(keyword in goal for keyword in ["read", "open", "inspect", "inspect file", "查看", "打开"]) and path_hint:
            action = self._action_for_tool("filesystem", session)
            task_type = "file_read"
            risk_mode = "low"
            intent = "Inspect a specific workspace file before making decisions."
            confidence = 0.9
        elif any(keyword in goal for keyword in ["list", "files", "目录", "ls", "workspace"]) or not path_hint:
            action = self._action_for_tool("filesystem", session)
            task_type = "workspace_inspection"
            risk_mode = "low"
            intent = "Inspect the workspace structure before deeper work."
            confidence = 0.76
        elif any(keyword in goal for keyword in ["search", "find", "grep", "lookup", "查找"]):
            action = self._action_for_tool("knowledge_search", session)
            task_type = "knowledge_search"
            risk_mode = "low"
            intent = "Search available context rather than mutate the workspace."
            confidence = 0.81
        elif any(keyword in goal for keyword in ["git", "diff", "status", "log"]):
            action = self._action_for_tool("git", session)
            task_type = "repository_state"
            risk_mode = "low"
            intent = "Inspect repository state before taking action."
            confidence = 0.8
        else:
            action = self._action_for_tool("model_reflection", session)
            task_type = "synthesis"
            risk_mode = "low"
            intent = "Synthesize the request into a research-oriented next step."
            confidence = 0.68
        return IntentDeclaration(
            intent_id=new_id("intent"),
            task_type=task_type,
            intent=intent,
            confidence=confidence,
            risk_mode=risk_mode,
            suggested_action=action or ActionPlan(
                tool_name="model_reflection",
                subject="tool.model_reflection.run",
                payload={"prompt": session.goal, "context": session.context},
                summary="Produce a structured research reflection without touching the workspace.",
            ),
            model_profile_id=profile.model_profile_id,
            created_at=utc_now(),
        )

    def _heuristic_reflect(
        self,
        prompt: str,
        profile: ModelProfile,
        extra: Optional[Dict[str, Any]],
        settings: ModelProviderSettings,
    ) -> Dict[str, object]:
        details = dict(extra or {})
        details.setdefault("fallback_mode", True)
        return {
            "provider": settings.provider,
            "profile": profile.profile,
            "model_name": settings.model_name,
            "summary": prompt[:200],
            "research_notes": [
                "Prefer layered context over prompt stuffing.",
                "Make policy verdicts visible before execution.",
                "Keep replays rich enough for harness comparison.",
            ],
            "details": details,
        }

    def _action_for_tool(self, tool_name: str, session: ResearchSession) -> Optional[ActionPlan]:
        path_hint = str(session.context.get("path", "") or "")
        shell_command = str(session.context.get("shell_command", "") or "")
        goal = session.goal.lower()

        if tool_name == "shell":
            if not shell_command:
                return None
            return ActionPlan(
                tool_name="shell",
                subject="tool.shell.execute",
                payload={"command": shell_command},
                summary="Execute the supplied shell command inside the workspace.",
            )
        if tool_name == "http_fetch":
            url_match = URL_PATTERN.search(session.goal) or URL_PATTERN.search(str(session.context.get("url", "") or ""))
            if not url_match:
                return None
            return ActionPlan(
                tool_name="http_fetch",
                subject="tool.http_fetch.get",
                payload={"url": url_match.group(0)},
                summary="Fetch the referenced remote document for inspection.",
            )
        if tool_name == "filesystem":
            if any(keyword in goal for keyword in ["read", "open", "inspect file", "查看", "打开"]) and path_hint:
                return ActionPlan(
                    tool_name="filesystem",
                    subject="tool.filesystem.read_file",
                    payload={"action": "read_file", "path": path_hint},
                    summary="Read the targeted file from the workspace.",
                )
            return ActionPlan(
                tool_name="filesystem",
                subject="tool.filesystem.list_dir",
                payload={"action": "list_dir", "path": path_hint or "."},
                summary="List workspace paths to build a local mental model.",
            )
        if tool_name == "knowledge_search":
            return ActionPlan(
                tool_name="knowledge_search",
                subject="tool.knowledge_search.query",
                payload={"query": session.goal},
                summary="Search research traces and repository content for relevant context.",
            )
        if tool_name == "git":
            git_action = "status"
            if "diff" in goal:
                git_action = "diff"
            elif "log" in goal:
                git_action = "log"
            return ActionPlan(
                tool_name="git",
                subject=f"tool.git.{git_action}",
                payload={"action": git_action},
                summary="Inspect git state to understand current workspace drift.",
            )
        if tool_name == "model_reflection":
            return ActionPlan(
                tool_name="model_reflection",
                subject="tool.model_reflection.run",
                payload={"prompt": session.goal, "context": session.context},
                summary="Produce a structured research reflection without touching the workspace.",
            )
        return None


ModelRegistry = ProviderBackedModelRegistry
