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
        context, kind = evaluate(envelope)
        response = ADAPTERS[args.client](envelope.event, context, kind)
        if response:
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
    except BaseException:
        # Optional hooks can never replace deterministic pre-commit enforcement.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
