"""The workflows name an interpreter that exists (DEF-34).

`clients/workflows.json` told every Codex and Copilot skill, and every OpenCode
command, to run `python <plugin-root>/...`. macOS and most Linux distributions
ship python3 and no python, so each of those steps failed first. The procedures
now write `<python>`, and every generated skill says what it stands for, in
ADR-044's order. The OpenCode plugin substitutes the interpreter it resolved.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BARE = re.compile(r"(?<![\w<])python\s+<plugin-root>")


def test_no_workflow_runs_a_bare_python():
    text = (ROOT / "clients" / "workflows.json").read_text(encoding="utf-8")

    assert not BARE.search(text)


@pytest.mark.parametrize("tree", ["codex", "copilot"])
def test_every_generated_skill_that_runs_python_says_which(tree):
    for skill in sorted((ROOT / tree / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        assert not BARE.search(text), skill
        if "<python>" in text:
            assert "`python3`, `python`" in text and "3.10" in text, skill
