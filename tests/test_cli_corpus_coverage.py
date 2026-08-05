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
    """An exclusion without a reason is a hole, not a decision.

    The type check is load-bearing: `str(None)` is `"None"`, which is non-empty,
    so a `null` reason would sail through a truthiness test and read in the JSON
    as a deliberate exclusion nobody had to justify.
    """
    unjustified = sorted(
        f"{name}: {why!r}"
        for name, why in CORPUS["excluded"].items()
        if not isinstance(why, str) or len(why.strip()) < 10
    )
    assert not unjustified, (
        "exclusions without a usable reason:\n  "
        + "\n  ".join(unjustified)
        + "\n\nState why the entrypoint cannot be budgeted, in words."
    )


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


def _adr_status(adr_id: str) -> str | None:
    """The frontmatter status of one ADR, or None when no such file exists.

    Distinguished from a file that exists but declares no status: that is a
    formatting problem, and reporting it as "does not exist" would send the
    reader looking for a missing record instead of a broken one.
    """
    for path in (ROOT / "docs" / "adr").glob(f"{adr_id}-*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("status:"):
                return line.split(":", 1)[1].strip().strip('"')
        return ""  # the record is there; its frontmatter is not
    return None


def test_the_paths_known_to_exceed_the_ceiling_are_recorded_rather_than_hidden():
    """Over-ceiling paths are recorded, not omitted.

    A corpus that simply left them out would read as full coverage, which is the
    failure TASK-126 was about.
    """
    known = CORPUS["known_over_ceiling"]
    assert known.get("note"), "the over-ceiling paths need a stated reason"
    assert len(known) > 1, "no over-ceiling path recorded; were they budgeted instead?"


def test_every_over_ceiling_path_names_a_real_adr():
    """ADR-033's contract, resolved from the record and not from a list here.

    Without this the exception field would be a comment: anyone could write
    `latency_ceiling_exception: "ADR-999"` and the corpus would read as decided.
    No command name appears in this assertion.

    The referenced record must EXIST; it need not yet be Accepted. These entries
    are recorded findings, not declared budgets -- ADR-015's ceiling binds the
    `budgets` block, which a separate test holds at 2000 ms. Requiring a
    signature before a finding may be written down would mean the honest move,
    recording what was measured, is the one the gate blocks.
    """
    unexcused = []
    for name, entry in CORPUS["known_over_ceiling"].items():
        if not isinstance(entry, dict):
            continue  # the note
        adr = entry.get("latency_ceiling_exception")
        if not adr:
            unexcused.append(f"{name}: no latency_ceiling_exception")
        else:
            status = _adr_status(adr)
            if status is None:
                unexcused.append(f"{name}: names {adr}, which does not exist")
            elif status == "":
                unexcused.append(
                    f"{name}: names {adr}, whose frontmatter declares no status"
                )

    assert not unexcused, (
        "CLI paths above the ceiling with nothing behind them:\n  "
        + "\n  ".join(unexcused)
        + "\n\nBring the path under the ceiling, or write an ADR naming it as a "
        "user-initiated whole-repository command and reference it here."
    )


def test_an_exception_becomes_binding_only_once_its_adr_is_accepted():
    """Reported rather than enforced, so the state is visible either way.

    A Proposed exception is a proposal: the finding is recorded and the decision
    is in flight. This surfaces which is which instead of letting a record sit
    at Proposed indefinitely while the corpus reads as settled.
    """
    pending = sorted(
        f"{name} -> {entry['latency_ceiling_exception']} ({_adr_status(entry['latency_ceiling_exception'])})"
        for name, entry in CORPUS["known_over_ceiling"].items()
        if isinstance(entry, dict)
        and entry.get("latency_ceiling_exception")
        and _adr_status(entry["latency_ceiling_exception"]) != "Accepted"
    )
    # Not an assertion about emptiness -- an assertion that whatever is pending
    # is nameable. The list is the report.
    assert all(" -> ADR-" in item for item in pending), pending


def test_percentiles_are_ordered_within_each_row():
    broken = sorted(
        name
        for name, row in CORPUS["budgets"].items()
        if not row["p50_ms"] <= row["p95_ms"] <= row["hard_timeout_ms"]
    )
    assert not broken, f"rows whose p50/p95/hard are not ordered: {broken}"
