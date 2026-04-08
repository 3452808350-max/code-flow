from __future__ import annotations

import json
from typing import List, Optional

from ..storage import HarnessLabDatabase
from ..types import WorkerHeartbeatRequest, WorkerRegisterRequest, WorkerSnapshot
from ..utils import new_id, utc_now


class WorkerService:
    """Single-control-plane worker registry with lightweight lease tracking."""

    def __init__(self, database: HarnessLabDatabase) -> None:
        self.database = database

    def list_workers(self) -> List[WorkerSnapshot]:
        rows = self.database.fetchall("SELECT payload_json FROM workers ORDER BY updated_at DESC")
        return [WorkerSnapshot(**json.loads(row["payload_json"])) for row in rows]

    def get_worker(self, worker_id: str) -> WorkerSnapshot:
        row = self.database.fetchone("SELECT payload_json FROM workers WHERE worker_id = ?", (worker_id,))
        if not row:
            raise ValueError("Worker not found")
        return WorkerSnapshot(**json.loads(row["payload_json"]))

    def register_worker(self, request: WorkerRegisterRequest) -> WorkerSnapshot:
        now = utc_now()
        snapshot = WorkerSnapshot(
            worker_id=request.worker_id or new_id("worker"),
            label=request.label,
            state="idle",
            capabilities=request.capabilities,
            heartbeat_at=now,
            lease_count=0,
            version=request.version,
            current_run_id=None,
            current_task_node_id=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        self._persist_worker(snapshot)
        return snapshot

    def heartbeat(self, worker_id: str, request: WorkerHeartbeatRequest) -> WorkerSnapshot:
        worker = self.get_worker(worker_id)
        worker.state = request.state
        worker.lease_count = request.lease_count
        worker.current_run_id = request.current_run_id
        worker.current_task_node_id = request.current_task_node_id
        worker.last_error = request.last_error
        worker.heartbeat_at = utc_now()
        worker.updated_at = worker.heartbeat_at
        self._persist_worker(worker)
        return worker

    def ensure_default_worker(self) -> WorkerSnapshot:
        row = self.database.fetchone("SELECT payload_json FROM workers WHERE worker_id = ?", ("worker_control_plane_local",))
        if row:
            return WorkerSnapshot(**json.loads(row["payload_json"]))
        return self.register_worker(
            WorkerRegisterRequest(
                worker_id="worker_control_plane_local",
                label="control-plane-local",
                capabilities=["filesystem", "git", "http_fetch", "knowledge_search", "model_reflection", "shell"],
                version="v1",
            )
        )

    def acquire_worker(self, run_id: str, task_node_id: Optional[str] = None) -> WorkerSnapshot:
        workers = self.list_workers()
        if not workers:
            worker = self.ensure_default_worker()
        else:
            worker = next((item for item in workers if item.state in {"idle", "registering"}), workers[0])
        worker.state = "executing"
        worker.current_run_id = run_id
        worker.current_task_node_id = task_node_id
        worker.lease_count += 1
        worker.heartbeat_at = utc_now()
        worker.updated_at = worker.heartbeat_at
        self._persist_worker(worker)
        return worker

    def release_worker(self, worker_id: str, error: Optional[str] = None) -> WorkerSnapshot:
        worker = self.get_worker(worker_id)
        worker.state = "unhealthy" if error else "idle"
        worker.current_run_id = None
        worker.current_task_node_id = None
        worker.last_error = error
        worker.heartbeat_at = utc_now()
        worker.updated_at = worker.heartbeat_at
        self._persist_worker(worker)
        return worker

    def _persist_worker(self, worker: WorkerSnapshot) -> None:
        self.database.upsert_row(
            "workers",
            {
                "worker_id": worker.worker_id,
                "label": worker.label,
                "state": worker.state,
                "heartbeat_at": worker.heartbeat_at,
                "payload_json": json.dumps(worker.model_dump(), ensure_ascii=False),
                "created_at": worker.created_at,
                "updated_at": worker.updated_at,
            },
            "worker_id",
        )
