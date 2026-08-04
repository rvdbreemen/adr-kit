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


# ---------------------------------------------------------------------------
# The pre-commit hook has three states, not two (TASK-119)
# ---------------------------------------------------------------------------

FOREIGN_HOOK = "#!/bin/sh\n# husky\nexit 0\n"


def _project(tmp_path: Path, hook_body: str | None = None) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], capture_output=True, check=True)
    if hook_body is not None:
        (tmp_path / ".githooks").mkdir()
        (tmp_path / ".githooks" / "pre-commit").write_text(hook_body, encoding="utf-8")
    return tmp_path


def _setup(ws: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(SETUP), "--project-root", str(ws), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ws,
    )


def test_no_pre_commit_leaves_a_foreign_hook_byte_identical(tmp_path):
    """The flag reads as "do not install one" and used to mean "remove one".

    A project using husky, lefthook or a hand-written hook lost it to a flag
    whose name promises a non-act. Skipping was not expressible at all: every
    invocation either installed this kit's hook or removed whatever was there.
    """
    ws = _project(tmp_path, FOREIGN_HOOK)
    hook = ws / ".githooks" / "pre-commit"
    before = hook.read_bytes()

    result = _setup(ws, "--no-pre-commit")

    assert result.returncode == 0, result.stderr
    assert hook.read_bytes() == before


def test_no_pre_commit_leaves_our_own_hook_alone_too(tmp_path):
    """"Leave it alone" means leave it alone, whoever wrote it."""
    ws = _project(tmp_path)
    assert _setup(ws).returncode == 0
    hook = ws / ".githooks" / "pre-commit"
    ours = hook.read_bytes()

    result = _setup(ws, "--no-pre-commit")

    assert result.returncode == 0, result.stderr
    assert hook.read_bytes() == ours


def test_remove_pre_commit_removes_ours(tmp_path):
    ws = _project(tmp_path)
    assert _setup(ws).returncode == 0
    hook = ws / ".githooks" / "pre-commit"
    assert hook.exists()

    result = _setup(ws, "--remove-pre-commit")

    assert result.returncode == 0, result.stderr
    assert not hook.exists()


def test_remove_pre_commit_will_not_delete_someone_elses_hook(tmp_path):
    """Removal is bounded by the marker this kit writes into its own wrapper."""
    ws = _project(tmp_path, FOREIGN_HOOK)
    hook = ws / ".githooks" / "pre-commit"
    before = hook.read_bytes()

    result = _setup(ws, "--remove-pre-commit")

    assert result.returncode == 0, result.stderr
    assert hook.read_bytes() == before


def test_the_two_flags_contradict_each_other_and_are_refused(tmp_path):
    ws = _project(tmp_path)

    result = _setup(ws, "--no-pre-commit", "--remove-pre-commit")

    assert result.returncode != 0
    assert "pass one" in result.stderr


# ---------------------------------------------------------------------------
# The capability registry must not lag the manifest it governs (TASK-116)
# ---------------------------------------------------------------------------

def test_every_manifest_event_a_client_offers_is_in_the_registry():
    """`clients/capabilities.json` lists `hooks/manifest.json` under
    `ownership.canonical`, and carried neither of the two most recently added
    moments. A registry that lags the file it claims to govern is a registry
    that will be trusted and be wrong.
    """
    import json

    manifest = json.loads(
        (REPO_ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8")
    )
    capabilities = json.loads(
        (REPO_ROOT / "clients" / "capabilities.json").read_text(encoding="utf-8")
    )
    by_client = {
        entry["id"]: entry["event_mappings"] for entry in capabilities["clients"]
    }

    missing = []
    for event in manifest["events"]:
        for client_id, native in event["clients"].items():
            if native is None:
                continue  # the client does not offer this moment; R17 allows it
            mappings = by_client.get(client_id, {})
            if not any(
                mapping.get("native_event") == native
                and mapping.get("matcher", event["matcher"]) == event["matcher"]
                for mapping in mappings.values()
            ):
                missing.append((client_id, event["id"]))

    assert not missing, f"registry does not cover: {missing}"


# ---------------------------------------------------------------------------
# The support matrix derives its claims (TASK-115)
# ---------------------------------------------------------------------------

MATRIX = REPO_ROOT / "docs" / "client-support.md"


def test_the_lifecycle_table_is_not_hand_written():
    """It was three hardcoded strings, which is why it could be wrong.

    `Plan exit | supported (ExitPlanMode)` sat in this file through a release in
    which that event never fired, because nothing derived the row and so nothing
    could contradict it.
    """
    source = (REPO_ROOT / "scripts" / "client_certification.py").read_text(
        encoding="utf-8"
    )

    assert "LIFECYCLE_COLUMNS" in source
    assert "hooks/manifest.json" in source
    assert "| Claude Code CLI | Accepted global only |" not in source, (
        "a hardcoded lifecycle row is back"
    )


LABELS = {
    "claude-code-cli": "Claude Code CLI",
    "codex-cli": "Codex CLI",
    "github-copilot-cli": "GitHub Copilot CLI",
}


def _lifecycle_section() -> list[str]:
    """Only the lifecycle table.

    The document opens with a per-platform surface table whose rows begin with
    the same client labels, so an unscoped search reads the wrong one -- which
    is what these tests did on the first run.
    """
    lines = MATRIX.read_text(encoding="utf-8").splitlines()
    start = next(
        index for index, line in enumerate(lines)
        if line.startswith("## Lifecycle retrieval support")
    )
    return lines[start:]


def _cells(row: str) -> list[str]:
    """Split a Markdown row on unescaped pipes."""
    import re

    return [cell.strip() for cell in re.split(r"(?<!\\)\|", row)[1:-1]]


def test_every_cell_matches_the_manifest():
    """The document and the registry must not be able to disagree."""
    import json

    manifest = json.loads(
        (REPO_ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8")
    )
    events = {event["id"]: event for event in manifest["events"]}
    section = _lifecycle_section()

    for event_id in ("plan-exit", "pr-create", "post-tool-use", "session-start"):
        for client, native in events[event_id]["clients"].items():
            label = LABELS[client]
            row = next(
                line for line in section if line.startswith(f"| {label} |")
            )
            if native is None:
                assert "no native event" in row, (event_id, client, row)
            else:
                assert f"`{native}`" in row, (event_id, client, row)


def test_the_table_states_what_it_does_not_claim():
    """Registered is not the same as working, and the file has to say so.

    Conflating them is the exact failure this task exists to fix; separating
    them is what lets the table be derived at all.
    """
    text = MATRIX.read_text(encoding="utf-8")

    assert "does not say the wiring behind it works" in text
    assert "Evidence" in text, "the evidence class must stay visible"


def test_a_matcher_pipe_cannot_break_the_table():
    """`Edit|MultiEdit|Write` is a regex alternation inside a Markdown cell.

    Unescaped, its pipes end the cell and shift every column right -- a table
    that renders as nonsense while every underlying value is correct.
    """
    section = _lifecycle_section()
    header = next(line for line in section if line.startswith("| Client |"))
    rows = [line for line in section if line.startswith("| ") and "CLI |" in line]

    assert rows, "the lifecycle rows are missing"
    for row in rows:
        assert "Edit|MultiEdit" not in row, f"unescaped matcher pipe: {row}"
        assert len(_cells(row)) == len(_cells(header)), f"column count drifted: {row}"
