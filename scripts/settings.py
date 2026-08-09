#!/usr/bin/env python3
"""CLI for ADR Kit global defaults and per-project overrides."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adr_settings import (
    SettingsError,
    parse_cli_value,
    resolve_settings,
    write_setting,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adr-kit:settings")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--global-settings", type=Path)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("show")
    setter = subparsers.add_parser("set")
    setter.add_argument("key")
    setter.add_argument("value")
    setter.add_argument("--scope", choices=("global", "project"), default="project")
    unsetter = subparsers.add_parser("unset")
    unsetter.add_argument("key")
    unsetter.add_argument(
        "--scope", choices=("global", "project"), default="project"
    )
    return parser


def _render_human(payload: dict) -> str:
    lines = ["ADR Kit effective settings:"]
    for entry in payload["entries"]:
        value = json.dumps(entry["value"], ensure_ascii=False)
        lines.append(f"  {entry['key']} = {value} ({entry['source']})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = args.command or "show"
    root = args.project_root.resolve()
    try:
        if command == "set":
            write_setting(
                root,
                args.scope,
                args.key,
                parse_cli_value(args.value),
                global_path=args.global_settings,
            )
        elif command == "unset":
            write_setting(
                root,
                args.scope,
                args.key,
                unset=True,
                global_path=args.global_settings,
            )
        resolved = resolve_settings(root, global_path=args.global_settings)
    except SettingsError as exc:
        print(f"adr-kit:settings: {exc}", file=sys.stderr)
        return 2

    payload = dict(resolved)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_human(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
