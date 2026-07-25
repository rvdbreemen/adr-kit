#!/usr/bin/env python3
"""Plan and converge ADR Kit for detected Claude, Codex, and Copilot CLIs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent
for import_root in (ROOT, ROOT / "scripts"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from adr_settings import SettingsError, resolve_settings
from project_setup import apply_changes, plan_uninstall
from clients.installer.contracts import CLIENT_IDS
from clients.installer.detection import (
    Client,
    detect_client,
    detect_clients,
    detailed_detection,
    sha256_file,
)
from clients.installer.native import (
    INSTALLERS,
    MARKETPLACES,
    claude_marketplace_source_matches,
    display_command,
    install_claude,
    install_codex,
    install_copilot,
    marketplace_source_matches,
    uninstall_client,
    validate_install as _validate_install,
)
from clients.installer.payload import (
    MIN_PYTHON,
    PREPARED_MARKER,
    REQUIRED_INSTALL_FILES,
    default_install_root,
    prepare_install_source,
    payload_digest,
    remove_owned_payloads,
    validate_prepared_hooks,
    validate_prepared_mcp,
    validate_python as _validate_python,
    validate_source,
)
from clients.installer.planning import build_plan, render_plan
from clients.installer.transaction import run_transaction
from clients.installer.updates import record_update_state, update_decision
SUPPORTED = CLIENT_IDS
Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
def _display_command(command: Sequence[str], system: str | None = None) -> str:
    return display_command(command, system)


def validate_python(executable: str, runner: Runner = _run) -> str:
    return _validate_python(executable, runner)


def validate_install(name: str, client: Client, runner: Runner = _run) -> None:
    _validate_install(name, client, runner)


def report_migration_plan(source: Path, project_root: Path, runner: Runner = _run) -> None:
    adr_dir = project_root / "docs" / "adr"
    if not adr_dir.is_dir():
        print(f"ADR format scan: no ADR directory at {adr_dir}; nothing to inspect.")
        return
    command = [sys.executable, str(source / "bin" / "adr-migrate"), "--plan", str(adr_dir)]
    print(f"ADR format scan (read-only): {adr_dir}")
    result = runner(command)
    if result.returncode:
        print(
            "  warning: format discovery could not complete; installation remains valid. "
            + (result.stderr or result.stdout).strip(),
            file=sys.stderr,
        )
    elif result.stdout.strip():
        for line in result.stdout.splitlines():
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
    installed, failures = [], []
    for name in selected:
        print(f"Installing ADR Kit for {name}:")
        try:
            def apply() -> None:
                INSTALLERS[name](
                    detected[name], source, dry_run, runner, desired_version=version
                )

            def validate() -> None:
                if not dry_run and not skip_validation:
                    validate_install(name, detected[name], runner)

            def rollback() -> None:
                previous = source.with_name(source.name + ".old")
                if not previous.is_dir():
                    return
                marker = json.loads((previous / PREPARED_MARKER).read_text(encoding="utf-8"))
                INSTALLERS[name](
                    detected[name], previous, False, runner,
                    desired_version=marker.get("version"),
                )

            if dry_run:
                apply()
            else:
                run_transaction(
                    name, state_root=source.parent.parent / "state",
                    apply=apply, validate=validate, rollback=rollback,
                )
            installed.append(name)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            failures.append((name, str(exc)))
            print(f"  FAILED ({name}): {exc}", file=sys.stderr)
    return installed, failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install ADR Kit for detected Claude Code, Codex, and Copilot CLIs."
    )
    parser.add_argument("--clients", "--agents", default="auto")
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--install-root", type=Path)
    parser.add_argument("--global-settings", type=Path)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--detect-only", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser, args = _parser(), _parser().parse_args(argv)
    source, project_root = args.source.expanduser().resolve(), args.project_root.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    try:
        version = validate_source(source)
        python_executable = validate_python(args.python)
        resolved = resolve_settings(project_root, global_path=args.global_settings)
    except (RuntimeError, SettingsError) as exc:
        parser.error(str(exc))
    detected = detect_clients()
    update = update_decision(resolved["values"], version)
    if resolved["values"]["update"]["policy"] == "pinned":
        pinned = resolved["values"]["update"]["pinned_version"]
        if pinned != version:
            parser.error(f"local payload {version} does not match pinned version {pinned!r}")
    install_root = args.install_root.expanduser().resolve() if args.install_root else default_install_root()
    detailed = detailed_detection(
        detected, install_root=install_root, effective_settings=resolved["values"]
    )
    identity = {
        "version": version,
        "source": str(source),
        "source_sha256": sha256_file(source / ".claude-plugin" / "plugin.json"),
        "payload_sha256": payload_digest(source),
        "update": update,
    }
    if args.detect_only:
        payload = {
            "schema_version": 1, "adr_kit": identity,
            "clients": {
                name: detailed[name].as_dict() if name in detailed else None
                for name in SUPPORTED
            },
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for name in SUPPORTED:
                state = detailed.get(name)
                print(f"{name}: {state.executable} ({state.version})" if state else f"{name}: not detected")
        return 0
    try:
        selected = parse_selection(args.clients, detected)
    except ValueError as exc:
        parser.error(str(exc))
    selected = [
        name for name in selected
        if resolved["values"]["clients"][name]["enabled"] is not False
    ]
    plan = build_plan(
        detailed, source=source, version=version,
        source_sha256=identity["source_sha256"] or "",
        effective_settings=resolved["values"],
        requested=tuple(selected) if args.clients != "auto" else None,
        remove=args.uninstall,
    )
    print(render_plan(plan, format=args.format))
    if args.plan:
        return 0
    if plan.requires_confirmation and not args.yes:
        parser.error("breaking-version migration requires --yes after reviewing --plan")
    if not selected:
        print("No supported CLI detected; nothing installed.", file=sys.stderr)
        return 2
    if args.uninstall:
        failures = []
        for name in selected:
            try:
                uninstall_client(detected[name], dry_run=args.dry_run, runner=_run)
            except RuntimeError as exc:
                failures.append((name, str(exc)))
        if not failures and not args.dry_run:
            remove_owned_payloads(install_root)
            apply_changes(
                project_root, plan_uninstall(project_root, selected),
                configure_hooks_path=False,
            )
        return 1 if failures else 0
    try:
        prepared = prepare_install_source(
            source, version=version, python_executable=python_executable,
            install_root=install_root, dry_run=args.dry_run,
        )
        if not args.dry_run:
            validate_prepared_mcp(prepared, python_executable)
            validate_prepared_hooks(prepared)
    except RuntimeError as exc:
        parser.error(str(exc))
    installed, failures = install_selected_clients(
        selected, detected, prepared, version=version, dry_run=args.dry_run,
        skip_validation=args.skip_validation,
    )
    report_migration_plan(source, project_root)
    if installed:
        for name in installed:
            record_update_state(
                install_root.parent, name, version=version, trigger=update["trigger"]
            )
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
