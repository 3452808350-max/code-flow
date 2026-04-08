from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from uuid import uuid4


WORD_PATTERN = re.compile(r"\w+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def compact_text(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def token_estimate(text: str) -> int:
    return max(1, len(WORD_PATTERN.findall(text)))


def score_overlap(left: str, right: str) -> float:
    left_tokens = {token.lower() for token in WORD_PATTERN.findall(left)}
    right_tokens = {token.lower() for token in WORD_PATTERN.findall(right)}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / float(len(left_tokens))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def top_items(items: Iterable[Any], limit: int) -> List[Any]:
    output: List[Any] = []
    for item in items:
        output.append(item)
        if len(output) >= limit:
            break
    return output


def safe_preview(path: Path, limit: int = 1600) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"[binary file] {path.name}"
    return compact_text(content, limit)


def json_dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)

