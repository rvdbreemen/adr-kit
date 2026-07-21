"""Deterministic Proposed-ADR work queue and disposable cache helpers."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence


QUEUE_SCHEMA_VERSION = 1
QUEUE_CACHE_NAME = ".adr-kit-readiness.json"
QUEUE_MAX_ACTIONS = 3
QUEUE_MAX_BYTES = 256 * 1024
QUEUE_TTL_HOURS = 24
_COMMAND_RE = re.compile(r"^/adr-kit:grill ADR-\d{3,4}$")


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _age_days(item: dict, evaluated_on: date) -> int:
    recorded = _parse_date(item.get("date"))
    return max(0, (evaluated_on - recorded).days) if recorded else 0


def rank_proposed(report: dict) -> list[dict]:
    """Rank explainable Proposed work without granting lifecycle authority."""
    evaluated_on = _parse_date(report.get("evaluated_on")) or date.min
    candidates = []
    for item in report.get("adrs", []):
        if not isinstance(item, dict) or item.get("status") != "Proposed":
            continue
        link = item.get("implementation_link", {})
        linked = bool(isinstance(link, dict) and link.get("linked"))
        shipped = bool(item.get("documents_shipped"))
        ready = item.get("classification") == "ready-for-confirmation"
        open_questions = bool(item.get("open_questions"))
        age_days = _age_days(item, evaluated_on)
        quality = item.get("quality", {})
        quality_score = (
            float(quality.get("score", 1.0)) if isinstance(quality, dict) else 1.0
        )
        reasons = []
        if linked:
            reasons.append("active implementation link")
        if shipped:
            reasons.append("shipped but Proposed")
        if ready:
            reasons.append("ready for confirmation")
        if open_questions:
            reasons.append("open human questions")
        reasons.append(f"age {age_days} days")
        reasons.append(f"quality {quality_score:.3f}")
        candidates.append(
            {
                "adr_id": item["adr_id"],
                "classification": item.get("classification"),
                "command": f"/adr-kit:grill {item['adr_id']}",
                "reasons": reasons,
                "_rank": (
                    -int(linked),
                    -int(shipped),
                    -int(ready),
                    -int(open_questions),
                    -age_days,
                    quality_score,
                    str(item["adr_id"]),
                ),
            }
        )
    candidates.sort(key=lambda item: item["_rank"])
    for position, item in enumerate(candidates, 1):
        item["rank"] = position
        item.pop("_rank", None)
    return candidates


def build_queue_cache(
    report: dict,
    *,
    generated_at: datetime,
    ttl_hours: int = QUEUE_TTL_HOURS,
) -> dict:
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    generated_at = generated_at.astimezone(timezone.utc)
    expires_at = generated_at + timedelta(hours=ttl_hours)
    ranked = rank_proposed(report)
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "evaluated_on": report.get("evaluated_on"),
        "source_schema_version": report.get("schema_version"),
        "authoritative": False,
        "actions": ranked[:QUEUE_MAX_ACTIONS],
        "total_proposed": len(ranked),
    }


def write_queue_cache(path: Path, payload: dict) -> None:
    """Atomically replace the derived cache; interruption leaves old bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(encoded) > QUEUE_MAX_BYTES:
        raise ValueError("guardian readiness cache exceeds size limit")
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.005 * (attempt + 1))
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def load_queue_actions(
    path: Path,
    *,
    now: datetime | None = None,
) -> list[dict]:
    """Read at most three safe actions; invalid or stale cache fails open."""
    try:
        if not path.is_file() or path.stat().st_size > QUEUE_MAX_BYTES:
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return []
    try:
        expires_at = datetime.fromisoformat(str(payload["expires_at"]))
    except (KeyError, TypeError, ValueError):
        return []
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if current.astimezone(timezone.utc) >= expires_at.astimezone(timezone.utc):
        return []
    safe = []
    for item in payload.get("actions", []):
        if not isinstance(item, dict):
            continue
        adr_id = str(item.get("adr_id", ""))
        command = str(item.get("command", ""))
        if not re.fullmatch(r"ADR-\d{3,4}", adr_id) or not _COMMAND_RE.fullmatch(
            command
        ):
            continue
        reasons = [
            re.sub(r"[\r\n]+", " ", str(reason))[:160]
            for reason in item.get("reasons", [])
            if str(reason)
        ][:6]
        safe.append(
            {
                "adr_id": adr_id,
                "classification": str(item.get("classification", ""))[:80],
                "command": command,
                "reasons": reasons,
            }
        )
        if len(safe) == QUEUE_MAX_ACTIONS:
            break
    return safe


def render_queue_actions(actions: Sequence[dict]) -> str:
    if not actions:
        return ""
    lines = ["Proposed ADR decision queue (derived, non-authoritative):"]
    for item in actions[:QUEUE_MAX_ACTIONS]:
        reason = ", ".join(item.get("reasons", [])[:2])
        lines.append(f"- {item['adr_id']}: {reason} -> {item['command']}")
    return "\n".join(lines)
