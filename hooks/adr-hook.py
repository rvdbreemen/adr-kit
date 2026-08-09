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
    bin_dir = Path(__file__).resolve().parent.parent / "bin"
    verdict = judge_branch(
        envelope.workspace,
        envelope.workspace / "docs" / "adr",
        bin_dir / "adr-judge",
        # R2 asks two questions at this moment: does this violate an accepted
        # decision, and does it contain one nobody recorded. Only the first was
        # ever answered here (ADR-024). The second joins it rather than getting
        # its own moment, because this one is already intercepted and the user
        # is already waiting.
        suggest=bin_dir / "adr-suggest",
    )
    nudge = verdict.get("nudge") or ""
    if verdict.get("decision") == "deny":
        # A violation denies. The nudge rides along because the branch that
        # broke a rule is also the one most likely to be making a decision, but
        # it never contributes to the denial.
        reason = verdict["reason"]
        joined = "\n\n".join(part for part in (reason, nudge) if part)
        return joined, "pr-guard-deny"
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
    # that teaches people to skim past the one that matters. A branch carrying an
    # unrecorded decision is not clean in the sense that matters, so the nudge
    # speaks -- advisory, and on its own it can never block the tool call.
    if nudge:
        return nudge, "pr-guard-suggest"
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
            _emit(response)
    except BaseException:
        # Optional hooks can never replace deterministic pre-commit enforcement.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
