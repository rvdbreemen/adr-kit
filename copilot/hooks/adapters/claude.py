"""Claude Code hook output."""

from __future__ import annotations


def render(event: str, context: str, kind: str) -> dict:
    if not context:
        return {}
    if kind == "pr-guard-deny":
        # The one hook that may interfere. A branch that violates an Accepted
        # ADR should be fixed before it becomes a proposal, and denying the
        # tool call is the only way to say so at this moment. Every other
        # outcome of the guard allows the command through.
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "permissionDecision": "deny",
                "permissionDecisionReason": context,
            },
        }
    return {
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        },
    }
