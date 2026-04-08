from __future__ import annotations

from typing import List, Tuple

from ..types import ConstraintDocument, ContextBlock, IntentDeclaration, PromptFrame, PromptSection, PromptTemplate, ResearchSession
from ..utils import compact_text, new_id, token_estimate, utc_now


class PromptAssembler:
    """Build structured prompt frames from layered context and constraints."""

    def render(
        self,
        session: ResearchSession,
        template: PromptTemplate,
        constraint_document: ConstraintDocument,
        intent: IntentDeclaration,
        blocks: List[ContextBlock],
        truncated_blocks: List[str],
    ) -> PromptFrame:
        selected = [block for block in blocks if block.selected]
        structure = [block for block in selected if block.layer in {"structure", "index"}]
        context = [block for block in selected if block.layer == "task"]
        history = [block for block in selected if block.layer == "history"]
        sections: List[PromptSection] = []
        sections.append(
            self._section(
                "CONSTRAINTS",
                "Constraints",
                compact_text(constraint_document.body, 1200),
                [constraint_document.document_id],
            )
        )
        sections.append(
            self._section(
                "GOAL",
                "Goal",
                f"Goal: {session.goal}\nIntent: {intent.intent}\nRisk mode: {intent.risk_mode}\nAction: {intent.suggested_action.summary}",
                ["session://goal", intent.intent_id],
            )
        )
        sections.append(
            self._section(
                "REFERENCE",
                "Reference",
                "\n\n".join(f"[{block.title}]\n{compact_text(block.content, 700)}" for block in structure) or "No reference blocks selected.",
                [block.source_ref for block in structure],
            )
        )
        sections.append(
            self._section(
                "CONTEXT",
                "Context",
                "\n\n".join(f"[{block.title}]\n{compact_text(block.content, 900)}" for block in context) or "No task blocks selected.",
                [block.source_ref for block in context],
            )
        )
        sections.append(
            self._section(
                "HISTORY",
                "History",
                "\n\n".join(f"[{block.title}]\n{compact_text(block.content, 500)}" for block in history) or "No history blocks selected.",
                [block.source_ref for block in history],
            )
        )
        return PromptFrame(
            prompt_frame_id=new_id("prompt"),
            template_id=template.prompt_template_id,
            sections=sections,
            total_token_estimate=sum(section.token_estimate for section in sections),
            truncated_blocks=truncated_blocks,
            created_at=utc_now(),
        )

    @staticmethod
    def _section(section_key: str, title: str, content: str, source_refs: List[str]) -> PromptSection:
        return PromptSection(
            section_key=section_key,
            title=title,
            content=content,
            token_estimate=token_estimate(content),
            source_refs=source_refs,
        )

