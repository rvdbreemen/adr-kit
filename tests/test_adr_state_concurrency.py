"""Cross-process regression tests for shared ADR hook state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GUARDIAN = ROOT / "bin" / "adr-guardian"
WATCH = ROOT / "bin" / "adr-watch"


ADR_WITH_GLOB = """# ADR-001 Repository access

## Status

Accepted, 2026-07-18.

## Context

Repository boundaries need deterministic guidance.

## Decision

Use the repository layer for all matching source files.

## Enforcement

```json
{"forbid_pattern": [{"pattern": "legacy_api\\\\.execute", "path_glob": "src/**/*.py"}]}
```
"""


def _run_parallel(commands, cwd):
    processes = [
        subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        for command in commands
    ]
    results = [process.communicate(timeout=30) for process in processes]
    assert all(process.returncode == 0 for process in processes), results


def test_concurrent_guardian_stamps_preserve_every_trend_entry(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-repository-access.md").write_text(
        ADR_WITH_GLOB, encoding="utf-8"
    )
    commands = [
        [
            sys.executable,
            str(GUARDIAN),
            "stamp",
            "llm",
            "--suggest",
            str(index),
            "--state-dir",
            str(adr_dir),
        ]
        for index in range(8)
    ]

    _run_parallel(commands, tmp_path)

    state = json.loads(
        (adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8")
    )
    assert len(state["trend"]) == 8
    assert all(entry["tier"] == "llm" for entry in state["trend"])
    assert not list(adr_dir.glob(".*.tmp"))


def test_concurrent_watch_updates_preserve_all_unique_cooldowns(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-repository-access.md").write_text(
        ADR_WITH_GLOB, encoding="utf-8"
    )
    commands = [
        [sys.executable, str(WATCH), f"src/area/file-{index}.py"]
        for index in range(8)
    ]

    _run_parallel(commands, tmp_path)

    state = json.loads(
        (adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8")
    )
    keys = state["watch"]["nudges"]
    assert len(keys) == 8
    assert {
        f"ADR-001|src/area/file-{index}.py" for index in range(8)
    } == set(keys)
    assert not list(adr_dir.glob(".*.tmp"))
