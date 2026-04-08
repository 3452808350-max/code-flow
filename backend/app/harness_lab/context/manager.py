from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..storage import HarnessLabDatabase
from ..types import ContextBlock, ContextProfile, IntentDeclaration, ResearchSession
from ..utils import compact_text, new_id, safe_preview, score_overlap, token_estimate, top_items


class ContextManager:
    """Layered context assembler for Harness Lab."""

    def __init__(self, database: HarnessLabDatabase) -> None:
        self.database = database
        self.repo_root = database.repo_root
        self.excluded_prefixes = [
            ".git",
            "frontend/node_modules",
            "frontend/dist",
            "backend/data",
            "__pycache__",
            ".pytest_cache",
        ]

    def assemble(
        self,
        session: ResearchSession,
        profile: ContextProfile,
        intent: Optional[IntentDeclaration] = None,
    ) -> Tuple[List[ContextBlock], Dict[str, Any]]:
        blocks: List[ContextBlock] = []
        selected_goal = session.goal
        now_intent = intent or session.intent_declaration
        structure_content = self._structure_summary()
        blocks.append(
            self._block(
                layer="structure",
                block_type="workspace_map",
                title="Workspace structure",
                source_ref="workspace://root",
                content=structure_content,
                score=1.0,
                selected=True,
                metadata={"kind": "always_on"},
            )
        )
        task_content = f"Goal: {selected_goal}\nContext: {json.dumps(session.context, ensure_ascii=False, indent=2)}"
        if now_intent:
            task_content += f"\nIntent: {now_intent.intent}\nTask type: {now_intent.task_type}\nRisk mode: {now_intent.risk_mode}"
        blocks.append(
            self._block(
                layer="task",
                block_type="goal_bundle",
                title="Active task",
                source_ref="session://goal",
                content=task_content,
                score=1.0,
                selected=True,
                metadata={"kind": "always_on"},
            )
        )
        for history in self._history_blocks(selected_goal, profile.config.get("history_limit", 2)):
            blocks.append(history)
        path_hint = str(session.context.get("path", "") or "")
        index_limit = int(profile.config.get("index_limit", 6))
        for file_block in self._index_blocks(selected_goal, path_hint, index_limit):
            blocks.append(file_block)

        max_tokens = int(profile.config.get("max_tokens", 1400))
        max_blocks = int(profile.config.get("max_blocks", 8))
        token_total = 0
        selected_count = 0
        truncated: List[str] = []
        for block in sorted(blocks, key=self._selection_sort_key):
            must_keep = block.metadata.get("kind") == "always_on"
            if must_keep:
                token_total += block.token_estimate
                selected_count += 1
                continue
            if selected_count >= max_blocks or token_total + block.token_estimate > max_tokens:
                block.selected = False
                truncated.append(block.context_block_id)
                continue
            block.selected = True
            token_total += block.token_estimate
            selected_count += 1
        summary = {
            "selected_count": len([block for block in blocks if block.selected]),
            "total_count": len(blocks),
            "max_tokens": max_tokens,
            "used_tokens": token_total,
            "truncated_blocks": truncated,
        }
        return blocks, summary

    def _block(
        self,
        layer: str,
        block_type: str,
        title: str,
        source_ref: str,
        content: str,
        score: float,
        selected: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextBlock:
        return ContextBlock(
            context_block_id=new_id("ctx"),
            layer=layer,  # type: ignore[arg-type]
            type=block_type,
            title=title,
            source_ref=source_ref,
            content=content,
            score=round(score, 3),
            token_estimate=token_estimate(content),
            selected=selected,
            dependencies=[],
            metadata=metadata or {},
        )

    def _structure_summary(self) -> str:
        top_level = top_items(
            sorted(
                [
                    item.name
                    for item in self.repo_root.iterdir()
                    if not item.name.startswith(".") and item.name not in {"frontend", "backend"} or item.name in {"frontend", "backend", "design"}
                ]
            ),
            14,
        )
        key_paths = [
            "backend/app/main.py",
            "backend/app/harness_lab",
            "frontend/src/App.tsx",
            "frontend/src/lab",
            "design/harness-architecture-design.md",
            ".kiro/specs/graphical-frontend-interface/design.md",
        ]
        return (
            "Top-level workspace entries:\n- "
            + "\n- ".join(top_level)
            + "\nKey paths:\n- "
            + "\n- ".join(key_paths)
        )

    def _history_blocks(self, goal: str, limit: int) -> List[ContextBlock]:
        rows = self.database.fetchall(
            "SELECT payload_json FROM runs ORDER BY updated_at DESC LIMIT ?",
            (max(3, limit * 3),),
        )
        blocks: List[ContextBlock] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            score = score_overlap(goal, json.dumps(payload.get("result", {}), ensure_ascii=False))
            if score <= 0 and len(blocks) >= limit:
                continue
            result_summary = payload.get("result", {}).get("summary", "No result summary recorded")
            blocks.append(
                self._block(
                    layer="history",
                    block_type="recent_run",
                    title=f"Recent run {payload.get('run_id')}",
                    source_ref=f"run://{payload.get('run_id')}",
                    content=compact_text(result_summary, 500),
                    score=max(score, 0.15),
                    selected=False,
                    metadata={"status": payload.get("status")},
                )
            )
            if len(blocks) >= limit:
                break
        return blocks

    def _index_blocks(self, goal: str, path_hint: str, limit: int) -> List[ContextBlock]:
        candidates: List[Tuple[float, Path]] = []
        goal_signal = f"{goal} {path_hint}".strip()
        for path in self._iter_text_files():
            relative = str(path.relative_to(self.repo_root))
            score = score_overlap(goal_signal or relative, relative)
            if path_hint and relative == path_hint:
                score += 1.5
            if score <= 0:
                continue
            candidates.append((score, path))
        candidates.sort(key=lambda item: item[0], reverse=True)
        blocks: List[ContextBlock] = []
        for score, path in candidates[:limit]:
            relative = str(path.relative_to(self.repo_root))
            blocks.append(
                self._block(
                    layer="index",
                    block_type="file_preview",
                    title=relative,
                    source_ref=f"file://{relative}",
                    content=safe_preview(path),
                    score=score,
                    selected=False,
                    metadata={"path": relative},
                )
            )
        return blocks

    def _iter_text_files(self):
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(self.repo_root))
            if any(relative == prefix or relative.startswith(prefix + "/") for prefix in self.excluded_prefixes):
                continue
            if path.stat().st_size > 120_000:
                continue
            yield path

    @staticmethod
    def _selection_sort_key(block: ContextBlock):
        layer_order = {"structure": 0, "task": 1, "history": 2, "index": 3}
        return (layer_order.get(block.layer, 10), -block.score, block.token_estimate)

