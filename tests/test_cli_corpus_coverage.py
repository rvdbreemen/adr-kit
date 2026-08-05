"""Every bin/ entrypoint is inside ADR-015's fixture contract, or excluded by name.

ADR-015 chose a fixture contract precisely so the measurement survives slow CI
runners and future tools. A tool absent from the corpus is outside that contract
without anyone deciding it should be -- and the corpus covered 3 of 26
entrypoints, with nothing failing when a new one shipped without a row
(TASK-126).

The gate is coverage, not the numbers: it fails on an entrypoint that is neither
measured nor excluded, so the next tool cannot land outside the contract the same
silent way.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads(
    (ROOT / "tests" / "fixtures" / "cli" / "latency-corpus.json").read_text(
        encoding="utf-8"
    )
)
CEILING_MS = 2000


def _entrypoints() -> set[str]:
    return {p.name for p in (ROOT / "bin").iterdir() if p.is_file() and p.suffix == ""}


def test_every_entrypoint_is_budgeted_or_excluded_with_a_reason():
    budgeted = set(CORPUS["budgets"])
    excluded = set(CORPUS["excluded"])
    uncovered = sorted(_entrypoints() - budgeted - excluded)
    assert not uncovered, (
        "bin/ entrypoints outside ADR-015's fixture contract:\n  "
        + "\n  ".join(uncovered)
        + "\n\nAdd a measured row to tests/fixtures/cli/latency-corpus.json, or "
        "add it to `excluded` with the reason it cannot be budgeted."
    )


def test_no_exclusion_is_silent():
    """An exclusion without a reason is a hole, not a decision."""
    empty = sorted(name for name, why in CORPUS["excluded"].items() if not str(why).strip())
    assert not empty, f"excluded with no reason given: {empty}"


def test_no_exclusion_names_something_that_is_not_an_entrypoint():
    """A stale exclusion would quietly widen the hole as bin/ changes."""
    stale = sorted(set(CORPUS["excluded"]) - _entrypoints())
    assert not stale, (
        f"excluded names that are no longer in bin/: {stale}. Remove them, or the "
        "exclusion list starts covering things nobody checked."
    )


def test_every_budget_row_declares_which_kind_of_measurement_it_is():
    """A startup floor and a workload cost are not the same claim.

    Conflating them is how a corpus starts describing one repository rather than
    the tool: `--help` is the interpreter-plus-import floor every invocation
    pays, and the real cost of a lint run depends on the ADR set in front of it.
    """
    kinds = set(CORPUS["budget_kinds"])
    undeclared = sorted(
        name for name, row in CORPUS["budgets"].items() if row.get("kind") not in kinds
    )
    assert not undeclared, f"budget rows with no declared kind: {undeclared}"


def test_no_budgeted_row_exceeds_the_ceiling():
    """ADR-015's Must Not, on the CLI side it was already meant to cover."""
    over = sorted(
        f"{name}: {row['hard_timeout_ms']} ms"
        for name, row in CORPUS["budgets"].items()
        if row["hard_timeout_ms"] > CEILING_MS
    )
    assert not over, (
        f"CLI budgets above ADR-015's {CEILING_MS} ms ceiling:\n  " + "\n  ".join(over)
    )


def test_the_paths_known_to_exceed_the_ceiling_are_recorded_rather_than_hidden():
    """Three measured paths are over the ceiling and are not budgeted here.

    Recording them is the point: a corpus that simply omitted them would read as
    full coverage, which is the failure this whole task is about.
    """
    known = CORPUS["known_over_ceiling"]
    assert known.get("note"), "the over-ceiling paths need a stated reason"
    assert len(known) > 1, "no over-ceiling path recorded; were they budgeted instead?"


def test_percentiles_are_ordered_within_each_row():
    broken = sorted(
        name
        for name, row in CORPUS["budgets"].items()
        if not row["p50_ms"] <= row["p95_ms"] <= row["hard_timeout_ms"]
    )
    assert not broken, f"rows whose p50/p95/hard are not ordered: {broken}"
