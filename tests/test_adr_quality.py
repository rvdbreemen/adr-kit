"""Tests for bin/adr-quality.

Unit tests use importlib.machinery.SourceFileLoader to import gate functions
directly (the file has no .py extension). CLI behaviour (JSON output, exit
codes) is tested via subprocess, matching the pattern used in test_adr_lint.py.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_QUALITY = REPO_ROOT / "bin" / "adr-quality"

# ---------------------------------------------------------------------------
# Import gate functions directly via SourceFileLoader
# ---------------------------------------------------------------------------

loader = importlib.machinery.SourceFileLoader("adr_quality", str(ADR_QUALITY))
spec = importlib.util.spec_from_loader("adr_quality", loader)
adr_quality_mod = importlib.util.module_from_spec(spec)
# Register in sys.modules before exec so @dataclass (Python 3.13+) can
# resolve cls.__module__ during class processing.
sys.modules["adr_quality"] = adr_quality_mod
loader.exec_module(adr_quality_mod)

gate_completeness = adr_quality_mod.gate_completeness
gate_evidence = adr_quality_mod.gate_evidence
gate_clarity = adr_quality_mod.gate_clarity
gate_consistency = adr_quality_mod.gate_consistency
score_adr_quality = adr_quality_mod.score_adr_quality

# ---------------------------------------------------------------------------
# Fixture content helpers
# ---------------------------------------------------------------------------

FULL_ADR = """\
# ADR-042 Use PostgreSQL for Sensor Data

## Status

Accepted. Date: 2024-01-15.

## Status History

status_history:
  - date: 2024-01-15
    status: Accepted
    changed_by: Team
    reason: Initial decision record
    changed_via: adr-kit

## Context

We need a persistent store for 1 million sensor readings per day. The existing
in-memory solution cannot survive process restarts and causes data loss during
deployments. We evaluated several options given our team's expertise and the
NFR (Non-Functional Requirement) for 99.9% availability.

## Decision

We use PostgreSQL 15 as the primary data store for all sensor data,
replacing the in-memory HashMap. This change reduces data loss risk from 100%
on restart to 0%, and allows queries across 90-day rolling windows.

## Alternatives Considered

### Alternative A: MySQL

MySQL was considered but rejected because our team has deeper PostgreSQL
expertise and the JSONB column type fits our schema better.

### Alternative B: MongoDB

MongoDB was evaluated but rejected: the document model adds 15% overhead
per record compared to a normalised relational schema.

### Alternative C: Do nothing

Keeping the in-memory store would continue causing data loss on every
deployment (observed 12 times in Q3 2023). Unacceptable for production.

## Consequences

**Benefits**

- Data persists across restarts: 0 data-loss events expected vs 12 in Q3.
- Query latency: 5 ms p99 for 90-day aggregation queries.

**Trade-offs**

- Adds operational overhead: 2 hours/week for DBA tasks.

**Risks and mitigations**

- *Risk*: schema migration downtime. *Mitigation*: use zero-downtime migrations
  with pg_repack.

## Related Decisions

- **ADR-001 (Technology Stack)**: PostgreSQL aligns with our approved stack list.
- **ADR-010 (Data Retention Policy)**: this ADR implements the 90-day window.

## References

- TASK-500: spike to evaluate database options.
- src/storage/sensor_store.py:42 initial implementation.
- https://www.postgresql.org/docs/15/index.html
- Benchmark results: 5 ms p99 at 50 MB/s write throughput.
"""

MINIMAL_POOR_ADR = """\
Something about maybe using a different approach.

It might work or it might not. We could consider other options possibly.
"""

ALL_SECTIONS_ADR = """\
# ADR-001 Some Decision

## Status

Accepted.

## Status History

status_history:
  - date: 2024-01-01
    status: Accepted
    changed_by: Team
    reason: Initial
    changed_via: adr-kit

## Context

We need to choose a database for storing user records in our application.
The current in-memory store causes data loss on restart and cannot scale.

## Decision

We use PostgreSQL as the primary relational database for all user data.
This replaces the in-memory HashMap and provides ACID guarantees. The
migration will be done in three phases over two sprints.

## Alternatives Considered

### Alternative A: MySQL

MySQL was considered but rejected due to weaker JSONB support.

### Alternative B: MongoDB

MongoDB was rejected because the team lacks NoSQL operational expertise.

## Consequences

**Benefits**

- Persistence across restarts.

**Trade-offs**

- Increased operational complexity.

## Related Decisions

- **ADR-002 (Backup Strategy)**: depends on this decision.

## References

