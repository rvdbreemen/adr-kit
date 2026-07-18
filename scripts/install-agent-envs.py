#!/usr/bin/env python3
"""Detect supported agent CLIs and install ADR Kit through each native plugin API."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent
SUPPORTED = ("claude", "codex", "copilot")
VERSION_MARKERS = {
    "claude": "Claude Code",
    "codex": "codex-cli",
    "copilot": "GitHub Copilot CLI",
}
MARKETPLACES = {
    "claude": "rvdbreemen-adr-kit",
    "codex": "rvdbreemen-adr-kit-codex",
    "copilot": "rvdbreemen-adr-kit-copilot",
}
MIN_PYTHON = (3, 10)
PREPARED_MARKER = ".adr-kit-prepared-source.json"
REQUIRED_INSTALL_FILES = (
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    ".github/plugin/marketplace.json",
    "codex/.codex-plugin/plugin.json",
    "codex/.mcp.json",
    "copilot/plugin.json",
    "copilot/.mcp.json",
    "bin/adr-mcp",
)
JSON_INSTALL_FILES = tuple(
    path for path in REQUIRED_INSTALL_FILES if path.endswith(".json")
)


@dataclass(frozen=True)
class Client:
    name: str
    executable: str
    version: str


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _run_version(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )


def _display_command(command: Sequence[str], system: str | None = None) -> str:
    if (system or platform.system()) == "Windows":
        return subprocess.list2cmdline(list(command))
    return shlex.join(list(command))


def validate_source(source: Path) -> str:
    """Validate the complete marketplace payload before client mutations."""
    missing = [
        relative
        for relative in REQUIRED_INSTALL_FILES
        if not (source / relative).is_file()
    ]
    if missing:
        raise RuntimeError(
            "ADR Kit source is incomplete; missing: " + ", ".join(missing)
        )

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
        first = plugins[0]
        return first.get("version") if isinstance(first, dict) else None

    version = manifests[".claude-plugin/plugin.json"].get("version")
    versions = {
        ".claude-plugin/plugin.json": version,
        ".claude-plugin/marketplace.json": marketplace_version(
            ".claude-plugin/marketplace.json"
        ),
        "codex/.codex-plugin/plugin.json": manifests[
            "codex/.codex-plugin/plugin.json"
        ].get("version"),
        "copilot/plugin.json": manifests["copilot/plugin.json"].get("version"),
        ".github/plugin/marketplace.json": marketplace_version(
            ".github/plugin/marketplace.json"
        ),
    }
    if not isinstance(version, str) or not version:
        raise RuntimeError("Claude plugin manifest has no release version")
    mismatched = [
        f"{path}={value!r}"
        for path, value in versions.items()
        if value != version
    ]
    if mismatched:
        raise RuntimeError(
            f"installer manifest versions must all equal {version!r}: "
            + ", ".join(mismatched)
        )
    return version


def validate_python(
    executable: str,
    runner: Runner = _run,
) -> str:
    """Require a child-process-capable Python 3.10+ runtime."""
    command = [
        executable,
        "-c",
        (
            "import json,sys;"
            "print(json.dumps({'version':list(sys.version_info[:3]),"
            "'executable':sys.executable}))"
        ),
    ]
    try:
        result = runner(command)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            f"Python runtime could not start: {executable}: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Python runtime check failed: {executable}: {detail}")
    try:
        payload = json.loads(result.stdout)
        version = tuple(int(part) for part in payload["version"][:2])
        resolved = str(Path(payload["executable"]).expanduser().resolve())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Python runtime returned an invalid probe result: {executable}"
        ) from exc
    if version < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; "
            f"{resolved} reports {version[0]}.{version[1]}"
        )
    return resolved


def default_install_root(
    *,
    system: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return a persistent per-user data location for prepared marketplaces."""
    system = system or platform.system()
    env = env if env is not None else dict(os.environ)
    home = home or Path.home()
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
    for relative in ("codex/.mcp.json", "copilot/.mcp.json"):
        path = root / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        server = payload.get("mcpServers", {}).get("adr-kit")
        if not isinstance(server, dict):
            raise RuntimeError(f"{path}: missing mcpServers.adr-kit")
        server["command"] = executable
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _make_unix_entrypoints_executable(root: Path, system: str) -> None:
    if system == "Windows":
        return
    paths = [root / ".claude-plugin" / "hooks" / "run-hook.cmd"]
    for directory in (root / "bin", root / "codex" / "bin", root / "copilot" / "bin"):
        if directory.is_dir():
            paths.extend(path for path in directory.iterdir() if path.is_file())
    for path in paths:
        if path.is_file():
            path.chmod(path.stat().st_mode | 0o111)


