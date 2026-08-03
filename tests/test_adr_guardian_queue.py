from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(BIN))
sys.path.insert(0, str(HOOKS))

from adr_guardian_queue import (  # noqa: E402
    build_queue_cache,
    load_queue_actions,
    rank_proposed,
    write_queue_cache,
)
from adr_hook_core import evaluate, parse_payload  # noqa: E402
from test_adr_readiness import _write_adr  # noqa: E402


def _item(
    adr_id: str,
    *,
    linked: bool = False,
    shipped: bool = False,
    ready: bool = False,
    questions: bool = False,
    age: str = "2026-07-20",
    quality: float = 1.0,
) -> dict:
    return {
        "adr_id": adr_id,
        "status": "Proposed",
        "date": age,
        "classification": (
            "ready-for-confirmation"
            if ready
            else ("needs-human-input" if questions else "needs-mechanical-fix")
        ),
        "documents_shipped": shipped,
        "open_questions": ["Deferred: revisit after load test on 2026-08-01"]
        if questions
        else [],
        "quality": {"score": quality},
        "implementation_link": {"linked": linked},
    }


def _report(items: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "evaluated_on": "2026-07-20",
        "adrs": items,
    }


def test_queue_ranking_is_stable_explainable_and_priority_ordered():
    items = [
        _item("ADR-006", quality=0.1, age="2020-01-01"),
        _item("ADR-004", questions=True),
        _item("ADR-003", ready=True),
        _item("ADR-002", shipped=True),
        _item("ADR-001", linked=True),
        _item("ADR-005", quality=0.2, age="2025-01-01"),
    ]
    first = rank_proposed(_report(items))
    second = rank_proposed(_report(list(reversed(items))))

    assert [item["adr_id"] for item in first] == [
        "ADR-001",
        "ADR-002",
        "ADR-003",
        "ADR-004",
        "ADR-006",
        "ADR-005",
    ]
    assert first == second
    assert first[0]["reasons"][0] == "active implementation link"
    assert "open human questions" in first[3]["reasons"]
    assert first[3]["classification"] == "needs-human-input"


def test_cache_is_atomic_disposable_bounded_and_fails_open(tmp_path):
    path = tmp_path / ".adr-kit-readiness.json"
    now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    # Every item carries a signal on purpose. Since TASK-82 a Proposed ADR with
    # nothing attached -- sharp, unlinked, unshipped, asking nothing -- drops out
    # of the queue rather than padding it, so a fixture of quality-1.0 unlinked
    # records would now yield one action and test nothing about the cache.
    payload = build_queue_cache(
        _report([
            _item(f"ADR-{number:03d}", linked=number == 1, quality=0.4)
            for number in range(1, 8)
        ]),
        generated_at=now,
    )
    assert payload["authoritative"] is False
    assert len(payload["actions"]) == 3

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: write_queue_cache(path, payload), range(8)))
    assert len(load_queue_actions(path, now=now + timedelta(hours=1))) == 3

    path.write_text("{partial", encoding="utf-8")
    assert load_queue_actions(path, now=now) == []
    write_queue_cache(path, payload)
    assert load_queue_actions(path, now=now + timedelta(days=2)) == []
    path.unlink()
    assert load_queue_actions(path, now=now) == []


def test_session_start_reads_only_three_prepared_actions_and_fails_open(tmp_path):
    project = tmp_path / "repo"
    adr_dir = project / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    payload = build_queue_cache(
        _report([_item(f"ADR-{number:03d}", linked=True) for number in range(1, 6)]),
        generated_at=datetime.now(timezone.utc),
    )
    write_queue_cache(adr_dir / ".adr-kit-readiness.json", payload)
    envelope = parse_payload(
        json.dumps(
            {"cwd": str(project), "hook_event_name": "SessionStart"}
        ).encode(),
        "codex-cli",
    )
    assert envelope is not None
    context, kind = evaluate(envelope)
    assert kind == "session"
    assert context.count("/adr-kit:grill") == 3

    (adr_dir / ".adr-kit-readiness.json").write_text("{", encoding="utf-8")
    assert evaluate(envelope) == ("", "noop")


def test_guardian_refresh_writes_cache_outside_hook(tmp_path):
    project = tmp_path / "repo"
    adr_dir = project / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(
        adr_dir,
        1,
        open_questions="- [ ] Who owns rollout?",
        verified_in=["src/service.py"],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-guardian"),
            "refresh-readiness",
            "--project-root",
            str(project),
            "--today",
            "2026-07-20",
            "--generated-at",
            "2026-07-20T12:00:00+00:00",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    cache = json.loads(
        (adr_dir / ".adr-kit-readiness.json").read_text(encoding="utf-8")
    )
    assert cache["authoritative"] is False
    assert cache["actions"][0]["command"] == "/adr-kit:grill ADR-001"


@pytest.mark.skipif(
    sys.platform != "win32"
    or not (HOOKS / "bin" / "windows-x64" / "adr-hook.exe").is_file(),
    reason="Windows native hook host",
)
def test_native_session_start_reads_prepared_queue(tmp_path):
    project = tmp_path / "repo"
    adr_dir = project / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    payload = build_queue_cache(
        _report([_item("ADR-001", linked=True)]),
        generated_at=datetime.now(timezone.utc),
    )
    write_queue_cache(adr_dir / ".adr-kit-readiness.json", payload)
    result = subprocess.run(
        [
            str(HOOKS / "bin" / "windows-x64" / "adr-hook.exe"),
            "--client",
            "codex-cli",
            "--event",
            "SessionStart",
        ],
        input=json.dumps({"cwd": str(project)}),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert "/adr-kit:grill ADR-001" in result.stdout
