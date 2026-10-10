"""Append-only audit trail: output/audit_trail.json.

The file is one JSON array. Each agent-loop step adds an entry. Existing entries are never
removed: every write reads the current array, appends, and swaps the file in atomically. If the
file is ever unreadable, it is moved aside (not deleted) and a new array is started.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from config import AUDIT_TRAIL

MAX_TEXT = 2000  # long tool results and replies are clipped so the file stays readable


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def clip(value: Any) -> Any:
    """Shorten long strings (recursively) so one tool result can't bloat the trail."""
    if isinstance(value, str):
        return value if len(value) <= MAX_TEXT else value[:MAX_TEXT] + f"... [{len(value) - MAX_TEXT} more chars]"
    if isinstance(value, dict):
        return {k: clip(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clip(v) for v in value]
    return value


class AuditTrail:
    def __init__(self, path: Path = AUDIT_TRAIL):
        self.path = path
        self._lock = threading.Lock()

    def _read(self) -> list[dict]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        aside = self.path.with_name(f"audit_trail.unreadable-{datetime.now():%Y%m%d-%H%M%S}.json")
        self.path.rename(aside)  # keep it for a human to look at; never wipe history
        return []

    def append(self, *, run_id: str, ticket_id: int, agent: str, depth: int, step: int | None,
               event: str, **detail: Any) -> dict:
        entry = {
            "ts": _now(),
            "run_id": run_id,
            "ticket_id": ticket_id,
            "agent": agent,
            "depth": depth,
            "step": step,
            "event": event,
            **clip(detail),
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            entries = self._read()
            entries.append(entry)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(entries, indent=1, default=str), encoding="utf-8")
            os.replace(tmp, self.path)
        return entry
