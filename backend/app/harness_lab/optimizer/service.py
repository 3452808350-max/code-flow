from __future__ import annotations

import json
from statistics import mean
from typing import Any, Dict, List

from ..storage import HarnessLabDatabase
from ..types import ExperimentRun, HarnessPolicy, ResearchRun
from ..utils import new_id, utc_now


class OptimizerService:
    """Harness comparison and experiment registry."""

    def __init__(self, database: HarnessLabDatabase) -> None:
        self.database = database

    def list_policies(self) -> List[HarnessPolicy]:
        rows = self.database.fetchall("SELECT payload_json FROM harness_policies ORDER BY updated_at DESC")
        return [HarnessPolicy(**json.loads(row["payload_json"])) for row in rows]

    def get_policy(self, policy_id: str) -> HarnessPolicy:
        row = self.database.fetchone("SELECT payload_json FROM harness_policies WHERE policy_id = ?", (policy_id,))
        if not row:
            raise ValueError("Policy not found")
        return HarnessPolicy(**json.loads(row["payload_json"]))

    def publish_policy(self, policy_id: str) -> HarnessPolicy:
        policy = self.get_policy(policy_id)
        policy.status = "published"
        policy.updated_at = utc_now()
        self._persist_policy(policy)
        return policy

    def compare_policies(self, policy_ids: List[str]) -> Dict[str, Any]:
        policies = [self.get_policy(policy_id) for policy_id in policy_ids[:2]]
        if len(policies) < 2:
            raise ValueError("Two policy IDs are required for comparison")
        left, right = policies
        diffs = []
        for field in [
            "constraint_set_id",
            "context_profile_id",
            "prompt_template_id",
            "model_profile_id",
            "repair_policy",
            "budget_policy",
        ]:
            left_value = getattr(left, field)
            right_value = getattr(right, field)
            if left_value != right_value:
                diffs.append({"field": field, "left": left_value, "right": right_value})
        return {
            "left": left.model_dump(),
            "right": right.model_dump(),
            "diffs": diffs,
        }

    def list_experiments(self) -> List[ExperimentRun]:
        rows = self.database.fetchall("SELECT payload_json FROM experiments ORDER BY updated_at DESC")
        return [ExperimentRun(**json.loads(row["payload_json"])) for row in rows]

    def create_experiment(self, scenario_suite: str, harness_ids: List[str], trace_refs: List[str]) -> ExperimentRun:
        runs = [self._load_run(ref) for ref in trace_refs if self._load_run(ref) is not None]
        metrics = {
            "success_rate": self._success_rate(runs),
            "approval_rate": self._approval_rate(trace_refs),
            "unsafe_action_count": self._unsafe_action_count(runs),
            "repair_rate": self._repair_rate(runs),
            "context_budget_hit_rate": self._context_budget_hit_rate(runs),
            "prompt_size": self._prompt_size(runs),
            "tool_efficiency": self._tool_efficiency(runs),
        }
        winner = harness_ids[0] if harness_ids else None
        now = utc_now()
        experiment = ExperimentRun(
            experiment_id=new_id("exp"),
            scenario_suite=scenario_suite,
            harness_ids=harness_ids,
            status="completed",
            metrics=metrics,
            trace_refs=trace_refs,
            winner=winner,
            created_at=now,
            updated_at=now,
        )
        self.database.upsert_row(
            "experiments",
            {
                "experiment_id": experiment.experiment_id,
                "scenario_suite": experiment.scenario_suite,
                "status": experiment.status,
                "winner": experiment.winner,
                "payload_json": json.dumps(experiment.model_dump(), ensure_ascii=False),
                "created_at": experiment.created_at,
                "updated_at": experiment.updated_at,
            },
            "experiment_id",
        )
        return experiment

    def _persist_policy(self, policy: HarnessPolicy) -> None:
        self.database.upsert_row(
            "harness_policies",
            {
                "policy_id": policy.policy_id,
                "name": policy.name,
                "status": policy.status,
                "constraint_set_id": policy.constraint_set_id,
                "context_profile_id": policy.context_profile_id,
                "prompt_template_id": policy.prompt_template_id,
                "model_profile_id": policy.model_profile_id,
                "payload_json": json.dumps(policy.model_dump(), ensure_ascii=False),
                "created_at": policy.created_at,
                "updated_at": policy.updated_at,
            },
            "policy_id",
        )

    def _load_run(self, run_id: str) -> ResearchRun:
        row = self.database.fetchone("SELECT payload_json FROM runs WHERE run_id = ?", (run_id,))
        if not row:
            return None
        return ResearchRun(**json.loads(row["payload_json"]))

    @staticmethod
    def _success_rate(runs: List[ResearchRun]) -> float:
        if not runs:
            return 0.0
        return round(len([run for run in runs if run.status == "completed"]) / float(len(runs)), 3)

    def _approval_rate(self, trace_refs: List[str]) -> float:
        if not trace_refs:
            return 0.0
        approvals = 0
        for run_id in trace_refs:
            approvals += len(self.database.list_approvals(run_id=run_id))
        return round(approvals / float(len(trace_refs)), 3)

    @staticmethod
    def _unsafe_action_count(runs: List[ResearchRun]) -> int:
        count = 0
        for run in runs:
            trace = run.execution_trace
            if not trace:
                continue
            count += len([verdict for verdict in trace.policy_verdicts if verdict.decision == "deny"])
        return count

    @staticmethod
    def _repair_rate(runs: List[ResearchRun]) -> float:
        if not runs:
            return 0.0
        repaired = 0
        for run in runs:
            trace = run.execution_trace
            if trace and trace.recovery_events:
                repaired += 1
        return round(repaired / float(len(runs)), 3)

    @staticmethod
    def _context_budget_hit_rate(runs: List[ResearchRun]) -> float:
        if not runs:
            return 0.0
        hits = 0
        for run in runs:
            prompt = run.prompt_frame
            if prompt and prompt.truncated_blocks:
                hits += 1
        return round(hits / float(len(runs)), 3)

    @staticmethod
    def _prompt_size(runs: List[ResearchRun]) -> float:
        sizes = [run.prompt_frame.total_token_estimate for run in runs if run.prompt_frame]
        return round(mean(sizes), 3) if sizes else 0.0

    @staticmethod
    def _tool_efficiency(runs: List[ResearchRun]) -> float:
        calls = [len(run.execution_trace.tool_calls) for run in runs if run.execution_trace]
        if not calls:
            return 0.0
        return round(mean([1 / max(1, value) for value in calls]), 3)

