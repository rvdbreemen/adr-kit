#!/usr/bin/env python3
"""Fail-open command entrypoint for ADR Kit lifecycle hooks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from adapters import ADAPTERS
from adr_hook_core import duplicate_event, evaluate, parse_payload
from adr_pr_guard import judge_branch, looks_like_pr_create


def _pr_guard(envelope) -> tuple[str, str] | None:
    """Judge the branch when the agent is about to open a pull request.

    Returns None when this is not that moment, so the normal injection path
    runs untouched. Kept in the entrypoint rather than in adr_hook_core because
    it spawns adr-judge, and the retrieval core is asserted to import nothing
    that can reach a model or the network.
    """
    if envelope.event != "PreToolUse":
        return None
    tool = (envelope.tool_name or "").lower().replace("_", "")
    if tool not in {"bash", "shell", "run", "terminal"}:
        return None
    command = envelope.tool_input.get("command")
    if not isinstance(command, str) or not looks_like_pr_create(command):
        return None
    verdict = judge_branch(
        envelope.workspace,
        envelope.workspace / "docs" / "adr",
        Path(__file__).resolve().parent.parent / "bin" / "adr-judge",
    )
    if verdict.get("decision") != "deny":
        return None
    return verdict["reason"], "pr-guard-deny"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--client", required=True, choices=tuple(ADAPTERS))
    parser.add_argument("--event")
    args, _unknown = parser.parse_known_args(argv)
    try:
        envelope = parse_payload(
            sys.stdin.buffer.read(64 * 1024 + 1), args.client, args.event
        )
        if envelope is None:
            return 0
        if duplicate_event(envelope):
            return 0
        context, kind = _pr_guard(envelope) or evaluate(envelope)
        response = ADAPTERS[args.client](envelope.event, context, kind)
        if response:
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
    except BaseException:
        # Optional hooks can never replace deterministic pre-commit enforcement.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
