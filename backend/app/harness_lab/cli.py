from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from backend.app.harness_lab.bootstrap import harness_lab_services  # noqa: E402
from backend.app.harness_lab.types import RunRequest, SessionRequest, WorkerRegisterRequest  # noqa: E402


def _emit(payload: Any, output_format: str = "text") -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
        return
    if isinstance(payload, list):
        for item in payload:
            print(item)
        return
    print(payload)


def _latest_run_id() -> str | None:
    runs = harness_lab_services.runtime.list_runs(limit=1)
    return runs[0].run_id if runs else None


def _latest_session_id() -> str | None:
    sessions = harness_lab_services.runtime.list_sessions(limit=1)
    return sessions[0].session_id if sessions else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hlab", description="Harness Lab CLI control surface")
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit = subparsers.add_parser("submit", help="Create a session and execute a run")
    submit.add_argument("goal")
    submit.add_argument("--path", dest="path_hint", default="")
    submit.add_argument("--shell", dest="shell_command", default="")
    submit.add_argument("--execution-mode", default="single_worker")

    subparsers.add_parser("doctor", help="Run local control-plane diagnostics")

    attach = subparsers.add_parser("attach", help="Inspect the latest or requested run")
    attach.add_argument("--run-id", default="")

    eval_cmd = subparsers.add_parser("eval", help="Run offline replay or benchmark evaluation")
    eval_cmd.add_argument("--suite", choices=["replay", "benchmark"], default="replay")
    eval_cmd.add_argument("--candidate-id", default="")
    eval_cmd.add_argument("--trace-ref", action="append", default=[])

    subparsers.add_parser("candidates", help="List improvement candidates")

    promote = subparsers.add_parser("promote", help="Publish a candidate")
    promote.add_argument("candidate_id")

    rollback = subparsers.add_parser("rollback", help="Rollback a candidate")
    rollback.add_argument("candidate_id")

    subparsers.add_parser("approvals", help="List approval inbox")

    workers = subparsers.add_parser("workers", help="List or register workers")
    workers.add_argument("--register", action="store_true")
    workers.add_argument("--label", default="cli-worker")
    workers.add_argument("--capability", action="append", default=[])

    subparsers.add_parser("serve", help="Start the FastAPI control plane")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "doctor":
        _emit(harness_lab_services.doctor_report(), args.output_format)
        return

    if args.command == "submit":
        context: dict[str, Any] = {}
        if args.path_hint:
            context["path"] = args.path_hint
        if args.shell_command:
            context["shell_command"] = args.shell_command
        session = harness_lab_services.runtime.create_session(
            SessionRequest(
                goal=args.goal,
                context=context,
                execution_mode=args.execution_mode,
            )
        )
        run = asyncio.run(harness_lab_services.runtime.create_run(RunRequest(session_id=session.session_id)))
        _emit(
            {
                "session_id": session.session_id,
                "run_id": run.run_id,
                "status": run.status,
                "policy_id": run.policy_id,
                "workflow_template_id": run.workflow_template_id,
                "assigned_worker_id": run.assigned_worker_id,
            },
            args.output_format,
        )
        return

    if args.command == "attach":
        run_id = args.run_id or _latest_run_id()
        if not run_id:
            raise SystemExit("No run is available to attach to.")
        run = harness_lab_services.runtime.get_run(run_id)
        _emit(run.model_dump(), args.output_format)
        return

    if args.command == "eval":
        latest_run_id = _latest_run_id()
        trace_refs = args.trace_ref or ([] if args.candidate_id else [latest_run_id] if latest_run_id else [])
        report = harness_lab_services.improvement.evaluate_candidate(
            suite=args.suite,
            candidate_id=args.candidate_id or None,
            trace_refs=trace_refs,
        )
        _emit(report.model_dump(), args.output_format)
        return

    if args.command == "candidates":
        _emit([item.model_dump() for item in harness_lab_services.improvement.list_candidates()], args.output_format)
        return

    if args.command == "promote":
        try:
            candidate = harness_lab_services.improvement.publish_candidate(args.candidate_id)
        except ValueError as exc:
            try:
                gate = harness_lab_services.improvement.get_candidate_gate(args.candidate_id)
                payload = {"error": str(exc), "gate": gate.model_dump()}
            except ValueError:
                payload = {"error": str(exc)}
            _emit(payload, args.output_format)
            raise SystemExit(1) from exc
        _emit(candidate.model_dump(), args.output_format)
        return

    if args.command == "rollback":
        candidate = harness_lab_services.improvement.rollback_candidate(args.candidate_id)
        _emit(candidate.model_dump(), args.output_format)
        return

    if args.command == "approvals":
        _emit([item.model_dump() for item in harness_lab_services.runtime.list_approvals()], args.output_format)
        return

    if args.command == "workers":
        if args.register:
            worker = harness_lab_services.workers.register_worker(
                WorkerRegisterRequest(label=args.label, capabilities=args.capability, version="v1")
            )
            _emit(worker.model_dump(), args.output_format)
            return
        _emit([item.model_dump() for item in harness_lab_services.workers.list_workers()], args.output_format)
        return

    if args.command == "serve":
        from backend.app.main import main as serve_main

        serve_main()
        return


if __name__ == "__main__":
    main()
