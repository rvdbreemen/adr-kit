"""Bootstrap reads the history, and the auto-accept path is reachable (TASK-80, R1).

Two of spec R1's four clauses failed. `.git/**` was in the scanner's skip list
and all four scanners walked the working tree, so commit messages, churn and the
order in which subsystems arrived contributed nothing -- even though that is
where the *why* of an existing codebase lives. And the auto-accept machinery
existed but no shipped path reached it.

What these tests hold:

* history findings arrive, and stay **distinguishable** from tree findings. A
  file that exists is a fact; a commit subject is a claim someone typed once,
  possibly about a decision reversed three commits later. Merging them would let
  the weaker evidence borrow the stronger one's authority;
* the scan fails open on every way a history can be unreadable, because a
  bootstrap that refuses to run on a thin history is worse than one that scans
  what it can and says which half is missing;
* `document` then `accept --auto` really reaches Accepted -- and refuses an
  untouched scaffold, which is structurally complete, scores 0.88 against a 0.70
  threshold, and decides nothing.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCOVER = REPO_ROOT / "bin" / "adr-discover"
ADR = REPO_ROOT / "bin" / "adr"
INIT_SKILL = REPO_ROOT / "skills" / "init" / "SKILL.md"


def _history_module():
    name = "adr_history_scan_test"
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "bin" / "adr_history_scan.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


history = _history_module()


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=root, check=True, capture_output=True,
    )


def _repo_with_history(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    _git(root.parent, "init", "-q", str(root))
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "src" / "app.py").write_text("v = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "feat: initial import")
    for index in range(9):
        (root / "src" / "app.py").write_text(f"v = {index + 2}\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", f"chore: iterate {index}")
    (root / "src" / "app.py").write_text("v = 99\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "refactor: switch to asyncio for the event loop")
    return root


def _discover(root: Path, *args: str):
    result = subprocess.run(
        [sys.executable, str(DISCOVER), "--root", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# AC#1 and AC#2: history is read, and stays distinguishable
# ---------------------------------------------------------------------------

def test_a_direction_changing_commit_becomes_a_candidate(tmp_path):
    root = _repo_with_history(tmp_path)

    payload = _discover(root)

    subjects = [
        candidate["title"]
        for candidate in payload["candidates"]
        if candidate["id"].startswith("history-subject-")
    ]
    assert any("switch to asyncio" in subject for subject in subjects), subjects


def test_churn_marks_a_file_nobody_has_settled(tmp_path):
    root = _repo_with_history(tmp_path)

    payload = _discover(root)

    churn = [c for c in payload["candidates"] if c["id"] == "history-churn"]
    assert churn, "eleven rewrites of one file did not register as churn"
    assert "src/app.py" in churn[0]["evidence_files"]


def test_every_candidate_says_where_it_came_from(tmp_path):
    """The whole point of the split: a fact about a file is not a claim in a log."""
    root = _repo_with_history(tmp_path)

    payload = _discover(root)

    sources = {candidate.get("source") for candidate in payload["candidates"]}
    assert sources <= {"tree", "history"}
    assert "tree" in sources and "history" in sources
    assert all(candidate.get("source") for candidate in payload["candidates"])


def test_history_candidates_carry_their_own_weakness(tmp_path):
    root = _repo_with_history(tmp_path)

    payload = _discover(root)

    weak = [
        candidate
        for candidate in payload["candidates"]
        if candidate.get("source") == "history"
    ]
    assert weak
    assert all(
        "why_this_is_weak" in candidate["details"]
        for candidate in weak
        if candidate["id"] != "history-first-appearance"
    )


def test_the_history_scan_can_be_turned_off(tmp_path):
    root = _repo_with_history(tmp_path)

    payload = _discover(root, "--no-history")

    assert payload["history"]["available"] is False
    assert not [c for c in payload["candidates"] if c.get("source") == "history"]


# ---------------------------------------------------------------------------
# Fail open: a thin history is not an error
# ---------------------------------------------------------------------------

def test_a_directory_that_is_not_a_repository_scans_the_tree_anyway(tmp_path):
    root = tmp_path / "plain"
    (root).mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    payload = _discover(root)

    assert payload["history"]["available"] is False
    assert payload["history"]["reason"]
    assert payload["candidate_count"] >= 1, "the tree scan must still run"


def test_a_repository_with_no_commits_reports_a_reason(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    _git(root.parent, "init", "-q", str(root))

    result = history.scan_history(root)

    assert result["available"] is False
    assert result["candidates"] == []
    assert "commit" in (result["reason"] or "")


def test_bookkeeping_merges_are_not_decisions(tmp_path):
    root = _repo_with_history(tmp_path)
    (root / "note.txt").write_text("x\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "Merge branch 'main' into feature")

    payload = _discover(root)

    titles = [c["title"] for c in payload["candidates"]]
    assert not any(title.startswith("Merge branch") for title in titles)


# ---------------------------------------------------------------------------
# AC#3 and AC#4: the auto-accept path is reachable, and refuses a scaffold
# ---------------------------------------------------------------------------

def _adr(root: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(ADR), *args, "--adr-dir", str(root / "docs" / "adr")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _seeded_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("import sys\n", encoding="utf-8")
    _git(root.parent, "init", "-q", str(root))
    (root / "docs" / "adr" / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Test Runner"}}), encoding="utf-8"
    )
    assert _adr(root, "new", "Use Python for the CLI").returncode == 0
    return root


def _fill_in_the_scaffold(root: Path) -> None:
    path = next((root / "docs" / "adr").glob("ADR-001*.md"))
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "Chosen option: **Option A**, because state the decisive rationale.",
        "Chosen option: Python 3 with no runtime dependencies, because the CLI "
        "installs on machines with no package manager and src/app.py already "
        "imports only the standard library.",
    )
    text = text.replace(
        "State how implementation of the decision will be verified.",
        "src/app.py imports only stdlib modules; a dependency manifest would "
        "contradict this decision.",
    )
    text = re.sub(
        r"\{Describe[^}]*\}",
        "The CLI ships to machines with no package manager, so a runtime "
        "dependency would block installation outright.",
        text,
    )
    path.write_text(text, encoding="utf-8")


def test_document_records_a_real_signer(tmp_path):
    """It writes a history entry, so it must resolve a signer like every other
    lifecycle command. It did not, and the empty changed_by made the record
    permanently unacceptable two commands later."""
    root = _seeded_project(tmp_path)

    result = _adr(root, "document", "ADR-001", "--verified-in", "src/app.py")

    assert result.returncode == 0, result.stderr
    text = next((root / "docs" / "adr").glob("ADR-001*.md")).read_text(encoding="utf-8")
    assert 'changed_by: ""' not in text
    assert "User: Test Runner" in text


def test_an_untouched_scaffold_is_refused_by_the_auto_path(tmp_path):
    """Structurally complete, scores above threshold, decides nothing."""
    root = _seeded_project(tmp_path)
    assert _adr(root, "document", "ADR-001", "--verified-in", "src/app.py").returncode == 0

    result = _adr(root, "accept", "ADR-001", "--auto", "--auto-mode", "auto",
                  "--repo-root", str(root))

    assert result.returncode == 2
    assert "template instructions" in result.stderr


def test_a_written_record_reaches_accepted_through_the_supported_path(tmp_path):
    root = _seeded_project(tmp_path)
    _fill_in_the_scaffold(root)
    assert _adr(root, "document", "ADR-001", "--verified-in", "src/app.py").returncode == 0

    result = _adr(root, "accept", "ADR-001", "--auto", "--auto-mode", "auto",
                  "--repo-root", str(root))

    assert result.returncode == 0, result.stdout + result.stderr
    text = next((root / "docs" / "adr").glob("ADR-001*.md")).read_text(encoding="utf-8")
    assert 'status: "Accepted"' in text


def test_auto_accept_still_refuses_a_record_that_documents_nothing(tmp_path):
    """--auto is not a bypass: without shipped evidence it is an ordinary ADR."""
    root = _seeded_project(tmp_path)
    _fill_in_the_scaffold(root)

    result = _adr(root, "accept", "ADR-001", "--auto", "--auto-mode", "auto",
                  "--repo-root", str(root))

    assert result.returncode == 2
    assert "documents_shipped" in result.stderr


# ---------------------------------------------------------------------------
# AC#5 and AC#6: the skill text
# ---------------------------------------------------------------------------

def test_init_names_the_lifecycle_command_and_verifies_the_index():
    text = INIT_SKILL.read_text(encoding="utf-8")

    assert "bin/adr new" in text, "init must name the command, not gesture at it"
    assert "adr-index docs/adr --check" in text
    # Prose wraps; the assertion is about the instruction, not the line breaks.
    assert "does not finish" in " ".join(text.split()).casefold()


def test_init_reconciles_never_silently_accept_with_the_auto_path():
    text = INIT_SKILL.read_text(encoding="utf-8")

    assert "accept ADR-NNN --auto" in text
    assert "documentation, not authorisation" in text
    # The rule that survives: the user is always asked.
    assert "Never accept without" in text or "never accepted" in text
