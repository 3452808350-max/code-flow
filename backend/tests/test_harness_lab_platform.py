from __future__ import annotations

import json
import subprocess
import sys

from fastapi.testclient import TestClient

from backend.app.harness_lab.bootstrap import harness_lab_services
from backend.app.harness_lab.runtime.models import normalize_base_url
from backend.app.harness_lab.types import ModelCallTrace
from backend.app.main import app


client = TestClient(app)


def test_provider_settings_health_and_catalog(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("HARNESS_LAB_MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("HARNESS_LAB_MODEL_NAME", "deepseek-chat")

    assert normalize_base_url("https://api.deepseek.com") == "https://api.deepseek.com/v1"
    assert normalize_base_url("https://api.deepseek.com/v1") == "https://api.deepseek.com/v1"

    health = client.get("/api/health")
    assert health.status_code == 200
    health_data = health.json()["data"]
    assert health_data["model_provider"] == "deepseek"
    assert health_data["model_ready"] is False
    assert health_data["fallback_mode"] is True
    assert health_data["base_url"] == "https://api.deepseek.com/v1"

    catalog = client.get("/api/settings/catalog")
    assert catalog.status_code == 200
    catalog_data = catalog.json()["data"]
    assert catalog_data["model_provider"]["default_model_name"] == "deepseek-chat"
    assert catalog_data["model_provider"]["fallback_mode"] is True
    assert "workflow_templates" in catalog_data
    assert "workers" in catalog_data
    assert any(
        item["provider"] == "deepseek"
        and item["config"]["mode"] == "chat"
        and item["config"]["model_name"] == "deepseek-chat"
        for item in catalog_data["model_profiles"]
    )


def test_model_backed_intent_and_run_trace(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("HARNESS_LAB_MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("HARNESS_LAB_MODEL_NAME", "deepseek-chat")

    def fake_call(settings, messages):
        system_prompt = messages[0]["content"]
        if "intent declaration layer" in system_prompt:
            return (
                {
                    "task_type": "knowledge_search",
                    "intent": "Use repository search before touching files.",
                    "confidence": 0.94,
                    "risk_mode": "low",
                    "suggested_action": "knowledge_search",
                },
                ModelCallTrace(
                    provider=settings.provider,
                    model_name=settings.model_name,
                    latency_ms=12,
                    used_fallback=False,
                    failure_reason=None,
                ),
            )
        return (
            {
                "summary": "Reflection finished through DeepSeek.",
                "research_notes": ["Stay read-first.", "Keep policy verdicts visible."],
                "details": {"path": "runtime"},
            },
            ModelCallTrace(
                provider=settings.provider,
                model_name=settings.model_name,
                latency_ms=15,
                used_fallback=False,
                failure_reason=None,
            ),
        )

    monkeypatch.setattr(harness_lab_services.model_registry, "_call_provider_json", fake_call)

    session_response = client.post(
        "/api/sessions",
        json={
            "goal": "Search the runtime implementation before making changes.",
            "context": {"path": "backend/app/harness_lab/runtime"},
            "execution_mode": "single_worker",
        },
    )
    assert session_response.status_code == 200
    session_payload = session_response.json()["data"]
    assert session_payload["intent_declaration"]["task_type"] == "knowledge_search"
    assert session_payload["intent_declaration"]["suggested_action"]["tool_name"] == "knowledge_search"
    assert session_payload["intent_model_call"]["provider"] == "deepseek"
    assert session_payload["intent_model_call"]["used_fallback"] is False

    run_response = client.post("/api/runs", json={"session_id": session_payload["session_id"]})
    assert run_response.status_code == 200
    run_payload = run_response.json()["data"]
    assert run_payload["execution_trace"]["model_calls"][0]["provider"] == "deepseek"
    assert run_payload["execution_trace"]["model_calls"][0]["used_fallback"] is False
    assert run_payload["execution_trace"]["tool_calls"][0]["tool_name"] == "knowledge_search"


def test_invalid_model_payload_falls_back_without_leaking_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("HARNESS_LAB_MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("HARNESS_LAB_MODEL_NAME", "deepseek-chat")

    def fake_invalid_call(settings, messages):
        return (
            {"task_type": "broken", "intent": "Missing required keys"},
            ModelCallTrace(
                provider=settings.provider,
                model_name=settings.model_name,
                latency_ms=9,
                used_fallback=False,
                failure_reason=None,
            ),
        )

    monkeypatch.setattr(harness_lab_services.model_registry, "_call_provider_json", fake_invalid_call)

    session_response = client.post(
        "/api/sessions",
        json={
            "goal": "Inspect the repository root safely and produce a Harness Lab trace.",
            "context": {"path": "."},
            "execution_mode": "single_worker",
        },
    )
    assert session_response.status_code == 200
    session_payload = session_response.json()["data"]
    assert session_payload["intent_declaration"]["suggested_action"]["tool_name"] == "filesystem"
    assert session_payload["intent_model_call"]["used_fallback"] is True
    assert "invalid intent payload" in session_payload["intent_model_call"]["failure_reason"].lower()
    assert "super-secret-test-key" not in json.dumps(session_payload, ensure_ascii=False)


def test_model_reflection_path_and_shell_approval_flow(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("HARNESS_LAB_MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("HARNESS_LAB_MODEL_NAME", "deepseek-chat")

    def fake_call(settings, messages):
        system_prompt = messages[0]["content"]
        if "intent declaration layer" in system_prompt:
            user_payload = messages[1]["content"]
            if "shell_command" in user_payload:
                return (
                    {
                        "task_type": "shell_command",
                        "intent": "Run the explicit shell command under approval control.",
                        "confidence": 0.96,
                        "risk_mode": "high",
                        "suggested_action": "shell",
                    },
                    ModelCallTrace(
                        provider=settings.provider,
                        model_name=settings.model_name,
                        latency_ms=11,
                        used_fallback=False,
                        failure_reason=None,
                    ),
                )
            return (
                {
                    "task_type": "synthesis",
                    "intent": "Reflect before taking any workspace action.",
                    "confidence": 0.83,
                    "risk_mode": "low",
                    "suggested_action": "model_reflection",
                },
                ModelCallTrace(
                    provider=settings.provider,
                    model_name=settings.model_name,
                    latency_ms=10,
                    used_fallback=False,
                    failure_reason=None,
                ),
            )
        return (
            {
                "summary": "DeepSeek reflection completed.",
                "research_notes": ["Compare harness traces.", "Prefer replayable outputs."],
                "details": {"source": "mock"},
            },
            ModelCallTrace(
                provider=settings.provider,
                model_name=settings.model_name,
                latency_ms=14,
                used_fallback=False,
                failure_reason=None,
            ),
        )

    monkeypatch.setattr(harness_lab_services.model_registry, "_call_provider_json", fake_call)

    reflection_session = client.post(
        "/api/sessions",
        json={
            "goal": "Summarize the harness architecture tradeoffs.",
            "context": {},
            "execution_mode": "single_worker",
        },
    ).json()["data"]
    reflection_run = client.post("/api/runs", json={"session_id": reflection_session["session_id"]})
    assert reflection_run.status_code == 200
    reflection_data = reflection_run.json()["data"]
    assert reflection_data["status"] == "completed"
    assert len(reflection_data["execution_trace"]["model_calls"]) >= 2
    assert reflection_data["execution_trace"]["tool_calls"][0]["output"]["summary"] == "DeepSeek reflection completed."

    shell_session = client.post(
        "/api/sessions",
        json={
            "goal": "Execute a reviewed shell command.",
            "context": {"shell_command": "mkdir -p backend/data/harness_lab/test_probe"},
            "execution_mode": "single_worker",
        },
    ).json()["data"]
    shell_run = client.post("/api/runs", json={"session_id": shell_session["session_id"]})
    assert shell_run.status_code == 200
    shell_run_data = shell_run.json()["data"]
    assert shell_run_data["status"] == "awaiting_approval"
    assert shell_run_data["execution_trace"]["model_calls"][0]["provider"] == "deepseek"
    assert shell_run_data["execution_trace"]["model_calls"][0]["used_fallback"] is False

    approvals = client.get("/api/approvals")
    assert approvals.status_code == 200
    assert any(item["run_id"] == shell_run_data["run_id"] for item in approvals.json()["data"])
    replay = client.get(f"/api/replays/{shell_run_data['run_id']}")
    assert replay.status_code == 200
    replay_body = json.dumps(replay.json()["data"], ensure_ascii=False)
    assert "super-secret-test-key" not in replay_body
    assert "test-key" not in replay_body


def test_policy_compare_and_experiment_registry():
    policies = client.get("/api/policies")
    assert policies.status_code == 200
    policy_ids = [item["policy_id"] for item in policies.json()["data"][:2]]
    assert len(policy_ids) == 2

    compare = client.post("/api/policies/compare", json={"policy_ids": policy_ids})
    assert compare.status_code == 200
    assert "diffs" in compare.json()["data"]

    experiment = client.post(
        "/api/experiments",
        json={"scenario_suite": "golden_trace", "harness_ids": policy_ids, "trace_refs": []},
    )
    assert experiment.status_code == 200
    assert experiment.json()["data"]["scenario_suite"] == "golden_trace"


def test_improvement_plane_workflow_gate_and_worker_registry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("HARNESS_LAB_MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("HARNESS_LAB_MODEL_NAME", "deepseek-chat")

    def fake_call(settings, messages):
        system_prompt = messages[0]["content"]
        user_payload = messages[1]["content"]
        if "intent declaration layer" in system_prompt:
            if "shell_command" in user_payload:
                return (
                    {
                        "task_type": "shell_command",
                        "intent": "Route the shell command through approval-controlled execution.",
                        "confidence": 0.95,
                        "risk_mode": "high",
                        "suggested_action": "shell",
                    },
                    ModelCallTrace(
                        provider=settings.provider,
                        model_name=settings.model_name,
                        latency_ms=8,
                        used_fallback=False,
                        failure_reason=None,
                    ),
                )
            if "summarize" in user_payload.lower():
                return (
                    {
                        "task_type": "synthesis",
                        "intent": "Use model reflection to summarize the architecture.",
                        "confidence": 0.91,
                        "risk_mode": "low",
                        "suggested_action": "model_reflection",
                    },
                    ModelCallTrace(
                        provider=settings.provider,
                        model_name=settings.model_name,
                        latency_ms=7,
                        used_fallback=False,
                        failure_reason=None,
                    ),
                )
            return (
                {
                    "task_type": "knowledge_search",
                    "intent": "Inspect the repository safely before changes.",
                    "confidence": 0.89,
                    "risk_mode": "low",
                    "suggested_action": "knowledge_search",
                },
                ModelCallTrace(
                    provider=settings.provider,
                    model_name=settings.model_name,
                    latency_ms=6,
                    used_fallback=False,
                    failure_reason=None,
                ),
            )
        return (
            {
                "summary": "Benchmark reflection completed.",
                "research_notes": ["Use replay traces.", "Keep worker allocations visible."],
                "details": {"source": "test"},
            },
            ModelCallTrace(
                provider=settings.provider,
                model_name=settings.model_name,
                latency_ms=9,
                used_fallback=False,
                failure_reason=None,
            ),
        )

    monkeypatch.setattr(harness_lab_services.model_registry, "_call_provider_json", fake_call)

    workers = client.get("/api/workers")
    assert workers.status_code == 200
    assert any(item["worker_id"] == "worker_control_plane_local" for item in workers.json()["data"])

    second_worker = client.post(
        "/api/workers",
        json={"label": "parallel-worker", "capabilities": ["filesystem", "knowledge_search", "model_reflection"], "version": "v1"},
    )
    assert second_worker.status_code == 200

    session = client.post(
        "/api/sessions",
        json={
            "goal": "Inspect the repository root safely and produce a Harness Lab trace.",
            "context": {"path": "."},
            "workflow_template_id": "workflow_template_mission_control_v1",
            "execution_mode": "single_worker",
        },
    ).json()["data"]
    run = client.post("/api/runs", json={"session_id": session["session_id"]}).json()["data"]
    run_detail = client.get(f"/api/runs/{run['run_id']}")
    assert run_detail.status_code == 200
    task_started_events = [
        item for item in run_detail.json()["events"] if item["event_type"] == "task.started"
    ]
    task_worker_ids = {item["payload"].get("worker_id") for item in task_started_events if item["payload"].get("worker_id")}
    assert len(task_worker_ids) >= 2

    reflection_session = client.post(
        "/api/sessions",
        json={
            "goal": "Summarize the current architecture and monitoring tradeoffs.",
            "context": {},
            "workflow_template_id": "workflow_template_mission_control_v1",
            "execution_mode": "single_worker",
        },
    ).json()["data"]
    reflection_run = client.post("/api/runs", json={"session_id": reflection_session["session_id"]}).json()["data"]

    approval_session = client.post(
        "/api/sessions",
        json={
            "goal": "Review a shell action under approval control.",
            "context": {"shell_command": "mkdir -p backend/data/harness_lab/benchmark_probe"},
            "workflow_template_id": "workflow_template_mission_control_v1",
            "execution_mode": "single_worker",
        },
    ).json()["data"]
    approval_run = client.post("/api/runs", json={"session_id": approval_session["session_id"]}).json()["data"]
    assert approval_run["status"] == "awaiting_approval"

    trace_refs = [run["run_id"], reflection_run["run_id"], approval_run["run_id"]]

    policy_candidate_response = client.post(
        "/api/improvement/candidates/policy",
        json={"trace_refs": trace_refs},
    )
    assert policy_candidate_response.status_code == 200
    policy_candidate = policy_candidate_response.json()["data"]["candidate"]
    assert policy_candidate["kind"] == "policy"

    replay_eval = client.post(
        "/api/evals/replay",
        json={"candidate_id": policy_candidate["candidate_id"], "trace_refs": trace_refs},
    )
    assert replay_eval.status_code == 200
    replay_eval_data = replay_eval.json()["data"]
    assert replay_eval_data["suite"] == "replay"
    assert replay_eval_data["suite_manifest"]["source"] == "historical_traces"
    replay_eval_detail = client.get(f"/api/evals/{replay_eval_data['evaluation_id']}")
    assert replay_eval_detail.status_code == 200
    assert replay_eval_detail.json()["data"]["evaluation_id"] == replay_eval_data["evaluation_id"]

    gate_before_policy_benchmark = client.get(f"/api/candidates/{policy_candidate['candidate_id']}/gate")
    assert gate_before_policy_benchmark.status_code == 200
    assert gate_before_policy_benchmark.json()["data"]["replay_passed"] is True
    assert gate_before_policy_benchmark.json()["data"]["benchmark_passed"] is False

    publish_policy_too_early = client.post(f"/api/candidates/{policy_candidate['candidate_id']}/publish")
    assert publish_policy_too_early.status_code == 400

    policy_benchmark_eval = client.post(
        "/api/evals/benchmark",
        json={"candidate_id": policy_candidate["candidate_id"], "trace_refs": trace_refs},
    )
    assert policy_benchmark_eval.status_code == 200
    assert policy_benchmark_eval.json()["data"]["suite"] == "benchmark"
    assert len(policy_benchmark_eval.json()["data"]["bucket_results"]) == 5

    published_policy_candidate = client.post(f"/api/candidates/{policy_candidate['candidate_id']}/publish")
    assert published_policy_candidate.status_code == 200
    assert published_policy_candidate.json()["data"]["publish_status"] == "published"

    workflow_candidate_response = client.post(
        "/api/improvement/candidates/workflow",
        json={"trace_refs": trace_refs},
    )
    assert workflow_candidate_response.status_code == 200
    workflow_candidate = workflow_candidate_response.json()["data"]["candidate"]
    assert workflow_candidate["kind"] == "workflow"

    benchmark_eval = client.post(
        "/api/evals/benchmark",
        json={"candidate_id": workflow_candidate["candidate_id"], "trace_refs": trace_refs},
    )
    assert benchmark_eval.status_code == 200
    benchmark_eval_data = benchmark_eval.json()["data"]
    assert benchmark_eval_data["suite"] == "benchmark"
    assert benchmark_eval_data["suite_manifest"]["source"] == "historical_traces"
    assert len(benchmark_eval_data["bucket_results"]) == 5
    assert "safe_read" in [item["bucket"] for item in benchmark_eval_data["bucket_results"]]
    assert isinstance(benchmark_eval_data["coverage_gaps"], list)

    workflow_replay_eval = client.post(
        "/api/evals/replay",
        json={"candidate_id": workflow_candidate["candidate_id"], "trace_refs": trace_refs},
    )
    assert workflow_replay_eval.status_code == 200

    workflow_gate = client.get(f"/api/candidates/{workflow_candidate['candidate_id']}/gate")
    assert workflow_gate.status_code == 200
    assert workflow_gate.json()["data"]["replay_passed"] is True
    assert workflow_gate.json()["data"]["benchmark_passed"] is True
    assert workflow_gate.json()["data"]["approval_required"] is True
    assert workflow_gate.json()["data"]["approval_satisfied"] is False

    publish_without_approval = client.post(f"/api/candidates/{workflow_candidate['candidate_id']}/publish")
    assert publish_without_approval.status_code == 400

    approved_candidate = client.post(f"/api/candidates/{workflow_candidate['candidate_id']}/approve")
    assert approved_candidate.status_code == 200
    assert approved_candidate.json()["data"]["approved"] is True
    assert approved_candidate.json()["data"]["publish_status"] == "publish_ready"

    published_workflow_candidate = client.post(f"/api/candidates/{workflow_candidate['candidate_id']}/publish")
    assert published_workflow_candidate.status_code == 200
    assert published_workflow_candidate.json()["data"]["publish_status"] == "published"

    workflows = client.get("/api/workflows")
    assert workflows.status_code == 200
    workflow_ids = [item["workflow_id"] for item in workflows.json()["data"][:2]]
    assert len(workflow_ids) == 2

    workflow_diff = client.post("/api/workflows/compare", json={"workflow_ids": workflow_ids})
    assert workflow_diff.status_code == 200
    assert "diffs" in workflow_diff.json()["data"]

    candidates = client.get("/api/candidates")
    assert candidates.status_code == 200
    assert len(candidates.json()["data"]) >= 2

    failure_clusters = client.get("/api/failure-clusters")
    assert failure_clusters.status_code == 200
    assert isinstance(failure_clusters.json()["data"], list)


def test_hlab_cli_doctor_and_workers():
    doctor = subprocess.run(
        [sys.executable, "-m", "backend.app.harness_lab.cli", "--output-format", "json", "doctor"],
        check=True,
        capture_output=True,
        text=True,
    )
    doctor_payload = json.loads(doctor.stdout)
    assert "control_plane" in doctor_payload
    assert "provider" in doctor_payload

    workers = subprocess.run(
        [sys.executable, "-m", "backend.app.harness_lab.cli", "--output-format", "json", "workers"],
        check=True,
        capture_output=True,
        text=True,
    )
    workers_payload = json.loads(workers.stdout)
    assert isinstance(workers_payload, list)
    assert any(item["worker_id"] == "worker_control_plane_local" for item in workers_payload)

    failed_promote = subprocess.run(
        [sys.executable, "-m", "backend.app.harness_lab.cli", "--output-format", "json", "promote", "candidate_missing_gate"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert failed_promote.returncode != 0