def prepare_install_source(
    source: Path,
    *,
    version: str,
    python_executable: str,
    install_root: Path,
    dry_run: bool,
    system: str | None = None,
) -> Path:
    """Create a persistent platform-local marketplace with runtime commands."""
    system = system or platform.system()
    destination = install_root.expanduser().resolve() / _safe_version(version)
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            f"prepared marketplace must not be inside its source checkout: {destination}"
        )
    print(f"Prepared marketplace: {destination}")
    print(f"  Python runtime: {python_executable}")
    if dry_run:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    backup = destination.with_name(destination.name + ".old")
    for path in (temporary, destination, backup):
        if path.exists() and not (path / PREPARED_MARKER).is_file():
            raise RuntimeError(
                f"refusing to replace unowned installer directory: {path}"
            )
    for path in (temporary, backup):
        if path.exists():
            shutil.rmtree(path)

    ignore = shutil.ignore_patterns(
        ".git",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "*.pyc",
        "backlog",
    )
    temporary.mkdir()
    (temporary / PREPARED_MARKER).write_text("{}\n", encoding="utf-8")
    shutil.copytree(source, temporary, ignore=ignore, dirs_exist_ok=True)
    _patch_mcp_python(temporary, python_executable)
    _make_unix_entrypoints_executable(temporary, system)
    marker = {
        "source": str(source),
        "version": version,
        "python": python_executable,
        "platform": system,
    }
    (temporary / PREPARED_MARKER).write_text(
        json.dumps(marker, indent=2) + "\n",
        encoding="utf-8",
    )
    validate_source(temporary)

    if destination.exists():
        destination.replace(backup)
    try:
        temporary.replace(destination)
    except OSError:
        if backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    return destination


def detect_client(
    name: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = _run_version,
) -> Client | None:
    try:
        executable = which(name)
    except OSError:
        return None
    if not executable:
        return None
    try:
        result = runner([executable, "--version"])
    except (OSError, subprocess.SubprocessError):
        return None
    version = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or VERSION_MARKERS[name].lower() not in version.lower():
        return None
    return Client(name, str(Path(executable).resolve()), version.splitlines()[0])


def detect_clients(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = _run_version,
) -> dict[str, Client]:
    return {
        name: client
        for name in SUPPORTED
        if (client := detect_client(name, which=which, runner=runner)) is not None
    }


def _json_output(result: subprocess.CompletedProcess[str]) -> object:
    try:
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return None


def _require_success(
    result: subprocess.CompletedProcess[str],
    description: str,
) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout).strip()
    raise RuntimeError(
        f"{description} failed ({result.returncode})"
        + (f": {detail}" if detail else "")
    )


def _string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for entry in value for item in _string_values(entry)]
    if isinstance(value, dict):
        return [item for entry in value.values() for item in _string_values(entry)]
    return []


def _normalized_path_text(value: str) -> str:
    text = value.replace("\\\\?\\", "").replace("\\", "/").rstrip("/")
    return text.casefold()


def marketplace_source_matches(value: object, source: Path) -> bool:
    expected = _normalized_path_text(str(source.resolve()))
    return any(
        _normalized_path_text(candidate) == expected
        or expected in _normalized_path_text(candidate)
        for candidate in _string_values(value)
    )


def claude_marketplace_source_matches(value: object, source: Path) -> bool:
    if marketplace_source_matches(value, source):
        return True
    return (
        isinstance(value, dict)
        and value.get("source") in {"directory", "local"}
        and (source / PREPARED_MARKER).is_file()
    )


def _invoke(
    command: Sequence[str],
    *,
    dry_run: bool,
    runner: Runner,
) -> subprocess.CompletedProcess[str]:
    printable = _display_command(command)
    print(f"  $ {printable}")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    result = runner(command)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {printable}\n{detail}")
    return result