- TASK-123: database evaluation spike.
"""

# ---------------------------------------------------------------------------
# 1. test_completeness_all_sections_present
# ---------------------------------------------------------------------------

def test_completeness_all_sections_present():
    result = gate_completeness(FULL_ADR)
    assert result["score"] == pytest.approx(1.0, abs=1e-9)
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# 2. test_completeness_missing_sections
# ---------------------------------------------------------------------------

def test_completeness_missing_sections():
    # Remove Status and References sections
    truncated = "\n".join(
        ln for ln in FULL_ADR.splitlines()
        if not ln.startswith("## Status") and not ln.startswith("## References")
    )
    result = gate_completeness(truncated)
    assert result["score"] < 1.0
    assert any(
        issue.code == "MISSING_SECTION"
        and ("Status" in issue.detail or "References" in issue.detail)
        for issue in result["issues"]
    )


def test_completeness_counts_an_empty_required_section_as_missing():
    """A heading with nothing under it scored full marks here (TASK-198).

    The section loop tested presence alone, while the checks below it already
    measured emptiness for Decision, Alternatives and Consequences. References
    and Related Decisions fell through that gap, and
    `adr accept --quality-threshold` reads this score.
    """
    hollow = re.sub(
        r"^## References\n.*\Z", "## References\n\n", FULL_ADR, flags=re.M | re.S
    )
    assert "## References" in hollow
    result = gate_completeness(hollow)
    assert result["score"] < 1.0
    assert any(
        issue.code == "MISSING_SECTION" and "References" in issue.detail
        for issue in result["issues"]
    )


def test_completeness_counts_a_placeholder_only_section_as_missing():
    """The TODO that adr-migrate writes is a hole, not content (TASK-198)."""
    placeholder = re.sub(
        r"^## References\n.*\Z",
        "## References\n\n- TODO: add verifiable references.\n",
        FULL_ADR,
        flags=re.M | re.S,
    )
    result = gate_completeness(placeholder)
    assert result["score"] < 1.0
    assert any(
        issue.code == "MISSING_SECTION" and "References" in issue.detail
        for issue in result["issues"]
    )


# ---------------------------------------------------------------------------
# 3. test_completeness_short_decision
# ---------------------------------------------------------------------------

def test_completeness_short_decision():
    short_decision_adr = ALL_SECTIONS_ADR.replace(
        "We use PostgreSQL as the primary relational database for all user data.\n"
        "This replaces the in-memory HashMap and provides ACID guarantees. The\n"
        "migration will be done in three phases over two sprints.",
        "Use PostgreSQL.",
    )
    result = gate_completeness(short_decision_adr)
    assert result["checks"]["decision_length_ok"] is False
    assert any(issue.code == "DECISION_TOO_SHORT" for issue in result["issues"])


# ---------------------------------------------------------------------------
# 4. test_completeness_one_alternative
# ---------------------------------------------------------------------------

def test_completeness_one_alternative():
    one_alt_adr = """\
# ADR-001 Some Decision

## Status

Accepted.

## Context

We need a database. The current solution does not work.

## Decision

We choose PostgreSQL as the primary database. It offers ACID compliance and
is well-supported. The team has 3 years of operational experience with it.

## Alternatives Considered

### Alternative A: MySQL

MySQL was considered but rejected due to weaker JSONB support.

## Consequences

- Better performance.

## Related Decisions

- ADR-002.

## References

- TASK-100.
"""
    result = gate_completeness(one_alt_adr)
    assert result["checks"]["alternatives_count_ok"] is False
    assert any(issue.code == "TOO_FEW_ALTERNATIVES" for issue in result["issues"])


# ---------------------------------------------------------------------------
# 5. test_evidence_with_metrics
# ---------------------------------------------------------------------------

def test_evidence_with_metrics():
    result = gate_evidence(FULL_ADR)
    assert result["checks"]["metrics_present"] is True
    assert result["score"] >= 0.3


# ---------------------------------------------------------------------------
# 6. test_evidence_with_links
# ---------------------------------------------------------------------------

def test_evidence_with_links():
    result = gate_evidence(FULL_ADR)
    assert result["checks"]["external_link_present"] is True
    assert result["score"] >= 0.2


# ---------------------------------------------------------------------------
# 7. test_evidence_minimal
# ---------------------------------------------------------------------------

def test_evidence_minimal():
    minimal = """\
## Status

Accepted.

## Context

Some context here.

## Decision

We decided something.

## Alternatives Considered

- Option A: rejected.
- Option B: rejected.

## Consequences

Some consequences.

## Related Decisions

None.

## References

