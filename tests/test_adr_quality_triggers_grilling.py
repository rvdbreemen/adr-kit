"""Quality decides who gets grilled, and the answers survive (TASK-82, R9).

What shipped was strong on the acceptance side and empty on the evaluation
side. `rank_proposed` enrolled every Proposed ADR, so a sharp one and an empty
one were queued identically with quality only a tiebreaker in the sort.
Readiness computed its own "quality" from three booleans. The real weighted
scorer, `bin/adr-quality`, was reachable from nothing but the `accept --auto`
path that nothing reached.

And grilling threw away half of every exchange. `## Open Questions` holds
unresolved items by design, and acceptance requires the list to be empty, so an
author who answered a question had to *delete* it to accept the ADR. What
survived was the Status History: who flipped the status and when, never what
they were asked -- and the reasoning is exactly what a future reader needs in
order to re-evaluate the decision, which is what supersession depends on.

The fix did not need a new persistence layer. `unresolved_open_questions`
already skipped `[x]` and `Answered:` items, so a checked line carrying the
answer survives acceptance untouched. `bin/adr answer` writes that line, which
turns a convention nobody documented into a mechanism.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"
ADR = BIN / "adr"
ADR_QUALITY = BIN / "adr-quality"
GUARDIAN = BIN / "adr-guardian"
GRILL_SKILL = REPO_ROOT / "skills" / "grill" / "SKILL.md"

for value in (str(BIN),):
    if value not in sys.path:
        sys.path.insert(0, value)

import adr_format  # noqa: E402
import adr_schema  # noqa: E402
import adr_catalog  # noqa: E402
import adr_quality_core  # noqa: E402
from adr_guardian_queue import rank_proposed  # noqa: E402


# ---------------------------------------------------------------------------
# AC#1: the queue is driven by quality, and a sharp ADR drops out
# ---------------------------------------------------------------------------

def _item(adr_id: str, *, quality: float, **flags) -> dict:
    return {
        "adr_id": adr_id,
        "status": "Proposed",
        "date": "2026-07-20",
        "classification": "ready-for-confirmation" if flags.get("ready") else "needs-mechanical-fix",
        "documents_shipped": flags.get("shipped", False),
        "open_questions": ["Who owns this?"] if flags.get("questions") else [],
        "quality": {"score": quality, "threshold": 0.70},
        "implementation_link": {"linked": flags.get("linked", False)},
    }


def _report(items: list[dict]) -> dict:
    return {"schema_version": 1, "evaluated_on": "2026-07-20", "adrs": items}


def test_a_low_score_puts_an_adr_in_the_queue_on_its_own():
    queued = rank_proposed(_report([_item("ADR-001", quality=0.40)]))

    assert [row["adr_id"] for row in queued] == ["ADR-001"]
    assert any("below" in reason for reason in queued[0]["reasons"])
    assert queued[0]["below_threshold"] is True


def test_a_sharp_adr_with_nothing_attached_drops_out():
    """The other half of AC#1, and the reason the first half is worth anything."""
    queued = rank_proposed(_report([_item("ADR-001", quality=0.95)]))

    assert queued == []


def test_a_sharp_adr_still_queues_when_something_else_needs_doing():
    queued = rank_proposed(_report([_item("ADR-001", quality=0.95, linked=True)]))

    assert [row["adr_id"] for row in queued] == ["ADR-001"]
    assert "active implementation link" in queued[0]["reasons"]
    assert queued[0]["below_threshold"] is False


def test_a_decayed_adr_outranks_a_merely_old_one():
    queued = rank_proposed(_report([
        _item("ADR-002", quality=0.95, questions=True),
        _item("ADR-001", quality=0.30),
    ]))

    # Open questions still outrank a low score -- a human is already waiting.
    assert [row["adr_id"] for row in queued] == ["ADR-002", "ADR-001"]


# ---------------------------------------------------------------------------
# AC#6: the real scorer is on a shipped path
# ---------------------------------------------------------------------------

def test_readiness_reads_the_weighted_scorer_not_three_booleans():
    from adr_readiness import build_readiness_report

    report = build_readiness_report(
        REPO_ROOT / "docs" / "adr", evaluated_on=date(2026, 8, 2), all_proposed=True
    )

    assert report["adrs"], "this repository should carry at least one Proposed ADR"
    for item in report["adrs"]:
        assert item["quality"]["source"] == "adr-quality", (
            "readiness fell back to the structural booleans; the scorer is "
            "unreachable again"
        )
        assert item["quality"]["threshold"] == adr_quality_core.QUALITY_THRESHOLD
        assert "below_threshold" in item["quality"]


def test_the_scorer_is_importable_and_scores_a_directory():
    scores = adr_quality_core.score_directory(
        REPO_ROOT / "docs" / "adr", statuses=["Accepted"]
    )

    assert len(scores) >= 10
    assert all(0.0 <= result["overall"] <= 1.0 for result in scores.values())


def test_an_unreadable_record_is_a_none_not_an_exception(tmp_path):
    assert adr_quality_core.score_path(tmp_path / "nope.md") is None


# ---------------------------------------------------------------------------
# AC#2: Accepted records are evaluated too
# ---------------------------------------------------------------------------

def test_the_sweep_reports_accepted_records_and_gates_on_decay():
    result = subprocess.run(
        [sys.executable, str(ADR_QUALITY), "--adr-dir",
         str(REPO_ROOT / "docs" / "adr"), "--status", "Accepted", "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    payload = json.loads(result.stdout)
    assert payload["scored"] >= 10
    assert payload["statuses"] == ["Accepted"]
    # This repository is healthy, so the gate passes; the contract is that it
    # would not if a record had decayed.
    assert result.returncode == (1 if payload["below_threshold"] else 0)


def test_the_sweep_gates_on_a_decayed_record(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-thin.md").write_text(
        "# ADR-001 Thin\n\n## Status\n\nAccepted, 2026-05-01.\n\n"
        "## Context\n\nx\n\n## Decision\n\nx\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(ADR_QUALITY), "--adr-dir", str(adr_dir), "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    assert result.returncode == 1
    assert json.loads(result.stdout)["below_threshold"] >= 1


# ---------------------------------------------------------------------------
# AC#3 and AC#4: the exchange survives acceptance
# ---------------------------------------------------------------------------

def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    (root / "docs" / "adr" / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Test Runner"}}), encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, str(ADR), "new", "Pick a queue backend",
         "--adr-dir", str(root / "docs" / "adr")],
        cwd=root, check=True, capture_output=True,
    )
    path = next((root / "docs" / "adr").glob("ADR-001*.md"))
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"(## Open Questions\n\n).*?(\n## )",
        r"\1- [ ] Does the queue need at-least-once or exactly-once delivery?\n"
        r"- [ ] Who owns the dead-letter policy?\n\2",
        text, count=1, flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    return root


def _answer(root: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(ADR), "answer", "ADR-001", *args,
         "--adr-dir", str(root / "docs" / "adr")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_an_answer_keeps_the_question_with_it(tmp_path):
    root = _project(tmp_path)

    result = _answer(root, "--question", "dead-letter",
                     "--answer", "Platform team owns it; runbook RB-14.")

    assert result.returncode == 0, result.stderr
    text = next((root / "docs" / "adr").glob("ADR-001*.md")).read_text(encoding="utf-8")
    assert "- [x] Who owns the dead-letter policy? — **Answered" in text
    assert "runbook RB-14" in text
    assert "User: Test Runner" in text


def test_an_answered_question_no_longer_blocks_acceptance(tmp_path):
    """The whole point: resolved and unresolved are different states."""
    root = _project(tmp_path)
    path = next((root / "docs" / "adr").glob("ADR-001*.md"))

    assert len(adr_format.unresolved_open_questions(path.read_text(encoding="utf-8"))) == 2
    assert _answer(root, "--question", "1", "--answer", "At-least-once.").returncode == 0
    assert _answer(root, "--question", "1", "--answer", "Platform team.").returncode == 0

    text = path.read_text(encoding="utf-8")
    assert adr_format.unresolved_open_questions(text) == []
    # And both exchanges are still in the record, which is the durable half.
    assert text.count("**Answered") == 2


def test_answering_preserves_the_blank_line_before_the_next_heading(tmp_path):
    root = _project(tmp_path)

    _answer(root, "--question", "1", "--answer", "At-least-once.")

    text = next((root / "docs" / "adr").glob("ADR-001*.md")).read_text(encoding="utf-8")
    assert "\n\n## Related Decisions" in text


def test_an_ambiguous_answer_refuses_and_lists_the_choices(tmp_path):
    root = _project(tmp_path)

    result = _answer(root, "--answer", "something")

    assert result.returncode == 2
    assert "2 unresolved questions" in result.stderr
    assert "dead-letter" in result.stderr


def test_an_empty_answer_is_refused(tmp_path):
    root = _project(tmp_path)

    result = _answer(root, "--question", "1", "--answer", "   ")

    assert result.returncode == 2
    assert "deletion with extra steps" in result.stderr


def test_answering_a_record_with_no_open_questions_says_so(tmp_path):
    root = _project(tmp_path)
    _answer(root, "--question", "1", "--answer", "At-least-once.")
    _answer(root, "--question", "1", "--answer", "Platform team.")

    result = _answer(root, "--answer", "another")

    assert result.returncode == 2
    assert "no unresolved question" in result.stderr


def test_the_grill_skill_names_the_writer_and_forbids_deletion():
    text = " ".join(GRILL_SKILL.read_text(encoding="utf-8").split())

    assert "bin/adr answer" in text
    assert "Never delete an answered question" in text


# ---------------------------------------------------------------------------
# AC#5: the nudge no longer waits for a model to read a sentence
# ---------------------------------------------------------------------------

def test_the_guardian_builds_the_queue_when_the_cache_is_missing(tmp_path):
    root = tmp_path / "project"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-thin.md").write_text(
        "---\nid: \"ADR-001\"\ntitle: \"Thin\"\nstatus: \"Proposed\"\n"
        "date: \"2026-05-01\"\nbinding: false\ngate: null\n"
        "documents_shipped: true\nverified_in: []\nsupersedes: []\n"
        "superseded_by: null\n---\n\n# ADR-001 Thin\n\n## Status\n\n"
        "Proposed, 2026-05-01.\n\n## Context\n\nx\n\n## Decision\n\nx\n",
        encoding="utf-8",
    )
    cache = adr_dir / ".adr-kit-readiness.json"
    assert not cache.exists()

    result = subprocess.run(
        [sys.executable, str(GUARDIAN), "check"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    assert result.returncode == 0
    assert cache.is_file(), (
        "the grill nudge's cache is still written only by a command that nothing "
        "invokes, so on a fresh clone the nudge stays silent"
    )
    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert payload["authoritative"] is False


def test_a_fresh_cache_is_left_alone(tmp_path):
    """The common case must cost one stat, not a full readiness pass."""
    root = tmp_path / "project"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-thin.md").write_text("# ADR-001 Thin\n\n## Status\n\nProposed.\n",
                                             encoding="utf-8")
    cache = adr_dir / ".adr-kit-readiness.json"
    sentinel = {
        "schema_version": 1,
        "authoritative": False,
        "generated_at": datetime(2026, 8, 2, tzinfo=timezone.utc).isoformat(),
        "expires_at": datetime(2099, 1, 1, tzinfo=timezone.utc).isoformat(),
        "actions": [],
        "sentinel": "untouched",
    }
    cache.write_text(json.dumps(sentinel), encoding="utf-8")

    subprocess.run([sys.executable, str(GUARDIAN), "check"], cwd=root,
                   capture_output=True, text=True)

    assert json.loads(cache.read_text(encoding="utf-8")).get("sentinel") == "untouched"


def test_the_guardian_still_exits_zero_when_the_queue_cannot_be_built(tmp_path):
    """A session must never fail to start because a nudge could not be computed."""
    root = tmp_path / "project"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-broken.md").write_text("---\nnot: [valid\n---\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(GUARDIAN), "check"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    assert result.returncode == 0
