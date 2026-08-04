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
    if verdict.get("decision") == "deny":
        return verdict["reason"], "pr-guard-deny"
    if verdict.get("checked") is False:
        # The guard could not do its job, and silence here is the whole defect:
        # a branch nobody managed to check looks exactly like a clean one. Say
        # so and let the command through -- an unchecked branch is not a
        # violation, and blocking on our own failure would punish the wrong
        # thing.
        return (
            "ADR check skipped before this pull request: "
            f"{verdict.get('reason', 'unknown reason')}. "
            "The commit hook and CI remain the enforcing gates.",
            "pr-guard-unchecked",
        )
    # A clean branch says nothing. An "all clear" on every pull request is noise
    # that teaches people to skim past the one that matters.
    return None


def _emit(response) -> None:
    """Write the response as UTF-8 bytes, past the platform's text layer.

    `print()` encodes through `sys.stdout`, which is cp1252 on a default Windows
    console. An ADR title carrying an em dash came out as byte 0x97 — not valid
    UTF-8, so a client decoding the frame as UTF-8 gets nothing usable; a title
    carrying anything cp1252 cannot represent raised `UnicodeEncodeError`, which
    the fail-open `except BaseException` swallowed into zero bytes and exit 0.
    Silent, total loss of the injection, on the platform `clients/capabilities.json`
    marks release-required.

    Writing bytes removes the failure rather than handling it: there is no text
    layer left to encode wrongly, so no encoding error can reach the fail-open
    catch and hide there. `bin/adr-mcp` reconfigures its stdout for the same
    reason (TASK-69); this is the same defect one process over.
    """
    frame = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
    out = getattr(sys.stdout, "buffer", None)
    if out is not None:
        out.write(frame.encode("utf-8") + b"\n")
        out.flush()
    else:
        # Fallback for environments without a binary stdout buffer (e.g. redirected stdout)
        sys.stdout.write(frame + "\n")
        sys.stdout.flush()


#: Events whose declared budget can absorb an embedding round trip. ADR-020
#: draws the line here: `session-start` and `user-prompt-submit` carry 500 ms
#: while the edit-tier events carry 100 ms, and a round trip does not fit
#: 100 ms at any realistic ADR count. Widening this set is a decision.
EMBEDDING_EVENTS = {"UserPromptSubmit"}


def _embedder_for(envelope):
    """Supply a query embedder, but only where the budget allows one.

    Built here rather than inside `adr_hook_core` on purpose: that module must
    stay unable to reach a model or the network, and this entrypoint is already
    the one hook-path file allowed to reach out -- it spawns `adr-judge` for the
    pull-request guard.
    """
    if envelope.event not in EMBEDDING_EVENTS:
        return None
    try:
        from adr_embed_query import embedder_for
    except ImportError:
        return None
    return embedder_for(envelope.workspace / "docs" / "adr")


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
        context, kind = _pr_guard(envelope) or evaluate(
            envelope, _embedder_for(envelope)
        )
        response = ADAPTERS[args.client](envelope.event, context, kind)
        if response:
            _emit(response)
    except BaseException:
        # Optional hooks can never replace deterministic pre-commit enforcement.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
