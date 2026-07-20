"""Native hook response adapters for ADR Kit's three certified clients."""

from __future__ import annotations

from .claude import render as render_claude
from .codex import render as render_codex
from .copilot import render as render_copilot

ADAPTERS = {
    "claude-code-cli": render_claude,
    "codex-cli": render_codex,
    "github-copilot-cli": render_copilot,
}
