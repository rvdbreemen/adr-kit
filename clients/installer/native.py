"""Native plugin-manager mutations for the three certified clients."""

from __future__ import annotations

import json
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from .contracts import CLIENT_IDS, SPECS
from .detection import Client
from .payload import PREPARED_MARKER

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
MARKETPLACES = {name: SPECS[name].marketplace for name in CLIENT_IDS}


def display_command(command: Sequence[str], system: str | None = None) -> str:
    return subprocess.list2cmdline(list(command)) if (system or platform.system()) == "Windows" else shlex.join(list(command))


def json_output(result: subprocess.CompletedProcess[str]) -> object:
    try:
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return None


def require_success(result: subprocess.CompletedProcess[str], description: str) -> None:
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{description} failed ({result.returncode})" + (f": {detail}" if detail else ""))


def _string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for entry in value for item in _string_values(entry)]
    if isinstance(value, dict):
        return [item for entry in value.values() for item in _string_values(entry)]
    return []


def _normalized_path_text(value: str) -> str:
    return value.replace("\\\\?\\", "").replace("\\", "/").rstrip("/").casefold()


def marketplace_source_matches(value: object, source: Path) -> bool:
    expected = _normalized_path_text(str(source.resolve()))
    return any(
        _normalized_path_text(candidate) == expected or expected in _normalized_path_text(candidate)
        for candidate in _string_values(value)
    )


def claude_marketplace_source_matches(value: object, source: Path) -> bool:
    return marketplace_source_matches(value, source) or (
        isinstance(value, dict)
        and value.get("source") in {"directory", "local"}
        and (source / PREPARED_MARKER).is_file()
    )


def invoke(
    command: Sequence[str], *, dry_run: bool, runner: Runner
) -> subprocess.CompletedProcess[str]:
    printable = display_command(command)
    print(f"  $ {printable}")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    result = runner(command)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {printable}\n{detail}")
    return result


def install_claude(
    client: Client, source: Path, dry_run: bool, runner: Runner, desired_version: str | None = None
) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    require_success(listed, "Claude marketplace listing")
    entries = {
        item.get("name"): item
        for item in (json_output(listed) or [])
        if isinstance(item, dict)
    }
    marketplace = entries.get(MARKETPLACES["claude"])
    if marketplace is not None and not claude_marketplace_source_matches(marketplace, source):
        invoke(
            [client.executable, "plugin", "marketplace", "remove", MARKETPLACES["claude"], "--scope", "user"],
            dry_run=dry_run, runner=runner,
        )
        marketplace = None
    if marketplace is None:
        invoke(
            [client.executable, "plugin", "marketplace", "add", str(source), "--scope", "user"],
            dry_run=dry_run, runner=runner,
        )
    installed = runner([client.executable, "plugin", "list", "--json"])
    require_success(installed, "Claude plugin listing")
    plugin_id = f"adr-kit@{MARKETPLACES['claude']}"
    user_entry = next(
        (
            item for item in (json_output(installed) or [])
            if isinstance(item, dict)
            and item.get("id") == plugin_id
            and item.get("scope", "user") == "user"
        ),
        None,
    )
    user_install = user_entry is not None
    if desired_version and user_entry and user_entry.get("version") == desired_version:
        print(f"  no-op: {plugin_id} {desired_version} is already healthy")
        return
    invoke(
        [client.executable, "plugin", "update" if user_install else "install", plugin_id, "--scope", "user"],
        dry_run=dry_run, runner=runner,
    )


