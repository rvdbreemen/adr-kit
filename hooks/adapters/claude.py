"""Claude Code hook output."""

from __future__ import annotations


def render(event: str, context: str, kind: str) -> dict:
    if not context:
        return {}
    return {
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        },
    }
