"""A question may go from open to answered, and nowhere else (TASK-96, ADR-022).

Every consumer of this data checked only *unresolved* items, so deleting a
question raised the quality score and cleared the acceptance gate exactly as
answering it did -- while `bin/adr answer` was the strictly more expensive path.
The cheapest route through the gates destroyed the record of the grilling.
Nobody has to act in bad faith for that to happen; it is what the incentive
rewarded.

Gate anchor for ADR-022: adr-open-questions-append-only-v1
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "bin" / "adr-lint"


def _format_module():
    spec = importlib.util.spec_from_file_location(
        "adr_format_under_test", ROOT / "bin" / "adr_format.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FORMAT = _format_module()

_ADR = """---
id: "ADR-001"
title: "Pick a Retrieval Store"
status: "Proposed"
date: "2026-08-05"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
context_scope: "selective"
---

# ADR-001 Pick a Retrieval Store

## Status

Proposed, 2026-08-05.

## Context and Problem Statement

The retrieval layer needs somewhere to keep its vectors.

## Decision Drivers

* Local-first.

## Considered Options

* A file-backed store.
* An external service.

## Decision Outcome

Chosen option: **a file-backed store**, because it keeps the hot path local.

## Consequences

### Positive

* No network on the query path.

### Negative

* The store has to be rebuilt when the model changes.

## Open Questions

{questions}

## Related Decisions

* None.

## References

* bin/adr-embed
"""

TWO_OPEN = "- [ ] Should the store be rebuilt automatically?\n- [ ] Which model is the default?"
ONE_ANSWERED = (
    "- [x] Should the store be rebuilt automatically? — **Answered 2026-08-05 by "
    "User: Robert van den Breemen:** no, an explicit build step keeps it predictable.\n"
    "- [ ] Which model is the default?"
)
ONE_DELETED = "- [ ] Which model is the default?"


def _repo(tmp_path: Path, questions: str) -> Path:
    """A git repository with one committed Proposed ADR."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-pick-a-retrieval-store.md").write_text(
        _ADR.format(questions=questions), encoding="utf-8"
    )
    for argv in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "Test Person"],
        ["git", "add", "-A"],
        ["git", "commit", "-qm", "seed"],
    ):
        subprocess.run(argv, cwd=str(tmp_path), capture_output=True, check=True)
    return adr_dir


def _lint(adr_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LINT), "--gates", "all", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _rewrite(adr_dir: Path, questions: str) -> None:
    target = adr_dir / "ADR-001-pick-a-retrieval-store.md"
    target.write_text(_ADR.format(questions=questions), encoding="utf-8")


def test_deleting_a_question_fails_and_quotes_it(tmp_path):
    """AC#2 and AC#6. The message has to name what was lost."""
    adr_dir = _repo(tmp_path, TWO_OPEN)
    _rewrite(adr_dir, ONE_DELETED)

    result = _lint(adr_dir)

    assert result.returncode != 0, result.stdout[-1500:]
    assert "Should the store be rebuilt automatically?" in result.stdout
    assert "bin/adr answer" in result.stdout


def test_answering_a_question_passes(tmp_path):
    """AC#3 and AC#6. The supported path must not be the one that fails."""
    adr_dir = _repo(tmp_path, TWO_OPEN)
    _rewrite(adr_dir, ONE_ANSWERED)

    result = _lint(adr_dir)

    assert "open-questions-deleted" not in result.stdout, result.stdout[-1500:]


def test_adding_a_question_passes(tmp_path):
    """Append-only means append is allowed."""
    adr_dir = _repo(tmp_path, ONE_DELETED)
    _rewrite(adr_dir, TWO_OPEN)

    result = _lint(adr_dir)

    assert "open-questions-deleted" not in result.stdout, result.stdout[-1500:]


def test_outside_a_git_repository_the_check_is_advisory_and_says_so(tmp_path):
    """AC#5. A hole named is worth more than a check that pretends."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-pick-a-retrieval-store.md").write_text(
        _ADR.format(questions=TWO_OPEN), encoding="utf-8"
    )

    # JSON, because the human summary counts advisories without naming them and
    # the point here is *which* advisory was raised.
    result = subprocess.run(
        [sys.executable, str(LINT), "--gates", "all", "--format", "json", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    import json as _json

    codes = [
        finding.get("code")
        for entry in _json.loads(result.stdout).get("files", [])
        for finding in entry.get("findings", [])
    ]
    assert "open-questions-unverifiable" in codes, result.stdout[-1500:]
    # Advisory, so it must not fail the run on its own.
    assert "open-questions-deleted" not in codes
    assert result.returncode == 0, result.stdout[-800:]


def test_an_accepted_record_is_not_subject_to_the_rule(tmp_path):
    """The rule is about a Proposed record's grilling, not a settled one."""
    adr_dir = _repo(tmp_path, TWO_OPEN)
    target = adr_dir / "ADR-001-pick-a-retrieval-store.md"
    target.write_text(
        _ADR.format(questions=ONE_DELETED).replace(
            'status: "Proposed"', 'status: "Accepted"'
        ),
        encoding="utf-8",
    )

    result = _lint(adr_dir)

    assert "open-questions-deleted" not in result.stdout, result.stdout[-1500:]


def test_the_parser_tells_an_answered_question_from_an_open_one():
    """AC#4's foundation: the two states must be distinguishable at all.

    `unresolved_open_questions` returns the same empty list for both, which is
    right for "what still blocks acceptance" and useless for "what was here".
    """
    answered = FORMAT.all_open_questions(_ADR.format(questions=ONE_ANSWERED))
    assert answered == {
        "Should the store be rebuilt automatically?": True,
        "Which model is the default?": False,
    }
    assert FORMAT.unresolved_open_questions(
        _ADR.format(questions=ONE_ANSWERED)
    ) == ["Which model is the default?"]


def test_readiness_stops_treating_deletion_and_answering_as_equivalent(tmp_path):
    """AC#4. Both leave the unresolved list empty; only one kept the reasoning."""
    sys.path.insert(0, str(ROOT / "bin"))
    spec = importlib.util.spec_from_file_location(
        "adr_readiness_under_test", ROOT / "bin" / "adr_readiness.py"
    )
    readiness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(readiness)

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    answered_file = adr_dir / "answered.md"
    deleted_file = adr_dir / "deleted.md"
    answered_file.write_text(
        _ADR.format(
            questions=ONE_ANSWERED.replace("\n- [ ] Which model is the default?", "")
        ),
        encoding="utf-8",
    )
    deleted_file.write_text(_ADR.format(questions="* None."), encoding="utf-8")

    answered_record = {"open_questions": [], "path": str(answered_file)}
    deleted_record = {"open_questions": [], "path": str(deleted_file)}

    assert readiness._open_questions_resolved(answered_record) is True
    # No questions at all is still resolved -- there is nothing to preserve.
    assert readiness._open_questions_resolved(deleted_record) is True

    # The distinction that matters: a record still carrying an unanswered
    # question is not resolved, however the section is spelled.
    open_file = adr_dir / "open.md"
    open_file.write_text(_ADR.format(questions=TWO_OPEN), encoding="utf-8")
    assert (
        readiness._open_questions_resolved(
            {"open_questions": ["Which model is the default?"], "path": str(open_file)}
        )
        is False
    )


@pytest.mark.parametrize("client", ["codex", "copilot"])
def test_both_mirrors_carry_the_check(client):
    lint = (ROOT / client / "bin" / "adr-lint").read_text(encoding="utf-8")
    assert "check_open_questions_append_only" in lint