def install_claude(
    client: Client,
    source: Path,
    dry_run: bool,
    runner: Runner,
    desired_version: str | None = None,
) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    _require_success(listed, "Claude marketplace listing")
    entries = {
        item.get("name"): item
        for item in (_json_output(listed) or [])
        if isinstance(item, dict)
    }
    marketplace = entries.get(MARKETPLACES["claude"])
    if marketplace is not None and not claude_marketplace_source_matches(
        marketplace, source
    ):
        _invoke(
            [
                client.executable,
                "plugin",
                "marketplace",
                "remove",
                MARKETPLACES["claude"],
                "--scope",
                "user",
            ],
            dry_run=dry_run,
            runner=runner,
        )
        marketplace = None
    if marketplace is None:
        _invoke(
            [
                client.executable,
                "plugin",
                "marketplace",
                "add",
                str(source),
                "--scope",
                "user",
            ],
            dry_run=dry_run,
            runner=runner,
        )
    installed = runner([client.executable, "plugin", "list", "--json"])
    _require_success(installed, "Claude plugin listing")
    payload = _json_output(installed)
    plugin_id = f"adr-kit@{MARKETPLACES['claude']}"
    user_install = any(
        isinstance(item, dict)
        and item.get("id") == plugin_id
        and item.get("scope", "user") == "user"
        for item in (payload or [])
    )
    action = "update" if user_install else "install"
    command = [client.executable, "plugin", action, plugin_id, "--scope", "user"]
    _invoke(command, dry_run=dry_run, runner=runner)


