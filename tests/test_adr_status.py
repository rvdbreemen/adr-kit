"""Tests for bin/adr-status — ADR Health Dashboard.

Uses subprocess for CLI integration tests and importlib for unit-testing
pure functions (no .py extension on the binary).
"""
from __future__ import annotations

import importlib.util
import json
import statistics
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_STATUS = REPO_ROOT / "bin" / "adr-status"


# ---------------------------------------------------------------------------
# importlib loader — load pure functions from bin/adr-status (no .py ext)
# ---------------------------------------------------------------------------

def _load_module():
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("adr_status", str(ADR_STATUS))
    spec = importlib.util.spec_from_loader("adr_status", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_module()

extract_status = _mod.extract_status
extract_date = _mod.extract_date
compute_age_days = _mod.compute_age_days
has_enforcement = _mod.has_enforcement
has_valid_enforcement_json = _mod.has_valid_enforcement_json
extract_enforcement_types = _mod.extract_enforcement_types
compute_summary = _mod.compute_summary
find_retirement_candidates = _mod.find_retirement_candidates
load_adr_set = _mod.load_adr_set


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_ENFORCEMENT_JSON = json.dumps({
    "forbid_pattern": [{"pattern": "\\bFoo\\b", "path_glob": "src/**/*.py",
                         "message": "Do not use Foo."}],
    "forbid_import": [],
    "require_pattern": [],
    "llm_judge": False,
})

_BROKEN_ENFORCEMENT_JSON = "{ this is not valid json }"


def _make_adr(
    tmp_path: Path,
    adr_id: str,
    status: str = "Accepted",
    date_str: str | None = None,
    with_enforcement: bool = False,
    broken_enforcement: bool = False,
) -> Path:
    date_line = f"Date: {date_str}." if date_str else ""
    enf_block = ""
    if with_enforcement:
        json_body = _BROKEN_ENFORCEMENT_JSON if broken_enforcement else _MINIMAL_ENFORCEMENT_JSON
        enf_block = f"\n## Enforcement\n\n```json\n{json_body}\n```\n"

    content = f"""# {adr_id} Test ADR

## Status

{status}. {date_line}

## Context

Some context.

## Decision

We decided something.

## Consequences

**Benefits**
- Good

**Trade-offs**
- None
{enf_block}
"""
    path = tmp_path / f"{adr_id}-test-adr.md"
    path.write_text(content, encoding="utf-8")
    return path


def _run_cli(adr_dir: Path, *extra_args: str):
    result = subprocess.run(
        [sys.executable, str(ADR_STATUS), str(adr_dir), *extra_args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result


# ---------------------------------------------------------------------------
# 1. Total count matches ADR files
# ---------------------------------------------------------------------------

def test_total_count_matches_adr_files(tmp_path):
    _make_adr(tmp_path, "ADR-001")
    _make_adr(tmp_path, "ADR-002")
    _make_adr(tmp_path, "ADR-003")
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["total"] == 3


# ---------------------------------------------------------------------------
# 2. Status breakdown — accepted
# ---------------------------------------------------------------------------

def test_status_breakdown_accepted(tmp_path):
    _make_adr(tmp_path, "ADR-001", status="Accepted")
    _make_adr(tmp_path, "ADR-002", status="Accepted")
    _make_adr(tmp_path, "ADR-003", status="Accepted")
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["by_status"]["accepted"] == 3


# ---------------------------------------------------------------------------
# 3. Status breakdown — mix
# ---------------------------------------------------------------------------

def test_status_breakdown_proposed(tmp_path):
    _make_adr(tmp_path, "ADR-001", status="Accepted")
    _make_adr(tmp_path, "ADR-002", status="Proposed")
    _make_adr(tmp_path, "ADR-003", status="Proposed")
    _make_adr(tmp_path, "ADR-004", status="Superseded")
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["by_status"]["accepted"] == 1
    assert summary["by_status"]["proposed"] == 2
    assert summary["by_status"]["superseded"] == 1


# ---------------------------------------------------------------------------
# 4. Health percentage calculation
# ---------------------------------------------------------------------------

def test_health_pct_calculation(tmp_path):
    _make_adr(tmp_path, "ADR-001", status="Accepted")
    _make_adr(tmp_path, "ADR-002", status="Accepted")
    _make_adr(tmp_path, "ADR-003", status="Accepted")
    _make_adr(tmp_path, "ADR-004", status="Proposed")
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["health_pct"] == 75.0


# ---------------------------------------------------------------------------
# 5. Average age calculated correctly
# ---------------------------------------------------------------------------

def test_avg_age_days_calculated(tmp_path):
    known_date = (date.today() - timedelta(days=100)).isoformat()
    _make_adr(tmp_path, "ADR-001", date_str=known_date)
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["avg_age_days"] is not None
    assert abs(summary["avg_age_days"] - 100) <= 1


# ---------------------------------------------------------------------------
# 6. avg_age_days is None (or 0) when no dates present
# ---------------------------------------------------------------------------

def test_avg_age_none_when_no_dates(tmp_path):
    # Write ADR with no date in content
    content = "# ADR-001 No Date\n\n## Status\n\nAccepted.\n\n## Context\n\nNo date here.\n"
    (tmp_path / "ADR-001-no-date.md").write_text(content, encoding="utf-8")
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    # avg_age_days should be None when no ADR has a parseable date
    assert summary["avg_age_days"] is None


# ---------------------------------------------------------------------------
# 7. with_enforcement count
# ---------------------------------------------------------------------------

def test_with_enforcement_count(tmp_path):
    _make_adr(tmp_path, "ADR-001", with_enforcement=True)
    _make_adr(tmp_path, "ADR-002", with_enforcement=True)
    _make_adr(tmp_path, "ADR-003", with_enforcement=False)
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["with_enforcement"] == 2


# ---------------------------------------------------------------------------
# 8. enforcement_valid_pct — 1 valid + 1 broken = 50%
# ---------------------------------------------------------------------------

def test_enforcement_valid_pct(tmp_path):
    _make_adr(tmp_path, "ADR-001", with_enforcement=True, broken_enforcement=False)
    _make_adr(tmp_path, "ADR-002", with_enforcement=True, broken_enforcement=True)
    _make_adr(tmp_path, "ADR-003", with_enforcement=False)
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["with_enforcement"] == 2
    assert summary["enforcement_valid_pct"] == 50.0


# ---------------------------------------------------------------------------
# 9. Retirement candidate — Superseded → confidence high
# ---------------------------------------------------------------------------

def test_retirement_candidate_superseded(tmp_path):
    _make_adr(tmp_path, "ADR-001", status="Superseded")
    adrs = load_adr_set(tmp_path)
    candidates = find_retirement_candidates(adrs)
    assert any(
        c["adr_id"] == "ADR-001" and c["confidence"] == "high"
        for c in candidates
    ), f"Expected high-confidence candidate for Superseded, got: {candidates}"


# ---------------------------------------------------------------------------
# 10. Retirement candidate — Proposed >365 days → confidence medium
# ---------------------------------------------------------------------------

def test_retirement_candidate_old_proposed(tmp_path):
    old_date = (date.today() - timedelta(days=400)).isoformat()
    _make_adr(tmp_path, "ADR-002", status="Proposed", date_str=old_date)
    adrs = load_adr_set(tmp_path)
    candidates = find_retirement_candidates(adrs)
    assert any(
        c["adr_id"] == "ADR-002" and c["confidence"] == "medium"
        for c in candidates
    ), f"Expected medium-confidence candidate for old Proposed, got: {candidates}"


# ---------------------------------------------------------------------------
# 11. JSON output format
# ---------------------------------------------------------------------------

def test_json_output_format(tmp_path):
    _make_adr(tmp_path, "ADR-001")
    result = _run_cli(tmp_path, "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "summary" in data
    assert "adrs" in data
    assert "retirement_candidates" in data


# ---------------------------------------------------------------------------
# 12. JSON has all required fields
# ---------------------------------------------------------------------------

def test_json_has_all_fields(tmp_path):
    today = date.today().isoformat()
    _make_adr(tmp_path, "ADR-001", date_str=today, with_enforcement=True)
    result = _run_cli(tmp_path, "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)

    summary = data["summary"]
    for field in ("total", "by_status", "health_pct", "avg_age_days",
                  "with_enforcement", "enforcement_valid_pct"):
        assert field in summary, f"Missing summary field: {field}"

    for key in ("accepted", "proposed", "superseded", "deprecated", "unknown"):
        assert key in summary["by_status"], f"Missing by_status key: {key}"

    adr_entry = data["adrs"][0]
    for field in ("adr_id", "status", "date", "age_days", "has_enforcement",
                  "enforcement_valid", "enforcement_types", "title"):
        assert field in adr_entry, f"Missing adr entry field: {field}"


# ---------------------------------------------------------------------------
# 13. Table output format
# ---------------------------------------------------------------------------

def test_table_output_format(tmp_path):
    _make_adr(tmp_path, "ADR-001", status="Accepted")
    result = _run_cli(tmp_path, "--format", "table")
    assert result.returncode == 0, result.stderr
    stdout = result.stdout or ""
    assert "ADR-001" in stdout
    assert "Accepted" in stdout
    assert "ADR Health Dashboard" in stdout


# ---------------------------------------------------------------------------
# 14. Markdown output format
# ---------------------------------------------------------------------------

def test_markdown_output_format(tmp_path):
    _make_adr(tmp_path, "ADR-001")
    result = _run_cli(tmp_path, "--format", "markdown")
    assert result.returncode == 0, result.stderr
    assert "# ADR Health Dashboard" in result.stdout
    assert "## Summary" in result.stdout
    assert "## ADR List" in result.stdout


# ---------------------------------------------------------------------------
# 15. Performance: 30 ADRs under 500ms
# ---------------------------------------------------------------------------

def test_performance_under_500ms(tmp_path):
    """Test that processing 30 ADRs completes in under 500ms (in-process, not subprocess).

    We measure only the core work (load + compute + format) to exclude Python
    startup time, which on Windows can be 300-700ms per subprocess invocation.
    """
    today = date.today().isoformat()
    for i in range(1, 31):
        _make_adr(tmp_path, f"ADR-{i:03d}", date_str=today, with_enforcement=(i % 2 == 0))

    def operation():
        adrs = load_adr_set(tmp_path)
        summary = compute_summary(adrs)
        candidates = find_retirement_candidates(adrs)
        _mod.format_json_output(summary, adrs, candidates)

    operation()
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - start) * 1000)
    elapsed_ms = statistics.median(samples)

    assert elapsed_ms < 500, f"Took {elapsed_ms:.0f}ms, expected <500ms"


# ---------------------------------------------------------------------------
# 16. Empty directory returns zero total
# ---------------------------------------------------------------------------

def test_empty_dir_returns_zero_total(tmp_path):
    result = _run_cli(tmp_path, "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# 17. --adr-dir flag works as alternative to positional
# ---------------------------------------------------------------------------

def test_adr_dir_flag(tmp_path):
    _make_adr(tmp_path, "ADR-001")
    result = subprocess.run(
        [sys.executable, str(ADR_STATUS), "--adr-dir", str(tmp_path), "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# Unit tests for pure functions
# ---------------------------------------------------------------------------

def test_extract_status_section():
    content = "# ADR-001 Title\n\n## Status\n\nAccepted. Date: 2024-01-01.\n"
    assert extract_status(content) == "Accepted"


def test_extract_status_bold_inline():
    content = "# ADR-001\n\n**Status:** Proposed\n"
    assert extract_status(content) == "Proposed"


def test_extract_status_does_not_match_status_history():
    content = (
        "# ADR-001\n\n## Status\n\nAccepted.\n\n"
        "## Status History\n\nstatus_history:\n  - status: Proposed\n"
    )
    # Should return Accepted from ## Status, not something from ## Status History
    assert extract_status(content) == "Accepted"


def test_extract_status_unknown():
    content = "# ADR-001\n\nNo status here.\n"
    assert extract_status(content) == "Unknown"


def test_extract_date_iso():
    content = "## Status\n\nAccepted. Date: 2025-03-15.\n"
    assert extract_date(content) == "2025-03-15"


def test_extract_date_none():
    content = "## Status\n\nAccepted.\n"
    assert extract_date(content) is None


def test_compute_age_days_today():
    today = date.today().isoformat()
    age = compute_age_days(today)
    assert age == 0


def test_compute_age_days_none():
    assert compute_age_days(None) is None


def test_has_enforcement_true():
    content = (
        "## Enforcement\n\n"
        "```json\n"
        '{"forbid_pattern": [], "llm_judge": false}\n'
        "```\n"
    )
    assert has_enforcement(content) is True


def test_has_enforcement_false():
    content = "## Context\n\nSome context.\n"
    assert has_enforcement(content) is False


def test_has_valid_enforcement_json_true():
    content = (
        "## Enforcement\n\n"
        "```json\n"
        '{"forbid_pattern": [], "llm_judge": false}\n'
        "```\n"
    )
    assert has_valid_enforcement_json(content) is True


def test_has_valid_enforcement_json_false():
    content = (
        "## Enforcement\n\n"
        "```json\n"
        "{ not valid json }\n"
        "```\n"
    )
    assert has_valid_enforcement_json(content) is False


def test_extract_enforcement_types():
    content = (
        "## Enforcement\n\n"
        "```json\n"
        '{"forbid_pattern": [{"pattern": "Foo"}], "llm_judge": false, "forbid_import": []}\n'
        "```\n"
    )
    types = extract_enforcement_types(content)
    assert "forbid_pattern" in types
    assert "llm_judge" not in types  # false value → not included


def test_enforcement_valid_pct_zero_when_no_enforcement(tmp_path):
    _make_adr(tmp_path, "ADR-001", with_enforcement=False)
    adrs = load_adr_set(tmp_path)
    summary = compute_summary(adrs)
    assert summary["enforcement_valid_pct"] == 0.0


def test_retirement_candidates_sorted_by_confidence(tmp_path):
    _make_adr(tmp_path, "ADR-001", status="Superseded")  # high
    old_date = (date.today() - timedelta(days=400)).isoformat()
    _make_adr(tmp_path, "ADR-002", status="Proposed", date_str=old_date)  # medium
    adrs = load_adr_set(tmp_path)
    candidates = find_retirement_candidates(adrs)
    confidences = [c["confidence"] for c in candidates]
    # high should come before medium
    assert confidences.index("high") < confidences.index("medium")
