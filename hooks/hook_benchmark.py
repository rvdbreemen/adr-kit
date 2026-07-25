"""Reproducible end-to-end latency harness for the normalized hook host."""

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

METHOD_ID = "adr-kit-hook-latency-v1"


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile + 0.5)))
    return ordered[index]


def host_command(plugin_root: Path, client: str, event: str) -> tuple[list[str], str]:
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if os.name == "nt":
        native = plugin_root / "hooks" / "bin" / f"windows-{arch}" / "adr-hook.exe"
    elif sys.platform == "darwin":
        native = plugin_root / "hooks" / "bin" / f"darwin-{arch}" / "adr-hook"
    else:
        native = plugin_root / "hooks" / "bin" / f"linux-{arch}" / "adr-hook"
    if native.is_file():
        return [str(native), "--client", client, "--event", event], "native"
    return [
        sys.executable,
        str(plugin_root / "hooks" / "adr-hook.py"),
        "--client",
        client,
        "--event",
        event,
    ], "python-fallback"


def reference_payloads(project_root: Path) -> dict[str, dict[str, Any]]:
    common = {"cwd": str(project_root), "session_id": "benchmark-session"}
    return {
        "SessionStart": {**common, "hook_event_name": "SessionStart"},
        "UserPromptSubmit": {
            **common,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "implement deterministic ADR hook governance",
        },
        "SubagentStart": {
            **common,
            "hook_event_name": "SubagentStart",
            "parent_context": "ADR-001 and ADR-004 govern this task.",
        },
        "PreToolUse": {
            **common,
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "hooks/adr_hook_core.py"},
        },
        "PostToolUse": {
            **common,
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "hooks/adr_hook_core.py"},
        },
        "PreCompact": {**common, "hook_event_name": "PreCompact"},
        "Stop": {**common, "hook_event_name": "Stop"},
    }


def measure(
    plugin_root: Path,
    project_root: Path,
    *,
    samples: int,
    reference_path: Path | None = None,
) -> dict[str, Any]:
    reference_path = reference_path or (
        plugin_root / "tests" / "fixtures" / "hooks" / "reference-corpus.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    payloads = reference_payloads(project_root)
    results = {}
    for event, payload in payloads.items():
        command, host = host_command(plugin_root, "codex-cli", event)
        budget = reference["budgets"][event]
        timeout_seconds = budget["hard_timeout_ms"] / 1000
        warmup = json.dumps(
            {**payload, "agent_id": "benchmark-warmup"},
            ensure_ascii=False,
        ).encode("utf-8")
        try:
            subprocess.run(
                command,
                input=warmup,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            pass
        durations = []
        timeout_count = 0
        for sample in range(samples):
            encoded = json.dumps(
                {**payload, "agent_id": f"benchmark-{sample}"},
                ensure_ascii=False,
            ).encode("utf-8")
            started = time.perf_counter()
            try:
                subprocess.run(
                    command,
                    input=encoded,
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                timeout_count += 1
            durations.append((time.perf_counter() - started) * 1000)
        p50, p95, maximum = (
            statistics.median(durations),
            _percentile(durations, 0.95),
            max(durations),
        )
        results[event] = {
            "host": host,
            "sample_count": samples,
            "p50_ms": round(p50, 3),
            "p95_ms": round(p95, 3),
            "max_ms": round(maximum, 3),
            "timeout_count": timeout_count,
            "budget": budget,
            "targets": {
                "p50": p50 <= budget["p50_ms"],
                "p95": p95 <= budget["p95_ms"],
                "hard_timeout": timeout_count == 0,
            },
        }
    return {
        "schema_version": 1,
        "method_id": METHOD_ID,
        "machine": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "reference_fixture": str(reference_path),
        "process_startup_included": bool(reference["process_startup_included"]),
        "cache_state": "warm-filesystem",
        "ci_variance_percent": reference["ci_variance_percent"],
        "results": results,
        "all_targets_met": all(
            all(item["targets"].values()) for item in results.values()
        ),
    }
