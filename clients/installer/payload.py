"""Prepared payload validation and activation-independent smoke probes."""

from __future__ import annotations

import json
import hashlib
import os
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Callable, Sequence

MIN_PYTHON = (3, 10)
PREPARED_MARKER = ".adr-kit-prepared-source.json"
REQUIRED_INSTALL_FILES = (
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".mcp.json",
    ".agents/plugins/marketplace.json",
    ".github/plugin/marketplace.json",
    "codex/.codex-plugin/plugin.json",
    "codex/hooks/hooks.json",
    "codex/.mcp.json",
    "copilot/plugin.json",
    "copilot/hooks.json",
    "copilot/.mcp.json",
    "hooks/hooks.json",
    "hooks/run-hook.cmd",
    "bin/adr-mcp",
)
JSON_INSTALL_FILES = tuple(path for path in REQUIRED_INSTALL_FILES if path.endswith(".json"))
Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

def validate_source(source: Path) -> str:
    missing = [relative for relative in REQUIRED_INSTALL_FILES if not (source / relative).is_file()]
    if missing:
        raise RuntimeError("ADR Kit source is incomplete; missing: " + ", ".join(missing))
    manifests = {}
    for relative in JSON_INSTALL_FILES:
        path = source / relative
        try:
            manifests[relative] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"invalid installer JSON {path}: {exc}") from exc

    def marketplace_version(relative: str) -> object:
        plugins = manifests[relative].get("plugins")
        if not isinstance(plugins, list) or not plugins:
            return None
        return plugins[0].get("version") if isinstance(plugins[0], dict) else None

    version = manifests[".claude-plugin/plugin.json"].get("version")
    versions = {
        ".claude-plugin/plugin.json": version,
        ".claude-plugin/marketplace.json": marketplace_version(".claude-plugin/marketplace.json"),
        "codex/.codex-plugin/plugin.json": manifests["codex/.codex-plugin/plugin.json"].get("version"),
        "copilot/plugin.json": manifests["copilot/plugin.json"].get("version"),
        ".github/plugin/marketplace.json": marketplace_version(".github/plugin/marketplace.json"),
    }
    if not isinstance(version, str) or not version:
        raise RuntimeError("Claude plugin manifest has no release version")
    repository = manifests[".claude-plugin/plugin.json"].get("repository")
    if repository != "https://github.com/rvdbreemen/adr-kit.git":
        raise RuntimeError(f"unapproved ADR Kit source identity: {repository!r}")
    mismatched = [f"{path}={value!r}" for path, value in versions.items() if value != version]
    if mismatched:
        raise RuntimeError(
            f"installer manifest versions must all equal {version!r}: " + ", ".join(mismatched)
        )
    return version

def payload_digest(root: Path) -> str:
    """Hash the prepared public payload without volatile state or its marker."""
    digest = hashlib.sha256()
    ignored = {
        ".git",
        ".native-cert",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "backlog",
    }
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        if path.is_file() and path.name != PREPARED_MARKER and path.suffix != ".pyc":
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
            digest.update(b"\0")
    return digest.hexdigest()

def validate_python(executable: str, runner: Runner) -> str:
    command = [
        executable,
        "-c",
        "import json,sys;print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable}))",
    ]
    try:
        result = runner(command)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Python runtime could not start: {executable}: {exc}") from exc
    if result.returncode:
        raise RuntimeError(
            f"Python runtime check failed: {executable}: {(result.stderr or result.stdout).strip()}"
        )
    try:
        payload = json.loads(result.stdout)
        version = tuple(int(part) for part in payload["version"][:2])
        resolved = str(Path(payload["executable"]).expanduser().resolve())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Python runtime returned an invalid probe result: {executable}") from exc
    if version < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; "
            f"{resolved} reports {version[0]}.{version[1]}"
        )
    return resolved


def default_install_root(
    *, system: str | None = None, env: dict[str, str] | None = None, home: Path | None = None
) -> Path:
    system, env, home = system or platform.system(), env or dict(os.environ), home or Path.home()
    if system == "Windows":
        base = Path(env.get("LOCALAPPDATA", home / "AppData" / "Local"))
    elif system == "Darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(env.get("XDG_DATA_HOME", home / ".local" / "share"))
    return base / "adr-kit" / "marketplaces"


