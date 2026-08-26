"""Five relevant ADRs at the start of work, and both hooks agreeing (spec R5).

Two defects the audit found: the limit was 3 where the spec asks for 5, and the
documented knob `context.default_limit` never reached the hook, so a user who
set 5 still got 3. A third one mattered more than either: the Python and Rust
hooks each carried their own constant, so what an agent was told depended on the
platform - and nobody could see it happen.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _core():
    sys.path.insert(0, str(REPO_ROOT / "bin"))
    name = "adr_hook_core_limit"
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "hooks" / "adr_hook_core.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


core = _core()


def test_the_default_is_five():
    assert core.DEFAULT_MAX_RESULTS == 5


def test_the_configured_limit_reaches_the_hook(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"context": {"default_limit": 7}}), encoding="utf-8"
    )

    assert core._configured_limit(tmp_path) == 7


def test_an_absent_config_uses_the_default(tmp_path):
    assert core._configured_limit(tmp_path) == core.DEFAULT_MAX_RESULTS


def test_a_corrupt_config_uses_the_default(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text("{not json", encoding="utf-8")

    assert core._configured_limit(tmp_path) == core.DEFAULT_MAX_RESULTS


def test_an_absurd_limit_is_bounded_rather_than_obeyed(tmp_path):
    """A typo must not turn one prompt into a context flood."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"context": {"default_limit": 5000}}), encoding="utf-8"
    )

    assert core._configured_limit(tmp_path) == core.DEFAULT_MAX_RESULTS


# ---------------------------------------------------------------------------
# Candidate phrasing: retrieval narrows, the model chooses (spec B4, R5)
# ---------------------------------------------------------------------------

CANDIDATE_HEADINGS = (
    "Accepted ADR candidates for this prompt (retrieval-ranked):",
    "Proposed ADR candidates for this prompt (advisory):",
)
SELECTION_INSTRUCTION = (
    "These are retrieval candidates, not confirmed matches: apply "
    "the ones that actually govern this work and ignore the rest."
)


def test_prompt_injection_presents_candidates_and_instructs_selection(tmp_path):
    """The injected block hands the final relevance call to the session model.

    The old heading asserted relevance ("relevant to this prompt"), which read
    as a settled answer. R5 wants retrieval to narrow and the model to choose,
    so the block must present candidates and say what to do with them.
    """
    workspace = tmp_path
    adr_dir = workspace / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-pick-a-database.md").write_text(
        "---\n"
        'id: "ADR-001"\n'
        'title: "Pick a database"\n'
        'status: "Accepted"\n'
        "---\n\n# ADR-001 Pick a database\n\n## Status\n\nAccepted, 2026-01-01.\n\n"
        "## Decision Outcome\n\nChosen option: use SQLite for the importer "
        "database, because it needs no server.\n",
        encoding="utf-8",
    )
    # _query asks the shared engine with a strict index; a hand-written index
    # would be stale by definition (same reasoning as the dispatch-matrix
    # fixture), so generate the real one.
    import subprocess
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-index"), str(adr_dir)],
        capture_output=True, check=True,
    )
    envelope = core.Envelope(
        client="claude-code-cli",
        client_version=None,
        event="UserPromptSubmit",
        session_id=None,
        agent_id=None,
        workspace=workspace,
        tool_name=None,
        tool_input={},
        prompt="which database should the importer use?",
        parent_context=None,
    )
    context, kind = core._evaluate_context(envelope)
    assert kind == "prompt"
    assert CANDIDATE_HEADINGS[0] in context
    assert "relevant to this prompt" not in context
    assert SELECTION_INSTRUCTION in context
    # The instruction comes after the candidate list, where a reader lands.
    assert context.index(SELECTION_INSTRUCTION) > context.index(CANDIDATE_HEADINGS[0])


def test_the_selection_instruction_survives_truncation():
    """TASK-157 finding 4: append-then-slice cut the instruction exactly when
    the candidate set was biggest. The instruction's length is reserved and the
    candidates are truncated instead, keeping the total inside the budget."""
    fat = ["X" * 3000, "Y" * 3000]           # far over MAX_CONTEXT_CHARS together
    context = core._prompt_candidates_context(fat)
    assert len(context) <= core.MAX_CONTEXT_CHARS
    assert context.endswith(core.PROMPT_SELECTION_INSTRUCTION)
    small = ["one line"]
    context = core._prompt_candidates_context(small)
    assert context == "one line\n" + core.PROMPT_SELECTION_INSTRUCTION