None.
"""
    result = gate_evidence(minimal)
    assert result["score"] < 0.5
    assert result["checks"]["references_present"] is False


# ---------------------------------------------------------------------------
# 8. test_clarity_vague_language
# ---------------------------------------------------------------------------

def test_clarity_vague_language():
    vague_adr = ALL_SECTIONS_ADR.replace(
        "We use PostgreSQL as the primary relational database for all user data.\n"
        "This replaces the in-memory HashMap and provides ACID guarantees. The\n"
        "migration will be done in three phases over two sprints.",
        "We might consider using PostgreSQL, or possibly another database. "
        "The team should consider the trade-offs carefully before deciding.",
    )
    result = gate_clarity(vague_adr)
    assert result["checks"]["no_vague_language"] is False
    assert any(issue.code == "VAGUE_LANGUAGE" for issue in result["issues"])


# ---------------------------------------------------------------------------
# 9. test_clarity_good_decision
# ---------------------------------------------------------------------------

def test_clarity_good_decision():
    result = gate_clarity(ALL_SECTIONS_ADR)
    assert result["checks"]["no_vague_language"] is True
    assert not any(issue.code == "VAGUE_LANGUAGE" for issue in result["issues"])


# ---------------------------------------------------------------------------
# 10. test_consistency_related_decisions_present
# ---------------------------------------------------------------------------

def test_consistency_related_decisions_present():
    result = gate_consistency(FULL_ADR)
    assert result["checks"]["related_decisions_present"] is True
    assert result["score"] >= 0.4


# ---------------------------------------------------------------------------
# 11. test_overall_grade_A
# ---------------------------------------------------------------------------

def test_overall_grade_A():
    with tempfile.TemporaryDirectory() as tmpdir:
        adr_path = Path(tmpdir) / "ADR-042-use-postgresql.md"
        adr_path.write_text(FULL_ADR, encoding="utf-8")
        result = score_adr_quality(FULL_ADR, adr_path)
    assert result["grade"] == "A"
    assert result["overall"] >= 0.85


# ---------------------------------------------------------------------------
# 12. test_overall_grade_D
# ---------------------------------------------------------------------------

def test_overall_grade_D():
    with tempfile.TemporaryDirectory() as tmpdir:
        adr_path = Path(tmpdir) / "ADR-001-bad.md"
        adr_path.write_text(MINIMAL_POOR_ADR, encoding="utf-8")
        result = score_adr_quality(MINIMAL_POOR_ADR, adr_path)
    assert result["grade"] == "D"
    assert result["overall"] < 0.55


# ---------------------------------------------------------------------------
# CLI tests via subprocess
# ---------------------------------------------------------------------------

def _run_quality(*args):
    """Invoke adr-quality and return (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(ADR_QUALITY), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# 13. test_json_output_format
# ---------------------------------------------------------------------------

def test_json_output_format():
    with tempfile.NamedTemporaryFile(
        suffix=".md",
        prefix="ADR-042-",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as f:
        f.write(FULL_ADR)
        tmp_path = f.name

    try:
        code, stdout, stderr = _run_quality("--format", "json", tmp_path)
        data = json.loads(stdout)
        assert "adr_id" in data
        assert "overall" in data
        assert "grade" in data
        assert "gates" in data
        assert "issues" in data
        assert "recommendations" in data
        assert set(data["gates"].keys()) == {"completeness", "evidence", "clarity", "consistency"}
        assert isinstance(data["overall"], float)
        assert data["grade"] in ("A", "B", "C", "D")
        # Structured-issue contract: each issue is a dict with code/detail/
        # severity/message fields. Issues may be empty when the ADR is clean.
        assert isinstance(data["issues"], list)
        for issue in data["issues"]:
            assert set(issue.keys()) >= {"code", "detail", "severity", "message"}
            assert issue["severity"] in ("high", "medium", "low")
        # Per-gate issues are also structured.
        for gate in data["gates"].values():
            assert isinstance(gate["issues"], list)
            for issue in gate["issues"]:
                assert set(issue.keys()) >= {"code", "detail", "severity", "message"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 14. test_exit_code_0_on_good_adr
# ---------------------------------------------------------------------------

def test_exit_code_0_on_good_adr():
    with tempfile.NamedTemporaryFile(
        suffix=".md",
        prefix="ADR-042-",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as f:
        f.write(FULL_ADR)
        tmp_path = f.name

    try:
        code, stdout, stderr = _run_quality(tmp_path)
        assert code == 0, f"Expected exit 0 for good ADR, got {code}\nstdout: {stdout}\nstderr: {stderr}"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 15. test_exit_code_1_on_poor_adr
# ---------------------------------------------------------------------------

def test_exit_code_1_on_poor_adr():
    with tempfile.NamedTemporaryFile(
        suffix=".md",
        prefix="ADR-001-",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as f:
        f.write(MINIMAL_POOR_ADR)
        tmp_path = f.name

    try:
        code, stdout, stderr = _run_quality(tmp_path)
        assert code == 1, f"Expected exit 1 for poor ADR, got {code}\nstdout: {stdout}\nstderr: {stderr}"
    finally:
        Path(tmp_path).unlink(missing_ok=True)
