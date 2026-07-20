"""Codex hook output using hook-specific model context."""

from __future__ import annotations


def render(event: str, context: str, kind: str) -> dict:
    if not context:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }
