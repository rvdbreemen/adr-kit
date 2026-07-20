#!/usr/bin/env python3
"""Install ADR Kit's generated guide, managed pointers, and pre-commit gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adr_settings import SettingsError, resolve_settings
from project_setup import (
    SetupError,
    apply_changes,
    collect_changes,
    render_diff,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adr-kit:setup")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--clients",
        default="claude,codex,copilot",
        help="Comma-separated selected native clients.",
    )
    parser.add_argument("--global-settings", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-pre-commit", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.project_root.resolve()
    clients = [item.strip() for item in args.clients.split(",") if item.strip()]
    try:
        effective = resolve_settings(root, global_path=args.global_settings)
        clients = [
            client
            for client in clients
            if effective["values"]["clients"][client]["enabled"] is not False
        ]
        pre_commit = (
            effective["values"]["pre_commit"]["enabled"]
            and not args.no_pre_commit
        )
        changes, configure_hooks_path = collect_changes(
            root,
            args.plugin_root.resolve(),
            clients,
            pre_commit_enabled=pre_commit,
        )
        diff = render_diff(changes, root)
        if not args.dry_run:
            apply_changes(
                root,
                changes,
                configure_hooks_path=configure_hooks_path,
            )
    except (KeyError, SettingsError, SetupError) as exc:
        print(f"adr-kit:setup: {exc}", file=sys.stderr)
        return 2

    payload = {
        "dry_run": args.dry_run,
        "clients": clients,
        "pre_commit_enabled": pre_commit,
        "configure_hooks_path": configure_hooks_path,
        "changes": [
            {"path": str(change.path.relative_to(root)), "action": change.action}
            for change in changes
        ],
        "diff": diff,
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for change in payload["changes"]:
            print(f"{change['action']}: {change['path']}")
        if not payload["changes"]:
            print("ADR Kit project setup is already current.")
        if args.dry_run and diff:
            print(diff, end="" if diff.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