def _safe_version(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "unknown"


def _patch_mcp_python(root: Path, executable: str) -> None:
    for relative in (".mcp.json", "codex/.mcp.json", "copilot/.mcp.json"):
        path = root / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        server = payload.get("mcpServers", {}).get("adr-kit")
        if not isinstance(server, dict):
            raise RuntimeError(f"{path}: missing mcpServers.adr-kit")
        server["command"] = executable
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for relative in (
        "hooks/run-hook.cmd",
        "codex/hooks/run-hook.cmd",
        "copilot/hooks/run-hook.cmd",
    ):
        wrapper = root / relative
        text = wrapper.read_text(encoding="utf-8")
        if "__ADR_KIT_PYTHON__" not in text:
            raise RuntimeError(f"{wrapper}: missing embedded Python placeholder")
        wrapper.write_text(
            text.replace("__ADR_KIT_PYTHON__", executable),
            encoding="utf-8",
            newline="\n",
        )


def _make_unix_entrypoints_executable(root: Path, system: str) -> None:
    if system == "Windows":
        return
    paths = [
        root / "hooks" / "run-hook.cmd",
        root / "codex" / "hooks" / "run-hook.cmd",
        root / "copilot" / "hooks" / "run-hook.cmd",
    ]
    for directory in (root / "bin", root / "codex" / "bin", root / "copilot" / "bin"):
        if directory.is_dir():
            paths.extend(path for path in directory.iterdir() if path.is_file())
    for path in paths:
        if path.is_file():
            path.chmod(path.stat().st_mode | 0o111)


def _copy_public_payload(source: Path, destination: Path) -> None:
    allowlist_path = source / "packaging" / "public-artifacts.json"
    try:
        allowlist = json.loads(allowlist_path.read_text(encoding="utf-8"))
        roots = allowlist["include_roots"]
        if not isinstance(roots, list) or not roots:
            raise TypeError("include_roots")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as exc:
        raise RuntimeError(f"invalid public payload allowlist: {exc}") from exc
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pdb")
    for relative in roots:
        if not isinstance(relative, str):
            raise RuntimeError("public payload roots must be strings")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeError(f"unsafe public payload root: {relative}")
        source_path = source / relative
        target = destination / relative
        if source_path.is_symlink():
            raise RuntimeError(f"public payload symlink is not allowed: {relative}")
        if source_path.is_dir():
            shutil.copytree(
                source_path,
                target,
                dirs_exist_ok=True,
                ignore=ignore,
            )
        elif source_path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
        else:
            raise RuntimeError(f"missing public payload root: {relative}")


def prepare_install_source(
    source: Path,
    *,
    version: str,
    python_executable: str,
    install_root: Path,
    dry_run: bool,
    system: str | None = None,
) -> Path:
    system = system or platform.system()
    destination = install_root.expanduser().resolve() / _safe_version(version)
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise RuntimeError(f"prepared marketplace must not be inside its source checkout: {destination}")
    print(f"Prepared marketplace: {destination}")
    print(f"  Python runtime: {python_executable}")
    if dry_run:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary, backup = destination.with_name(destination.name + ".tmp"), destination.with_name(destination.name + ".old")
    for path in (temporary, destination, backup):
        if path.exists() and not (path / PREPARED_MARKER).is_file():
            raise RuntimeError(f"refusing to replace unowned installer directory: {path}")
    if temporary.exists():
        shutil.rmtree(temporary)
    if backup.exists():
        shutil.rmtree(backup)
    temporary.mkdir()
    (temporary / PREPARED_MARKER).write_text("{}\n", encoding="utf-8")
    _copy_public_payload(source, temporary)
    _patch_mcp_python(temporary, python_executable)
    _make_unix_entrypoints_executable(temporary, system)
    marker = {
        "source": str(source),
        "version": version,
        "python": python_executable,
        "platform": system,
        "payload_sha256": payload_digest(temporary),
    }
    (temporary / PREPARED_MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    validate_source(temporary)
    if payload_digest(temporary) != marker["payload_sha256"]:
        raise RuntimeError("prepared payload digest changed before activation")
    if destination.exists():
        destination.replace(backup)
    try:
        temporary.replace(destination)
    except OSError:
        if backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    return destination


def remove_owned_payloads(install_root: Path) -> list[Path]:
    removed = []
    if not install_root.is_dir():
        return removed
    for child in sorted(install_root.iterdir()):
        if child.is_dir() and (child / PREPARED_MARKER).is_file():
            shutil.rmtree(child)
            removed.append(child)
    return removed


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
            command, cwd=str(working), env=env, capture_output=True, text=True,
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
