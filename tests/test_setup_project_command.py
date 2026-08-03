"""The command the setup skills document has to be a command that runs.

`clients/workflows.json` told every generated client to run

    python <plugin-root>/scripts/setup-project.py --client <client-id> <workspace>

and that invocation could not work. The script defined no positional argument,
so the workspace was `unrecognized arguments`; the flag is `--clients`, plural,
taking `claude`/`codex`/`copilot`, so `--client codex-cli` survived argparse
prefix matching and then died on a dictionary lookup with exit 2. The working
form -- `--clients codex --project-root <path>` -- appeared in no skill, no
template and no document.

The consequence was not cosmetic. A Codex or Copilot user following the
documented path got no ADR instructions in the file their agent reads, and on
Copilot, where there is no PreToolUse tier by design, nothing else tells the
agent either.

This module runs what the documentation says, rather than asserting that the
documentation contains a string.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SETUP = REPO_ROOT / "scripts" / "setup-project.py"

SKILLS = {
    "claude-code-cli": REPO_ROOT / "skills" / "setup" / "SKILL.md",
    "codex-cli": REPO_ROOT / "codex" / "skills" / "setup" / "SKILL.md",
    "github-copilot-cli": REPO_ROOT / "copilot" / "skills" / "setup" / "SKILL.md",
}

DOCUMENTED = re.compile(
    r"python\s+<plugin-root>/scripts/setup-project\.py\s+(?P<args>[^`\n]+)"
)


def _run(*args: str, cwd: Path):
    return subprocess.run(
        [sys.executable, str(SETUP), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd,
    )


@pytest.mark.parametrize("client", ["codex-cli", "github-copilot-cli"])
def test_the_command_each_skill_documents_actually_runs(client, tmp_path):
    """Substitute the placeholders and execute it. No string assertions."""
    skill = SKILLS[client]
    if not skill.is_file():
        pytest.skip(f"{client} ships no setup skill")
    match = DOCUMENTED.search(skill.read_text(encoding="utf-8"))
    assert match, f"{client} setup skill no longer documents the command"

    argv = (
        match.group("args")
        .replace("<client-id>", client)
        .replace("<workspace>", str(tmp_path))
        .split("`")[0]
        .split()
    )
    result = _run(*argv, "--dry-run", cwd=tmp_path)

    assert result.returncode == 0, (
        f"the command {client}'s setup skill documents exits "
        f"{result.returncode}:\n{result.stderr}"
    )


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--client", "codex-cli", "{ws}"], id="documented-positional"),
        pytest.param(["--clients", "codex", "--project-root", "{ws}"], id="long-form"),
        pytest.param(["{ws}"], id="positional-only"),
        pytest.param(["--project-root", "{ws}"], id="flag-only"),
        pytest.param(["--client", "codex", "--project-root", "{ws}"], id="short-name"),
    ],
)
def test_every_spelling_a_caller_might_reasonably_use(argv, tmp_path):
    """Both vocabularies reach this command from real callers.

    The settings surface uses `claude`/`codex`/`copilot`; every skill and
    workflow that names a client elsewhere uses the full ids from
    `clients/capabilities.json`. Accepting one and dying on the other is what
    shipped.
    """
    resolved = [item.replace("{ws}", str(tmp_path)) for item in argv]

    result = _run(*resolved, "--dry-run", cwd=tmp_path)

    assert result.returncode == 0, result.stderr


def test_an_unknown_client_is_refused_by_name(tmp_path):
    """A dictionary lookup failing with a traceback is not an error message."""
    result = _run("--client", "emacs", str(tmp_path), "--dry-run", cwd=tmp_path)

    assert result.returncode != 0
    assert "emacs" in result.stderr
    assert "claude, codex, copilot" in result.stderr


def test_contradicting_the_workspace_twice_is_refused(tmp_path):
    other = tmp_path / "elsewhere"
    other.mkdir()

    result = _run(
        str(tmp_path), "--project-root", str(other), "--dry-run", cwd=tmp_path
    )

    assert result.returncode != 0
    assert "disagree" in result.stderr


def test_a_fresh_project_ends_with_instructions_where_the_agent_reads_them(tmp_path):
    """The user-visible outcome, not the mechanism.

    On Copilot this is the whole story: with no PreToolUse tier, the instruction
    file is the only thing that tells the agent the ADRs exist.
    """
    result = _run("--client", "codex-cli", "--project-root", str(tmp_path), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    agents = tmp_path / "AGENTS.md"
    assert agents.is_file(), "AGENTS.md is the file a Codex session reads"
    assert "ADR" in agents.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# One layout, and R16's detection on every client
# ---------------------------------------------------------------------------

LEGACY_MARKERS = ("<!-- ADR-KIT STUB START -->", ".claude/adr-kit-guide.md")


@pytest.mark.parametrize("skill", ["setup", "init"])
def test_the_claude_skills_no_longer_hand_write_an_older_layout(skill):
    """Prose describing a layout is prose that drifts from the writer.

    `skills/setup/SKILL.md` and `skills/init/SKILL.md` each carried a full
    `<!-- ADR-KIT STUB START -->` block and a `.claude/adr-kit-guide.md` write --
    exactly the footprint `scripts/project_setup.py` classifies as `LEGACY_GUIDES`
    and migrates away from -- while the Codex and Copilot skills delegated to
    `scripts/setup-project.py`. Neither mentioned `AGENTS.md`, so a Claude-set-up
    project and a Codex-set-up project ended in different shapes.
    """
    text = (REPO_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")

    assert "setup-project.py" in text, f"{skill} does not delegate to the writer"
    for marker in LEGACY_MARKERS:
        assert marker not in text, (
            f"{skill} still hand-writes {marker}, which the writer has owned "
            f"since the layout changed"
        )


@pytest.mark.parametrize(
    "skill_path",
    [
        REPO_ROOT / "skills" / "setup" / "SKILL.md",
        REPO_ROOT / "codex" / "skills" / "setup" / "SKILL.md",
        REPO_ROOT / "copilot" / "skills" / "setup" / "SKILL.md",
    ],
    ids=["claude", "codex", "copilot"],
)
def test_every_client_setup_path_asks_about_the_embedding_runtime(skill_path):
    """spec R16: setup must find out, and act on the answer.

    It reached two callers, both Claude skills, while the mirrored
    `bin/adr-settings` carried the flag on every client. On two of three clients
    setup never asked, so the user met the gap when retrieval quietly fell back.
    """
    assert "--check-embedding" in skill_path.read_text(encoding="utf-8")
