#!/usr/bin/env python3
"""Detect supported agent CLIs and install ADR Kit through each native plugin API."""

from __future__ import annotations

import argparse
import json
import os
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


def detect_client(
    name: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = _run,
) -> Client | None:
    executable = which(name)
    if not executable:
        return None
    result = runner([executable, "--version"])
    version = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or VERSION_MARKERS[name].lower() not in version.lower():
        return None
    return Client(name, str(Path(executable).resolve()), version.splitlines()[0])


def detect_clients(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = _run,
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


def _invoke(
    command: Sequence[str],
    *,
    dry_run: bool,
    runner: Runner,
) -> subprocess.CompletedProcess[str]:
    printable = subprocess.list2cmdline(list(command))
    print(f"  $ {printable}")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    result = runner(command)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {printable}\n{detail}")
    return result


def install_claude(client: Client, source: Path, dry_run: bool, runner: Runner) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    names = {
        item.get("name")
        for item in (_json_output(listed) or [])
        if isinstance(item, dict)
    }
    if MARKETPLACES["claude"] not in names:
        _invoke(
            [client.executable, "plugin", "marketplace", "add", str(source)],
            dry_run=dry_run,
            runner=runner,
        )
    installed = runner([client.executable, "plugin", "list", "--json"])
    payload = _json_output(installed)
    text = json.dumps(payload or {})
    plugin_id = f"adr-kit@{MARKETPLACES['claude']}"
    action = "update" if plugin_id in text else "install"
    command = [client.executable, "plugin", action, plugin_id]
    if action == "install":
        command += ["--scope", "user"]
    _invoke(command, dry_run=dry_run, runner=runner)


def install_codex(client: Client, source: Path, dry_run: bool, runner: Runner) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    payload = _json_output(listed)
    names = {
        item.get("name")
        for item in (payload or {}).get("marketplaces", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else set()
    if MARKETPLACES["codex"] not in names:
        _invoke(
            [client.executable, "plugin", "marketplace", "add", str(source), "--json"],
            dry_run=dry_run,
            runner=runner,
        )
    installed = runner([client.executable, "plugin", "list", "--json"])
    payload = _json_output(installed)
    plugin_id = f"adr-kit@{MARKETPLACES['codex']}"
    installed_entries = {
        item.get("pluginId"): item
        for item in (payload or {}).get("installed", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}
    desired = json.loads(
        (source / "codex" / ".codex-plugin" / "plugin.json").read_text(
            encoding="utf-8"
        )
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


def install_copilot(client: Client, source: Path, dry_run: bool, runner: Runner) -> None:
    marketplaces = runner([client.executable, "plugin", "marketplace", "list"])
    if MARKETPLACES["copilot"] not in (marketplaces.stdout + marketplaces.stderr):
        _invoke(
            [client.executable, "plugin", "marketplace", "add", str(source)],
            dry_run=dry_run,
            runner=runner,
        )
    listed = runner([client.executable, "plugin", "list"])
    installed = "adr-kit" in (listed.stdout + listed.stderr).lower()
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

    for name in selected:
        print(f"Installing ADR Kit for {name}:")
        INSTALLERS[name](detected[name], source, args.dry_run, _run)
        if not args.dry_run and not args.skip_validation:
            validate_install(name, detected[name])
    print("ADR Kit install complete for: " + ", ".join(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
