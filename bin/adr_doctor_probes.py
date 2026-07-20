"""Bounded native, MCP-extension, and local-model doctor probes."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
import sys
import os
from pathlib import Path

from adr_doctor_models import benchmark_extension, check
from adr_settings import (
    SettingsError,
    resolve_settings,
)
from clients.installer.detection import detect_clients
from hooks.hook_benchmark import measure as measure_hooks


def _command(values: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        values, cwd=str(cwd), capture_output=True, text=True,
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


def classify_model_probe(
    values: dict,
    *,
    candidates: list[tuple[str, str]],
    reachable: bool,
    rejection: str | None,
) -> tuple[str, str, str]:
    local = values["judgment"]["local"]
    provider, model = local.get("provider"), local.get("model")
    if not local["enabled"]:
        return "disabled", "disabled", "Enable local judgment in settings."
    if bool(provider) != bool(model):
        return (
            "missing-provider-or-model",
            "degraded",
            "Set both judgment.local.provider and judgment.local.model.",
        )
    if provider and provider != "ollama":
        return (
            "missing-provider",
            "degraded",
            f"Install/configure supported provider {provider!r}.",
        )
    if not reachable:
        return (
            "unreachable-backend",
            "degraded",
            "Start Ollama or change the configured local provider.",
        )
    if provider and (provider, model) not in candidates:
        return (
            "nonexistent-model-tag",
            "degraded",
            f"Install {model!r} or choose an existing Ollama model.",
        )
    if not provider and len(candidates) > 1:
        return (
            "ambiguous-discovery",
            "degraded",
            "Configure one provider/model explicitly.",
        )
    if not candidates:
        return (
            "no-models",
            "degraded",
            "Install a local Ollama model or disable local judgment.",
        )
    if rejection:
        return (
            "rejected-probe",
            "degraded",
            "Inspect Ollama health and permissions, then rerun --deep.",
        )
    return "healthy", "healthy", ""


def _ollama_candidates() -> tuple[list[tuple[str, str]], bool, str | None]:
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/tags",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ) as exc:
        return [], False, str(exc)
    models = payload.get("models", []) if isinstance(payload, dict) else []
    names = sorted({
        item["name"] for item in models
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    })
    return [("ollama", name) for name in names], True, None


def _model_deep(values: dict) -> dict:
    started = time.perf_counter()
    candidates, reachable, backend_error = _ollama_candidates()
    local = values["judgment"]["local"]
    configured = (local.get("provider"), local.get("model"))
    rejection = None
    if reachable and all(configured) and configured in candidates and configured[0] == "ollama":
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/show",
            data=json.dumps({"model": configured[1]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=2.0) as response:
                if response.status >= 400:
                    rejection = f"HTTP {response.status}"
        except (OSError, urllib.error.URLError) as exc:
            rejection = str(exc)
    state, status, action = classify_model_probe(
        values,
        candidates=candidates,
        reachable=reachable,
        rejection=rejection,
    )
    elapsed = (time.perf_counter() - started) * 1000
    return check(
        "local-judgment-live", status=status, required=False,
        summary=f"bounded provider/model identity probe: {state}",
        evidence=[{
            "provider": configured[0],
            "model": configured[1],
            "candidate_count": len(candidates),
            "elapsed_ms": round(elapsed, 3),
            "backend_error": backend_error,
            "rejection": rejection,
        }],
        actions=[{"detail": action}] if action else [],
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
            and {"adr_context", "adr_judge", "adr_status", "adr_quality"} == tools
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
    try:
        values = resolve_settings(root, global_path=global_settings)["values"]
        model = _model_deep(values)
        extensions.append(model)
        if not check_only and model["evidence"]:
            state_path = root / ".adr-kit" / "model-health.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = state_path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": model["status"],
                        "checked_at": time.time(),
                        **model["evidence"][0],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, state_path)
    except SettingsError:
        pass
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