def install_codex(
    client: Client, source: Path, dry_run: bool, runner: Runner, desired_version: str | None = None
) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    require_success(listed, "Codex marketplace listing")
    payload = json_output(listed)
    marketplaces = {
        item.get("name"): item
        for item in (payload or {}).get("marketplaces", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}
    marketplace = marketplaces.get(MARKETPLACES["codex"])
    installed = runner([client.executable, "plugin", "list", "--json"])
    require_success(installed, "Codex plugin listing")
    payload = json_output(installed)
    plugin_id = f"adr-kit@{MARKETPLACES['codex']}"
    entries = {
        item.get("pluginId"): item
        for item in (payload or {}).get("installed", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}
    if marketplace is not None and not marketplace_source_matches(marketplace, source):
        if plugin_id in entries:
            invoke([client.executable, "plugin", "remove", plugin_id], dry_run=dry_run, runner=runner)
            entries = {}
        invoke(
            [client.executable, "plugin", "marketplace", "remove", MARKETPLACES["codex"], "--json"],
            dry_run=dry_run, runner=runner,
        )
        marketplace = None
    if marketplace is None:
        invoke(
            [client.executable, "plugin", "marketplace", "add", str(source), "--json"],
            dry_run=dry_run, runner=runner,
        )
    desired = desired_version or json.loads(
        (source / "codex" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    ).get("version")
    if entries.get(plugin_id, {}).get("version") != desired:
        if plugin_id in entries:
            invoke([client.executable, "plugin", "remove", plugin_id], dry_run=dry_run, runner=runner)
        invoke([client.executable, "plugin", "add", plugin_id, "--json"], dry_run=dry_run, runner=runner)


def install_copilot(
    client: Client, source: Path, dry_run: bool, runner: Runner, desired_version: str | None = None
) -> None:
    marketplaces = runner([client.executable, "plugin", "marketplace", "list"])
    require_success(marketplaces, "Copilot marketplace listing")
    listing = marketplaces.stdout + marketplaces.stderr
    registered = MARKETPLACES["copilot"] in listing
    if registered and not marketplace_source_matches(listing, source):
        invoke(
            [client.executable, "plugin", "marketplace", "remove", MARKETPLACES["copilot"], "--force"],
            dry_run=dry_run, runner=runner,
        )
        registered = False
    if not registered:
        invoke([client.executable, "plugin", "marketplace", "add", str(source)], dry_run=dry_run, runner=runner)
    listed = runner([client.executable, "plugin", "list"])
    require_success(listed, "Copilot plugin listing")
    installed = registered and "adr-kit" in (listed.stdout + listed.stderr).lower()
    if installed and desired_version and desired_version in (listed.stdout + listed.stderr):
        print(f"  no-op: adr-kit {desired_version} is already healthy")
        return
    command = (
        [client.executable, "plugin", "update", "adr-kit"]
        if installed
        else [client.executable, "plugin", "install", f"adr-kit@{MARKETPLACES['copilot']}"]
    )
    invoke(command, dry_run=dry_run, runner=runner)


INSTALLERS = {"claude": install_claude, "codex": install_codex, "copilot": install_copilot}


def validate_install(name: str, client: Client, runner: Runner) -> None:
    result = runner(
        [client.executable, "plugin", "list", "--json"]
        if name in {"claude", "codex"}
        else [client.executable, "plugin", "list"]
    )
    expected = f"adr-kit@{MARKETPLACES[name]}"
    if result.returncode or expected not in (result.stdout + result.stderr):
        raise RuntimeError(f"{name} validation failed: ADR Kit plugin not listed")
    if name in {"codex", "copilot"}:
        mcp = runner([client.executable, "mcp", "list"])
        if mcp.returncode or "adr-kit" not in (mcp.stdout + mcp.stderr):
            raise RuntimeError(f"{name} validation failed: adr-kit MCP server not listed")
    print(f"  validation: PASS ({name})")


def uninstall_client(client: Client, *, dry_run: bool, runner: Runner) -> None:
    name, marketplace = client.name, MARKETPLACES[client.name]
    plugin_id = f"adr-kit@{marketplace}"
    if name == "claude":
        commands = [
            [client.executable, "plugin", "uninstall", plugin_id, "--scope", "user"],
            [client.executable, "plugin", "marketplace", "remove", marketplace, "--scope", "user"],
        ]
    elif name == "codex":
        commands = [
            [client.executable, "plugin", "remove", plugin_id],
            [client.executable, "plugin", "marketplace", "remove", marketplace, "--json"],
        ]
    else:
        commands = [
            [client.executable, "plugin", "uninstall", "adr-kit"],
            [client.executable, "plugin", "marketplace", "remove", marketplace, "--force"],
        ]
    for command in commands:
        result = invoke(command, dry_run=dry_run, runner=runner)
        if not dry_run and result.returncode:
            raise RuntimeError(f"{name} uninstall failed")
