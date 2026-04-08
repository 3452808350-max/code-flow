from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .types import ApprovalRequestModel, ArtifactRef, EventEnvelope
from .utils import ensure_parent, json_dumps, new_id, utc_now


class HarnessLabDatabase:
    """SQLite and filesystem backing store for Harness Lab."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.data_dir = self.repo_root / "backend" / "data" / "harness_lab"
        self.artifact_root = self.data_dir / "artifacts"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else self.data_dir / "harness_lab.db"
        self._initialize()

    @contextmanager
    def connection(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active_policy_id TEXT NOT NULL,
                    constraint_set_id TEXT NOT NULL,
                    context_profile_id TEXT NOT NULL,
                    prompt_template_id TEXT NOT NULL,
                    model_profile_id TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    prompt_frame_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS constraints_documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS context_profiles (
                    context_profile_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS prompt_templates (
                    prompt_template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_profiles (
                    model_profile_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS harness_policies (
                    policy_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    constraint_set_id TEXT NOT NULL,
                    context_profile_id TEXT NOT NULL,
                    prompt_template_id TEXT NOT NULL,
                    model_profile_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    scenario_suite TEXT NOT NULL,
                    status TEXT NOT NULL,
                    winner TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS replays (
                    replay_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    session_id TEXT,
                    run_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    verdict_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    artifact_type TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_templates (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS improvement_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_version_id TEXT NOT NULL,
                    publish_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evaluation_reports (
                    evaluation_id TEXT PRIMARY KEY,
                    candidate_id TEXT,
                    suite TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS failure_clusters (
                    cluster_id TEXT PRIMARY KEY,
                    signature TEXT NOT NULL UNIQUE,
                    frequency INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    state TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
        self._ensure_schema_evolution()

    def _ensure_schema_evolution(self) -> None:
        self._ensure_column("sessions", "workflow_template_id", "TEXT")

    def _ensure_column(self, table: str, column: str, column_type: str) -> None:
        with self.connection() as conn:
            existing_columns = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column in existing_columns:
                return
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def execute(self, query: str, params: tuple = ()) -> None:
        with self.connection() as conn:
            conn.execute(query, params)

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(query, params).fetchone()
        return dict(row) if row is not None else None

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def upsert_row(self, table: str, payload: Dict[str, Any], conflict_field: str) -> None:
        columns = list(payload.keys())
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f"{column}=excluded.{column}" for column in columns if column != conflict_field)
        query = (
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_field}) DO UPDATE SET {updates}"
        )
        self.execute(query, tuple(payload[column] for column in columns))

    def append_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> EventEnvelope:
        model = EventEnvelope(
            seq=0,
            event_id=new_id("event"),
            session_id=session_id,
            run_id=run_id,
            event_type=event_type,
            payload=payload,
            created_at=utc_now(),
        )
        self.execute(
            """
            INSERT INTO events (event_id, session_id, run_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                model.event_id,
                model.session_id,
                model.run_id,
                model.event_type,
                json_dumps(model.payload),
                model.created_at,
            ),
        )
        row = self.fetchone("SELECT * FROM events WHERE event_id = ?", (model.event_id,))
        return EventEnvelope(
            seq=row["seq"],
            event_id=row["event_id"],
            session_id=row["session_id"],
            run_id=row["run_id"],
            event_type=row["event_type"],
            payload=json.loads(row["payload_json"]),
            created_at=row["created_at"],
        )

    def list_events(
        self,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        after_seq: int = 0,
        limit: int = 200,
    ) -> List[EventEnvelope]:
        clauses = ["seq > ?"]
        params: List[Any] = [after_seq]
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        rows = self.fetchall(
            f"SELECT * FROM events WHERE {' AND '.join(clauses)} ORDER BY seq ASC LIMIT ?",
            tuple(params + [limit]),
        )
        return [
            EventEnvelope(
                seq=row["seq"],
                event_id=row["event_id"],
                session_id=row["session_id"],
                run_id=row["run_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def write_artifact_text(
        self,
        run_id: str,
        artifact_type: str,
        filename: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactRef:
        artifact_id = new_id("artifact")
        created_at = utc_now()
        relative_path = Path(run_id) / artifact_type / filename
        absolute_path = self.artifact_root / relative_path
        ensure_parent(absolute_path)
        absolute_path.write_text(content, encoding="utf-8")
        payload = metadata or {}
        self.execute(
            """
            INSERT INTO artifacts (artifact_id, run_id, artifact_type, relative_path, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                run_id,
                artifact_type,
                str(relative_path),
                json_dumps(payload),
                created_at,
            ),
        )
        return ArtifactRef(
            artifact_id=artifact_id,
            run_id=run_id,
            artifact_type=artifact_type,
            relative_path=str(relative_path),
            metadata=payload,
            created_at=created_at,
        )

    def list_artifacts(self, run_id: Optional[str] = None) -> List[ArtifactRef]:
        if run_id:
            rows = self.fetchall("SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at DESC", (run_id,))
        else:
            rows = self.fetchall("SELECT * FROM artifacts ORDER BY created_at DESC")
        return [
            ArtifactRef(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                artifact_type=row["artifact_type"],
                relative_path=row["relative_path"],
                metadata=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_approval(
        self,
        run_id: str,
        verdict_id: str,
        subject: str,
        summary: str,
        payload: Dict[str, Any],
    ) -> ApprovalRequestModel:
        approval = ApprovalRequestModel(
            approval_id=new_id("approval"),
            run_id=run_id,
            verdict_id=verdict_id,
            subject=subject,
            summary=summary,
            payload=payload,
            status="pending",
            decision=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.execute(
            """
            INSERT INTO approvals (
                approval_id, run_id, verdict_id, subject, status, decision, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval.approval_id,
                approval.run_id,
                approval.verdict_id,
                approval.subject,
                approval.status,
                approval.decision,
                json_dumps(approval.model_dump()),
                approval.created_at,
                approval.updated_at,
            ),
        )
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRequestModel:
        row = self.fetchone("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,))
        if not row:
            raise ValueError("Approval not found")
        payload = json.loads(row["payload_json"])
        payload["status"] = row["status"]
        payload["decision"] = row["decision"]
        payload["updated_at"] = row["updated_at"]
        return ApprovalRequestModel(**payload)

    def list_approvals(self, run_id: Optional[str] = None, status: Optional[str] = None) -> List[ApprovalRequestModel]:
        clauses: List[str] = []
        params: List[Any] = []
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetchall(f"SELECT * FROM approvals {where} ORDER BY created_at DESC", tuple(params))
        output: List[ApprovalRequestModel] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["status"] = row["status"]
            payload["decision"] = row["decision"]
            payload["updated_at"] = row["updated_at"]
            output.append(ApprovalRequestModel(**payload))
        return output

    def resolve_approval(self, approval_id: str, decision: str) -> ApprovalRequestModel:
        approval = self.get_approval(approval_id)
        now = utc_now()
        status = "approved" if decision in {"approve", "approve_once"} else "denied"
        approval.status = status
        approval.decision = decision
        approval.updated_at = now
        self.execute(
            "UPDATE approvals SET status = ?, decision = ?, payload_json = ?, updated_at = ? WHERE approval_id = ?",
            (status, decision, json_dumps(approval.model_dump()), now, approval_id),
        )
        return approval

    def upsert_replay(self, replay_id: str, run_id: str, payload: Dict[str, Any]) -> None:
        now = utc_now()
        self.upsert_row(
            "replays",
            {
                "replay_id": replay_id,
                "run_id": run_id,
                "payload_json": json_dumps(payload),
                "created_at": now,
                "updated_at": now,
            },
            "replay_id",
        )

    def get_replay(self, replay_id: str) -> Optional[Dict[str, Any]]:
        row = self.fetchone("SELECT * FROM replays WHERE replay_id = ? OR run_id = ?", (replay_id, replay_id))
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        payload["replay_id"] = row["replay_id"]
        payload["updated_at"] = row["updated_at"]
        return payload
