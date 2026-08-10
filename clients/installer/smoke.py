"""Activation-independent smoke probes for a prepared payload.

Split from ``payload.py`` along the seam its own docstring already named:
preparing a payload is one job, proving the prepared runtimes actually answer
is another. ADR-010 caps a support module at 400 lines and ``payload.py`` had
reached it exactly.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path


def _validate_mcp_process(
    command: list[str], *, working_directory: Path, environment: dict[str, str] | None = None
) -> None:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "adr-kit-installer", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    try:
        result = subprocess.run(
            command,
            input="\n".join(json.dumps(message) for message in messages) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(working_directory),
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"packaged MCP server could not start: {exc}") from exc
    if result.returncode:
        raise RuntimeError(f"packaged MCP smoke test failed: {(result.stderr or result.stdout).strip()}")
    if f"serving root={working_directory.resolve()} " not in result.stderr:
        raise RuntimeError(f"packaged MCP server used an unexpected project root; expected {working_directory.resolve()}")
    try:
        responses = {
            response["id"]: response
            for line in result.stdout.splitlines()
            if (response := json.loads(line)).get("id") is not None
        }
        names = {tool["name"] for tool in responses[2]["result"]["tools"]}
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("packaged MCP smoke test returned invalid JSON-RPC") from exc
    expected = {"adr_context", "adr_judge", "adr_status", "adr_quality", "adr_readiness"}
    if names != expected:
        raise RuntimeError("packaged MCP smoke test returned unexpected tools: " + ", ".join(sorted(names)))


def validate_prepared_mcp(
    source: Path, python_executable: str, *, copilot_project_root: Path | None = None
) -> None:
    temporary = None
    if copilot_project_root is None:
        temporary = tempfile.TemporaryDirectory(prefix="adr-kit-copilot-project-")
        copilot_project_root = Path(temporary.name)
    copilot_project_root.mkdir(parents=True, exist_ok=True)
    try:
        for name in ("claude", "codex", "copilot"):
            root = source if name == "claude" else source / name
            server = json.loads((root / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {}).get("adr-kit", {})
            command, args = server.get("command"), server.get("args")
            if command != python_executable:
                raise RuntimeError(f"{name} MCP runtime mismatch: expected {python_executable!r}, found {command!r}")
            if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
                raise RuntimeError(f"{name} MCP args must be a string list")
            environment, working = os.environ.copy(), root
            if name in {"claude", "copilot"}:
                variable = (
                    "${CLAUDE_PLUGIN_ROOT}"
                    if name == "claude"
                    else "${PLUGIN_ROOT}"
                )
                if not any(variable in value for value in args):
                    raise RuntimeError(
                        f"{name} MCP args must resolve from {variable}"
                    )
                environment.update({"PLUGIN_ROOT": str(root), "COPILOT_PLUGIN_ROOT": str(root), "CLAUDE_PLUGIN_ROOT": str(root)})
                args = [value.replace(variable, str(root)) for value in args]
                working = copilot_project_root
            _validate_mcp_process([command, *args], working_directory=working, environment=environment)
        print("Prepared MCP runtimes: PASS (initialize + tools/list)")
    finally:
        if temporary is not None:
            temporary.cleanup()


def validate_prepared_hooks(source: Path) -> None:
    wrapper = source / "hooks" / "run-hook.cmd"
    if platform.system() == "Windows":
        command, working = ["cmd.exe", "/d", "/c", str(wrapper), "session-start"], wrapper.parent
    else:
        command, working = ["sh", str(wrapper), "session-start"], source
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(source)
    try:
        result = subprocess.run(
            # The hook reads a payload from stdin. Without an explicit closed
            # stdin it inherits the installer's console and blocks until EOF,
            # which never arrives; the 30s timeout then re-enters communicate()
            # without a bound and the installer stalls with no error at all.
            command, cwd=str(working), env=env, capture_output=True, text=True,
            stdin=subprocess.DEVNULL,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"packaged Claude hook could not start: {exc}") from exc
    if result.returncode:
        raise RuntimeError(f"packaged Claude hook smoke test failed: {(result.stderr or result.stdout).strip()}")
    if result.stdout.strip():
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("packaged Claude hook returned invalid hook JSON") from exc
    print("Prepared Claude hook runtime: PASS (SessionStart fail-open contract)")
