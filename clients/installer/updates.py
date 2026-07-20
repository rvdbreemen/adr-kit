"""Deferred update-policy state; never imported by hook runtimes."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


def update_decision(values: dict, version: str, *, now: float | None = None, last_check: float | None = None) -> dict:
    update = values["update"]
    current = time.time() if now is None else now
    due = last_check is None or current - last_check >= update["frequency_hours"] * 3600
    pinned = update.get("pinned_version")
    allowed = not update["offline"] and update["policy"] not in {"manual", "notify"}
    if update["policy"] == "pinned":
        allowed = pinned == version
    return {
        "policy": update["policy"],
        "trigger": update["trigger"],
        "frequency_hours": update["frequency_hours"],
        "offline": update["offline"],
        "pinned_version": pinned,
        "due": due,
        "activation_allowed": allowed,
    }


def read_update_state(state_root: Path, client: str) -> dict:
    path = state_root / "updates" / f"{client}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def record_update_state(state_root: Path, client: str, *, version: str, trigger: str) -> Path:
    path = state_root / "updates" / f"{client}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "client": client,
        "version": version,
        "trigger": trigger,
        "last_check_epoch": time.time(),
    }
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path
