"""Bounded native and MCP-extension doctor probes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from adr_doctor_models import benchmark_extension, check
from clients.installer.detection import detect_clients
from hooks.hook_benchmark import measure as measure_hooks


def _command(values: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    # DEVNULL rather than the console, because `timeout=` is not a bound here.
    # On Windows `copilot` resolves to a .CMD shim, so the child is cmd.exe with
    # a node grandchild; subprocess.run's own TimeoutExpired handler then
    # re-enters communicate() with no bound, and kill() is TerminateProcess on
    # the shim alone. Measured: a 2s timeout returned after 8.18s behind a shim
    # against 2.03s without one. Closing stdin does not restore the bound, but
    # it removes the one thing that would make the wait permanent instead of
    # merely long.
    return subprocess.run(
        values, cwd=str(cwd), capture_output=True, text=True,
        stdin=subprocess.DEVNULL,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def _native_deep(root: Path, name: str, executable: str) -> dict:
    command = (
        [executable, "plugin", "list", "--json"]
        if name in {"claude", "codex"}
        else [executable, "plugin", "list"]
    )
    try:
        result = _command(command, cwd=root, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return check(
            "native-registration", client=name, status="failed",
            summary=f"native list probe failed: {exc}",
        )
    output = (result.stdout + result.stderr).lower()
    if "trust" in output or "review" in output:
        status = "trust-pending"
    elif result.returncode:
        status = "failed"
    elif "adr-kit" not in output:
        status = "stale"
    else:
        status = "healthy"
    return check(
        "native-registration", client=name, status=status,
        summary=f"bounded native plugin-list probe returned {status}",
        evidence=[{"command": command, "returncode": result.returncode}],
        actions=[{"detail": f"Review or reinstall ADR Kit in {name}."}]
        if status != "healthy" else [],
    )


def _mcp_deep(root: Path, plugin_root: Path) -> dict:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "adr-doctor", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "adr_status",
                "arguments": {"project_root": str(root)},
            },
        },
    ]
    try:
        result = subprocess.run(
            [sys.executable, str(plugin_root / "bin" / "adr-mcp")],
            input="\n".join(json.dumps(item) for item in messages) + "\n",
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        responses = {
            item["id"]: item
            for line in result.stdout.splitlines()
            if (item := json.loads(line)).get("id") is not None
        }
        tools = {item["name"] for item in responses[2]["result"]["tools"]}
        called = responses[3]["result"].get("isError") is not True
        healthy = (
            result.returncode == 0
            and {
                "adr_context",
                "adr_judge",
                "adr_status",
                "adr_quality",
                "adr_readiness",
            } == tools
            and called
        )
    except (
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as exc:
        return check(
            "mcp-live", status="failed",
            summary=f"MCP initialize/list/call probe failed: {exc}",
            actions=[{"detail": "Run adr-doctor --deep after reinstalling ADR Kit."}],
        )
    return check(
        "mcp-live", status="healthy" if healthy else "failed",
        summary=(
            "MCP initialize, tools/list, and adr_status call passed"
            if healthy else "MCP handshake returned an incomplete result"
        ),
        evidence=[{
            "returncode": result.returncode,
            "tools": sorted(tools),
            "call_ok": called,
        }],
    )


def run_deep_extensions(
    root: Path,
    plugin_root: Path,
    *,
    checks: list[dict],
    global_settings: Path | None,
    check_only: bool,
) -> list[dict]:
    extensions = [
        _native_deep(root, name, client.executable)
        for name, client in detect_clients().items()
    ]
    extensions.append(_mcp_deep(root, plugin_root))
    # The harness reads plugin_root/tests/fixtures/hooks/reference-corpus.json,
    # and `tests` is a forbidden segment in the public payload -- so the fixture
    # is absent from EVERY installed payload, not only from a generated client
    # tree. Without this branch that lands in the except below as "failed",
    # which reads like a broken harness rather than a fixture that was never
    # shipped. Pre-existing behaviour; only the wording changes.
    corpus = plugin_root / "tests" / "fixtures" / "hooks" / "reference-corpus.json"
    if not corpus.is_file():
        extensions.append(check(
            "hook-latency-extension", status="unsupported", required=False,
            summary=(
                "hook latency corpus is not part of an installed payload; "
                "run the harness from a checkout"
            ),
        ))
        return extensions
    try:
        hook_result = measure_hooks(plugin_root, root, samples=5)
        aggregate = {
            "p50_ms": max(
                item["p50_ms"] for item in hook_result["results"].values()
            ),
            "p95_ms": max(
                item["p95_ms"] for item in hook_result["results"].values()
            ),
            "max_ms": max(
                item["max_ms"] for item in hook_result["results"].values()
            ),
        }
        extension = benchmark_extension(
            method_id=hook_result["method_id"],
            state=hook_result["cache_state"],
            sample_count=5,
            reference_fixture=hook_result["reference_fixture"],
            budget={"event_specific": True},
            measurements=aggregate,
        )
        extension["process_startup_included"] = hook_result[
            "process_startup_included"
        ]
        extension["results"] = hook_result["results"]
        extensions.append(check(
            "hook-latency-extension",
            status="healthy" if hook_result["all_targets_met"] else "degraded",
            required=False,
            summary=(
                "hook latency targets passed"
                if hook_result["all_targets_met"]
                else "one or more hook latency targets missed"
            ),
            evidence=[{
                "machine": hook_result["machine"],
                "ci_variance_percent": hook_result["ci_variance_percent"],
            }],
            extension=extension,
        ))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        extensions.append(check(
            "hook-latency-extension", status="failed", required=False,
            summary=f"bounded hook latency harness failed: {exc}",
        ))
    return extensions
