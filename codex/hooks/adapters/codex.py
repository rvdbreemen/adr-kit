"""Codex hook output using hook-specific model context."""

from __future__ import annotations


def render(event: str, context: str, kind: str) -> dict:
    if not context:
        return {}
    if kind == "pr-guard-deny":
        # Codex gets the verdict, not the gate. This adapter has no permission
        # decision to return, so rendering the deny as plain context would make
        # a violation read exactly like an ordinary injection - the cost of the
        # judge with none of its effect, and a user who believes the branch was
        # checked and cleared. Say what it is instead, and name the gate that
        # does hold. See the `codex-pr-guard-advisory-only` degradation.
        context = (
            "ADR violation on this branch. This client cannot block the tool "
            "call, so the pull request is not stopped here - the pre-commit "
            "hook and CI remain the enforcing gates.\n\n" + context
        )
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }
