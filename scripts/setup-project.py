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


CLIENT_ALIASES = {
    "claude-code-cli": "claude",
    "codex-cli": "codex",
    "github-copilot-cli": "copilot",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adr-kit:setup")
    parser.add_argument(
        "workspace",
        nargs="?",
        type=Path,
        default=None,
        help="Project to set up. Equivalent to --project-root; accepted "
        "positionally because that is the form the setup skills documented.",
    )
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--clients",
        default=None,
        help="Comma-separated selected native clients: claude, codex, copilot. "
        "Full client ids such as codex-cli are accepted and normalised.",
    )
    parser.add_argument(
        "--client",
        default=None,
        help="Alias for --clients, singular. Accepts a short name or a full "
        "client id.",
    )
    parser.add_argument("--global-settings", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-pre-commit", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def _selected_clients(raw: str | None) -> list[str]:
    """Normalise whatever the caller wrote into the short names settings use.

    Both spellings reach this command from real callers: the settings surface
    and this script's own default use `claude`/`codex`/`copilot`, while every
    skill and workflow that names a client elsewhere uses the full ids from
    `clients/capabilities.json`. Accepting one and failing on the other with a
    `KeyError` -- which is what shipped -- means the documented invocation dies
    on a dictionary lookup after argparse has already accepted it.
    """
    if raw is None:
        raw = "claude,codex,copilot"
    selected = []
    for item in raw.split(","):
        name = item.strip()
        if not name:
            continue
        name = CLIENT_ALIASES.get(name, name)
        if name not in ("claude", "codex", "copilot"):
            raise SystemExit(
                f"adr-kit:setup: unknown client {item.strip()!r}; expected one "
                f"of claude, codex, copilot (or the full ids "
                f"{', '.join(sorted(CLIENT_ALIASES))})"
            )
        if name not in selected:
            selected.append(name)
    return selected


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.client and args.clients:
        raise SystemExit(
            "adr-kit:setup: pass --client or --clients, not both; they mean "
            "the same thing"
        )
    if args.workspace and args.project_root and args.workspace != args.project_root:
        raise SystemExit(
            "adr-kit:setup: the positional workspace and --project-root "
            "disagree; pass one"
        )
    root = (args.project_root or args.workspace or Path.cwd()).resolve()
    clients = _selected_clients(args.client or args.clients)
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
