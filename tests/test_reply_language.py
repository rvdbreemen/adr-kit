"""Every skill and the generator agent carry the same reply-language rule (TASK-238).

The rule sets the language of the conversation only. ADR file content keeps the
project's documentation language, which the generator agent governs separately.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from client_generation_model import REPLY_RULE  # noqa: E402

# Canonical Claude Code skills, the generator agent, and the generated Codex and
# Copilot skills, which come from clients/workflows.json, not from skills/.
SURFACES = (
    sorted((REPO_ROOT / "skills").glob("*/SKILL.md"))
    + [REPO_ROOT / "agents" / "adr-generator.md"]
    + sorted((REPO_ROOT / "codex" / "skills").glob("*/SKILL.md"))
    + sorted((REPO_ROOT / "copilot" / "skills").glob("*/SKILL.md"))
)


def _first_paragraph_after_h1(text: str) -> str:
    match = re.search(r"^# [^\n]*\n\n([^\n]*)", text.replace("\r\n", "\n"), re.M)
    return match.group(1) if match else ""


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_reply_rule_sits_directly_under_the_heading(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert _first_paragraph_after_h1(text) == REPLY_RULE


def test_every_client_surface_is_collected() -> None:
    for root in ("skills", "codex/skills", "copilot/skills"):
        assert list((REPO_ROOT / root).glob("*/SKILL.md")), root


def test_document_language_rule_is_unchanged() -> None:
    agent = (REPO_ROOT / "agents" / "adr-generator.md").read_text(encoding="utf-8")
    assert (
        "**English** unless the project explicitly uses another language for documentation."
        in agent
    )
