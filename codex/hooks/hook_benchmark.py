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
    # Follow the dispatcher, not the filesystem. run-hook.cmd stopped preferring
    # the native host in v0.44.1 -- it runs only under ADR_KIT_NATIVE_HOOK=1,
    # because measured against the Python oracle it returned one of four
    # governing ADRs before an edit. A benchmark that still picks it up whenever
    # the file exists reports latency for a path that no longer ships, which is
    # the most misleading number this file could produce.
    if native.is_file() and os.environ.get("ADR_KIT_NATIVE_HOOK") == "1":
        return [str(native), "--client", client, "--event", event], "native"
    return [
        sys.executable,
        str(plugin_root / "hooks" / "adr-hook.py"),
        "--client",
        client,
        "--event",
        event,
    ], "python-fallback"


# Measured start cost of a bare CPython process -- `python -c pass`, p50 over 7
# samples, Windows 11 / CPython 3.12.9, 2026-08-05. It is a property of the
# machine, not of this kit: the corpus recorded 124 ms on 2026-07-26 and the same
# probe measures 182.6 ms here.
#
# It is named rather than inlined because it bounds what any budget can promise.
# Three events used to declare a 100 ms hard timeout, which the interpreter
# exceeds before reaching the first line of adr-hook.py -- no optimisation inside
# the hook could ever have met them (ADR-030).
MEASURED_INTERPRETER_FLOOR_MS = 182.6


def reference_payloads(project_root: Path) -> dict[str, dict[str, Any]]:
    """One payload per manifest event id, keyed the way the manifest is.

    Keyed by event id rather than by the client-facing event name, because
    `plan-exit` and `pr-create` are both registered as `pre-tool-use` with a
    matcher. Keyed by name they collided, so the lookup found no budget and the
    benchmark skipped both -- silently, while still reporting a pass (TASK-123).
    """
    common = {"cwd": str(project_root), "session_id": "benchmark-session"}
    edit_input = {"file_path": "hooks/adr_hook_core.py"}
    return {
        "session-start": {**common, "hook_event_name": "SessionStart"},
        "user-prompt-submit": {
            **common,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "implement deterministic ADR hook governance",
        },
        "subagent-start": {
            **common,
            "hook_event_name": "SubagentStart",
            "parent_context": "ADR-001 and ADR-004 govern this task.",
        },
        "pre-tool-use": {
            **common,
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": edit_input,
        },
        "post-tool-use": {
            **common,
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": edit_input,
        },
        # Matcher-dispatched: same event, different tool. These are the two the
        # old name-keyed lookup could not reach.
        "plan-exit": {
            **common,
            "hook_event_name": "PreToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {
                "plan": "Add a retry to the judge and swap the HTTP client."
            },
        },
        "pr-create": {
            **common,
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr create --base dev --title x --body y"},
        },
        "pre-compact": {**common, "hook_event_name": "PreCompact"},
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

    # The manifest is the single source for the budgets. The corpus used to
    # carry its own copy under client-facing event names, and that duplication
    # is what let two events go unmeasured: keyed by name, plan-exit and
    # pr-create both collapse onto pre-tool-use (TASK-123, ADR-030).
    manifest = json.loads(
        (plugin_root / "hooks" / "manifest.json").read_text(encoding="utf-8")
    )
    budgets = {event["id"]: event.get("latency") for event in manifest["events"]}
    payloads = reference_payloads(project_root)

    # An event with no budget must fail loudly. Skipping it silently is what the
    # old lookup did, and the report still read as a pass -- the exact failure
    # this harness exists to prevent.
    unmeasurable = sorted(key for key, value in budgets.items() if not value)
    unpayloaded = sorted(set(budgets) - set(payloads))
    uncovered = sorted(set(payloads) - set(budgets))
    if unmeasurable or unpayloaded or uncovered:
        raise ValueError(
            "hook benchmark cannot measure the declared event set: "
            f"no latency block for {unmeasurable}; "
            f"no payload for {unpayloaded}; "
            f"payload for undeclared {uncovered}"
        )

    results = {}
    for event_id, payload in payloads.items():
        command, host = host_command(
            plugin_root, "codex-cli", payload["hook_event_name"]
        )
        budget = budgets[event_id]
        # The kill timeout must clear the interpreter floor plus the hook's own
        # work, or the harness times out before the process has started and
        # reports a latency failure that is really a measurement artefact.
        timeout_seconds = max(
            budget["hard_timeout_ms"], MEASURED_INTERPRETER_FLOOR_MS * 2
        ) / 1000
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
        results[event_id] = {
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