def install_codex(
    client: Client,
    source: Path,
    dry_run: bool,
    runner: Runner,
    desired_version: str | None = None,
) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    _require_success(listed, "Codex marketplace listing")
    payload = _json_output(listed)
    marketplaces = {
        item.get("name"): item
        for item in (payload or {}).get("marketplaces", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}
    marketplace = marketplaces.get(MARKETPLACES["codex"])

    installed = runner([client.executable, "plugin", "list", "--json"])
    _require_success(installed, "Codex plugin listing")
    payload = _json_output(installed)
    plugin_id = f"adr-kit@{MARKETPLACES['codex']}"
    installed_entries = {
        item.get("pluginId"): item
        for item in (payload or {}).get("installed", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}

    if marketplace is not None and not marketplace_source_matches(
        marketplace, source
    ):
        if plugin_id in installed_entries:
            _invoke(
                [client.executable, "plugin", "remove", plugin_id],
                dry_run=dry_run,
                runner=runner,
            )
            installed_entries = {}
        _invoke(
            [
                client.executable,
                "plugin",
                "marketplace",
                "remove",
                MARKETPLACES["codex"],
                "--json",
            ],
            dry_run=dry_run,
            runner=runner,
        )
        marketplace = None
    if marketplace is None:
        _invoke(
            [client.executable, "plugin", "marketplace", "add", str(source), "--json"],
            dry_run=dry_run,
            runner=runner,
        )
    desired = desired_version or json.loads(
        (source / "codex" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    ).get("version")
    current = installed_entries.get(plugin_id, {}).get("version")
    if current != desired:
        if plugin_id in installed_entries:
            _invoke(
                [client.executable, "plugin", "remove", plugin_id],
                dry_run=dry_run,
                runner=runner,
            )
        _invoke(
            [client.executable, "plugin", "add", plugin_id, "--json"],
            dry_run=dry_run,
            runner=runner,
        )


def install_copilot(
    client: Client,
    source: Path,
    dry_run: bool,
    runner: Runner,
    desired_version: str | None = None,
) -> None:
    marketplaces = runner([client.executable, "plugin", "marketplace", "list"])
    _require_success(marketplaces, "Copilot marketplace listing")
    listing = marketplaces.stdout + marketplaces.stderr
    registered = MARKETPLACES["copilot"] in listing
    if registered and not marketplace_source_matches(listing, source):
        _invoke(
            [
                client.executable,
                "plugin",
                "marketplace",
                "remove",
                MARKETPLACES["copilot"],
                "--force",
            ],
            dry_run=dry_run,
            runner=runner,
        )
        registered = False
    if not registered:
        _invoke(
            [client.executable, "plugin", "marketplace", "add", str(source)],
            dry_run=dry_run,
            runner=runner,
        )
    listed = runner([client.executable, "plugin", "list"])
    _require_success(listed, "Copilot plugin listing")
    installed = (
        registered and "adr-kit" in (listed.stdout + listed.stderr).lower()
    )
    command = (
        [client.executable, "plugin", "update", "adr-kit"]
        if installed
        else [
            client.executable,
            "plugin",
            "install",
            f"adr-kit@{MARKETPLACES['copilot']}",
        ]
    )
    _invoke(command, dry_run=dry_run, runner=runner)


INSTALLERS = {
    "claude": install_claude,
    "codex": install_codex,
    "copilot": install_copilot,
}


def validate_prepared_mcp(source: Path, python_executable: str) -> None:
    """Start the packaged MCP server and complete initialize/tools-list."""
    for client_name in ("codex", "copilot"):
        config = json.loads(
            (source / client_name / ".mcp.json").read_text(encoding="utf-8")
        )
        command = config.get("mcpServers", {}).get("adr-kit", {}).get("command")
        if command != python_executable:
            raise RuntimeError(
                f"{client_name} MCP runtime mismatch: "
                f"expected {python_executable!r}, found {command!r}"
            )

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
    payload = "\n".join(json.dumps(message) for message in messages) + "\n"
    try:
        result = subprocess.run(
            [
                python_executable,
                str(source / "codex" / "bin" / "adr-mcp"),
                "--root",
                str(source),
            ],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"packaged MCP server could not start: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"packaged MCP smoke test failed: {detail}")
    responses = {}
    try:
        for line in result.stdout.splitlines():
            response = json.loads(line)
            if response.get("id") is not None:
                responses[response["id"]] = response
        tools = responses[2]["result"]["tools"]
        names = {tool["name"] for tool in tools}
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("packaged MCP smoke test returned invalid JSON-RPC") from exc
    expected = {"adr_context", "adr_judge", "adr_status", "adr_quality"}
    if names != expected:
        raise RuntimeError(
            "packaged MCP smoke test returned unexpected tools: "
            + ", ".join(sorted(names))
        )
    print("Prepared MCP runtime: PASS (initialize + tools/list)")


def validate_prepared_hooks(source: Path) -> None:
    """Execute the packaged Claude hook wrapper through the platform shell."""
    wrapper = source / ".claude-plugin" / "hooks" / "run-hook.cmd"
    if platform.system() == "Windows":
        # Absolute path mirrors plugin.json and stays resolvable when
        # NoDefaultCurrentDirectoryInExePath drops the cwd from the search path.
        command = ["cmd.exe", "/d", "/c", str(wrapper), "session-start"]
        working_directory = wrapper.parent
    else:
        command = ["sh", str(wrapper), "session-start"]
        working_directory = source
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(source)
    try:
        result = subprocess.run(
            command,
            cwd=str(working_directory),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"packaged Claude hook could not start: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"packaged Claude hook smoke test failed: {detail}")
    if result.stdout.strip():
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "packaged Claude hook returned invalid hook JSON"
            ) from exc
    print("Prepared Claude hook runtime: PASS (SessionStart fail-open contract)")


def validate_install(name: str, client: Client, runner: Runner = _run) -> None:
    if name == "claude":
        result = runner([client.executable, "plugin", "list", "--json"])
        expected = f"adr-kit@{MARKETPLACES[name]}"
        found = expected in (result.stdout + result.stderr)
    elif name == "codex":
        result = runner([client.executable, "plugin", "list", "--json"])
        expected = f"adr-kit@{MARKETPLACES[name]}"
        found = expected in (result.stdout + result.stderr)
    else:
        result = runner([client.executable, "plugin", "list"])
        found = f"adr-kit@{MARKETPLACES[name]}" in (result.stdout + result.stderr)
    if result.returncode != 0 or not found:
        raise RuntimeError(f"{name} validation failed: ADR Kit plugin not listed")
    if name in {"codex", "copilot"}:
        mcp = runner([client.executable, "mcp", "list"])
        if mcp.returncode != 0 or "adr-kit" not in (mcp.stdout + mcp.stderr):
            raise RuntimeError(f"{name} validation failed: adr-kit MCP server not listed")
    print(f"  validation: PASS ({name})")


def report_migration_plan(
    source: Path,
    project_root: Path,
    runner: Runner = _run,
) -> None:
    """Run read-only ADR format discovery after install; fail open on errors."""
    adr_dir = project_root / "docs" / "adr"
    if not adr_dir.is_dir():
        print(f"ADR format scan: no ADR directory at {adr_dir}; nothing to inspect.")
        return
    command = [
        sys.executable,
        str(source / "bin" / "adr-migrate"),
        "--plan",
        str(adr_dir),
    ]
    print(f"ADR format scan (read-only): {adr_dir}")
    result = runner(command)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        print(
            "  warning: format discovery could not complete; "
            f"installation remains valid. {detail}",
            file=sys.stderr,
        )
        return
    output = result.stdout.strip()
    if output:
        for line in output.splitlines():
            print(f"  {line}")


def parse_selection(raw: str, detected: dict[str, Client]) -> list[str]:
    if raw == "auto":
        return [name for name in SUPPORTED if name in detected]
    if raw == "all":
        missing = [name for name in SUPPORTED if name not in detected]
        if missing:
            raise ValueError("requested clients not detected: " + ", ".join(missing))
        return list(SUPPORTED)
    selected = [part.strip().lower() for part in raw.split(",") if part.strip()]
    unknown = [name for name in selected if name not in SUPPORTED]
    if unknown:
        raise ValueError("unsupported clients: " + ", ".join(unknown))
    missing = [name for name in selected if name not in detected]
    if missing:
        raise ValueError("requested clients not detected: " + ", ".join(missing))
    return list(dict.fromkeys(selected))


def install_selected_clients(
    selected: Sequence[str],
    detected: dict[str, Client],
    source: Path,
    *,
    version: str,
    dry_run: bool,
    skip_validation: bool,
    runner: Runner = _run,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Install every selected client, isolating failures per client."""
    installed = []
    failures = []
    for name in selected:
        print(f"Installing ADR Kit for {name}:")
        try:
            INSTALLERS[name](
                detected[name],
                source,
                dry_run,
                runner,
                desired_version=version,
            )
            if not dry_run and not skip_validation:
                validate_install(name, detected[name], runner)
            installed.append(name)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            failures.append((name, str(exc)))
            print(f"  FAILED ({name}): {exc}", file=sys.stderr)
    return installed, failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install ADR Kit for detected Claude Code, Codex, and Copilot CLIs."
    )
    parser.add_argument(
        "--clients",
        "--agents",
        default="auto",
        help="auto (default), all, or comma-separated claude,codex,copilot",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT,
        help="ADR Kit checkout or marketplace root (default: this repository).",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help=(
            "Project whose docs/adr should be scanned after install "
            "(default: current directory)."
        ),
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help=(
            "Python 3.10+ executable embedded in prepared Codex/Copilot MCP "
            "configuration (default: the interpreter running this installer)."
        ),
    )
    parser.add_argument(
        "--install-root",
        type=Path,
        default=None,
        help=(
            "Persistent directory for prepared platform-local marketplaces "
            "(default: the operating system's per-user data directory)."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Install without post-install plugin and MCP listing checks.",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Print detected clients without installing.",
    )
    args = parser.parse_args(argv)
    source = args.source.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    try:
        version = validate_source(source)
        python_executable = validate_python(args.python)
    except RuntimeError as exc:
        parser.error(str(exc))

    detected = detect_clients()
    for name in SUPPORTED:
        client = detected.get(name)
        state = f"{client.executable} ({client.version})" if client else "not detected"
        print(f"{name}: {state}")
    if args.detect_only:
        return 0
    try:
        selected = parse_selection(args.clients, detected)
    except ValueError as exc:
        parser.error(str(exc))
    if not selected:
        print("No supported CLI detected; nothing installed.", file=sys.stderr)
        return 2

    install_root = (
        args.install_root.expanduser().resolve()
        if args.install_root is not None
        else default_install_root()
    )
    try:
        prepared_source = prepare_install_source(
            source,
            version=version,
            python_executable=python_executable,
            install_root=install_root,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            validate_prepared_mcp(prepared_source, python_executable)
            validate_prepared_hooks(prepared_source)
    except RuntimeError as exc:
        parser.error(str(exc))

    installed, failures = install_selected_clients(
        selected,
        detected,
        prepared_source,
        version=version,
        dry_run=args.dry_run,
        skip_validation=args.skip_validation,
    )
    report_migration_plan(source, args.project_root.expanduser().resolve())
    if installed:
        print("ADR Kit install complete for: " + ", ".join(installed))
    if failures:
        print(
            "ADR Kit install failures: "
            + "; ".join(f"{name}: {detail}" for name, detail in failures),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
