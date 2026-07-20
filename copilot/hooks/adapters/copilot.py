"""Copilot CLI hook output with an honest post-edit backstop."""

from __future__ import annotations


def render(event: str, context: str, kind: str) -> dict:
    if not context:
        return {}
    if kind == "pre-edit":
        return {}
    return {"additionalContext": context}
