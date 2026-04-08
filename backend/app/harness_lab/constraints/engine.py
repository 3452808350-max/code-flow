from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from ..storage import HarnessLabDatabase
from ..types import ConstraintCreateRequest, ConstraintDocument, PolicyVerdict
from ..utils import new_id, utc_now


DESTRUCTIVE_SHELL_PATTERN = re.compile(
    r"(^|\s)(rm|chmod|chown|mkfs|dd|shutdown|reboot|git\s+push|git\s+commit|git\s+reset|sed\s+-i)"
)
MUTATING_SHELL_PATTERN = re.compile(r"(>|>>|\bmv\b|\bcp\b|\btouch\b|\btee\b|\bmkdir\b)")
READ_ONLY_SHELL_PATTERN = re.compile(r"^(pwd|ls|rg|find|cat|git status|git diff|git log|python3? -m compileall)")


class ConstraintEngine:
    """Natural-language constraint registry with heuristic policy enforcement."""

    def __init__(self, database: HarnessLabDatabase) -> None:
        self.database = database

    def list_documents(self, status: Optional[str] = None) -> List[ConstraintDocument]:
        if status:
            rows = self.database.fetchall(
                "SELECT payload_json FROM constraints_documents WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            )
        else:
            rows = self.database.fetchall("SELECT payload_json FROM constraints_documents ORDER BY updated_at DESC")
        return [ConstraintDocument(**json.loads(row["payload_json"])) for row in rows]

    def get_document(self, document_id: str) -> ConstraintDocument:
        row = self.database.fetchone(
            "SELECT payload_json FROM constraints_documents WHERE document_id = ?",
            (document_id,),
        )
        if not row:
            raise ValueError("Constraint document not found")
        return ConstraintDocument(**json.loads(row["payload_json"]))

    def create_document(self, request: ConstraintCreateRequest) -> ConstraintDocument:
        now = utc_now()
        document = ConstraintDocument(
            document_id=new_id("constraint"),
            title=request.title,
            body=request.body,
            scope=request.scope,
            status="candidate",
            tags=request.tags,
            priority=request.priority,
            source=request.source,
            version="v1",
            created_at=now,
            updated_at=now,
        )
        self._persist(document)
        return document

    def publish(self, document_id: str) -> ConstraintDocument:
        document = self.get_document(document_id)
        document.status = "published"
        document.updated_at = utc_now()
        self._persist(document)
        return document

    def archive(self, document_id: str) -> ConstraintDocument:
        document = self.get_document(document_id)
        document.status = "archived"
        document.updated_at = utc_now()
        self._persist(document)
        return document

    def verify(
        self,
        subject: str,
        payload: Dict[str, Any],
        constraint_set_id: Optional[str] = None,
    ) -> List[PolicyVerdict]:
        document = self.get_document(constraint_set_id) if constraint_set_id else self.list_documents(status="published")[0]
        verdicts: List[PolicyVerdict] = []
        tags = {tag.lower() for tag in document.tags}
        command = str(payload.get("command", "") or "")
        if subject == "tool.shell.execute":
            verdicts.append(self._verdict(subject, "approval_required", "Shell commands default to review in Harness Lab.", "tool.shell.*"))
            if command and READ_ONLY_SHELL_PATTERN.search(command):
                verdicts.append(self._verdict(subject, "allow", "Read-only shell commands may run without approval.", "tool.shell.read_only"))
            if command and MUTATING_SHELL_PATTERN.search(command):
                verdicts.append(self._verdict(subject, "approval_required", "Mutable shell operations require operator approval.", "tool.shell.mutable"))
            if command and DESTRUCTIVE_SHELL_PATTERN.search(command):
                verdicts.append(self._verdict(subject, "deny", "Destructive shell patterns are denied by the research guardrails.", "tool.shell.destructive"))
        elif subject == "tool.filesystem.read_file" or subject == "tool.filesystem.list_dir":
            verdicts.append(self._verdict(subject, "allow", "Read-only filesystem access is allowed.", "tool.filesystem.read"))
        elif subject == "tool.filesystem.write_file":
            decision = "deny" if "read-only" in tags else "approval_required"
            reason = "The active constraint set is read-only." if decision == "deny" else "Filesystem writes require review."
            verdicts.append(self._verdict(subject, decision, reason, "tool.filesystem.write"))
        elif subject.startswith("tool.git."):
            action = subject.rsplit(".", 1)[-1]
            if action in {"status", "diff", "log"}:
                verdicts.append(self._verdict(subject, "allow", "Read-only git inspection is allowed.", "tool.git.read"))
            else:
                verdicts.append(self._verdict(subject, "approval_required", "Mutable git actions require review.", "tool.git.mutable"))
        elif subject == "tool.http_fetch.get":
            decision = "approval_required" if "strict-network" in tags else "allow"
            reason = "Network fetches require review in strict-network mode." if decision == "approval_required" else "HTTP GET is allowed."
            verdicts.append(self._verdict(subject, decision, reason, "tool.http_fetch.get"))
        elif subject == "tool.knowledge_search.query":
            verdicts.append(self._verdict(subject, "allow", "Knowledge search is allowed.", "tool.knowledge_search.query"))
        elif subject == "tool.model_reflection.run":
            verdicts.append(self._verdict(subject, "allow", "Local model reflection is allowed.", "tool.model_reflection.run"))
        elif subject.startswith("tool.mcp_proxy"):
            verdicts.append(self._verdict(subject, "approval_required", "External proxy calls require review.", "tool.mcp_proxy.*"))
        else:
            verdicts.append(self._verdict(subject, "deny", "Unknown operations are denied by default.", "default.deny"))
        return verdicts

    def final_verdict(self, verdicts: List[PolicyVerdict]) -> PolicyVerdict:
        precedence = {"deny": 0, "approval_required": 1, "allow": 2}
        return sorted(verdicts, key=lambda verdict: precedence[verdict.decision])[0]

    def _persist(self, document: ConstraintDocument) -> None:
        self.database.upsert_row(
            "constraints_documents",
            {
                "document_id": document.document_id,
                "title": document.title,
                "scope": document.scope,
                "status": document.status,
                "version": document.version,
                "payload_json": json.dumps(document.model_dump(), ensure_ascii=False),
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            },
            "document_id",
        )

    @staticmethod
    def _verdict(subject: str, decision: str, reason: str, matched_rule: str) -> PolicyVerdict:
        return PolicyVerdict(
            verdict_id=new_id("verdict"),
            subject=subject,
            decision=decision,  # type: ignore[arg-type]
            reason=reason,
            matched_rule=matched_rule,
            created_at=utc_now(),
        )

