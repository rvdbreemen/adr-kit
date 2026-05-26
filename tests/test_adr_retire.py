"""Tests for the v0.14 deterministic ADR retirement report."""

import json
import runpy
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_RETIRE = REPO_ROOT / "bin" / "adr-retire"
RETIRE = runpy.run_path(str(ADR_RETIRE))


def adr(status="Accepted", day="2026-01-01", decision="Use `Redis`.", enforcement=""):
    return (
        "# ADR-001 Example\n\n"
        f"## Status\n\n{status}, {day}.\n\n"
        "## Status History\n\n```yaml\nstatus_history:\n"
        f"  - date: {day}\n"
        f"    status: {status}\n"
        "    changed_by: test\n"
        "    reason: test\n"
        "    changed_via: pytest\n"
        "```\n\n"
        "## Decision\n\n"
        f"{decision}\n\n"
        f"{enforcement}"
    )


def project(tmp_path, files):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for name, content in files.items():
        (adr_dir / name).write_text(content, encoding="utf-8")
    return adr_dir


def run_retire(adr_dir, *extra):
    return subprocess.run(
        [sys.executable, str(ADR_RETIRE), str(adr_dir), "--repo-root", str(adr_dir.parent.parent), *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_staleness_scores_old_history():
    score = RETIRE["detect_90day_staleness"](
        "ADR-001", adr(day="2026-01-01"), {}, date(2026, 5, 26)
    )
    assert score == 1.0


def test_staleness_keeps_recent_history():
    score = RETIRE["detect_90day_staleness"](
        "ADR-001", adr(day="2026-05-20"), {}, date(2026, 5, 26)
    )
    assert score == 0.0


def test_staleness_uses_status_date_without_history():
    text = "# ADR-001 Example\n\n## Status\n\nAccepted, 2026-01-01.\n"
    assert RETIRE["detect_90day_staleness"]("ADR-001", text, {}, date(2026, 5, 26)) == 1.0


def test_staleness_unknown_date_is_not_a_retirement_signal():
    assert RETIRE["detect_90day_staleness"]("ADR-001", "## Status\n\nAccepted.\n", {}) == 0.0


def test_technology_missing_from_source_scores_one(tmp_path):
    assert RETIRE["detect_tech_removal"]("ADR-001", adr(), tmp_path) == 1.0


def test_technology_present_in_source_scores_zero(tmp_path):
    (tmp_path / "service.py").write_text("client = Redis()", encoding="utf-8")
    assert RETIRE["detect_tech_removal"]("ADR-001", adr(), tmp_path) == 0.0


def test_technology_without_explicit_identifier_is_not_guessed(tmp_path):
    text = adr(decision="Use a durable cache.")
    assert RETIRE["detect_tech_removal"]("ADR-001", text, tmp_path) == 0.0


def test_broken_supersession_is_detected():
    text = adr(decision="Superseded by ADR-9.")
    assert RETIRE["detect_supersession_broken"]("ADR-001", text, ["ADR-001"]) == 1.0


def test_existing_supersession_target_is_normalized():
    text = adr(decision="Superseded by ADR-9.")
    assert RETIRE["detect_supersession_broken"]("ADR-001", text, ["ADR-001", "ADR-009"]) == 0.0


def test_superseded_status_still_reports_broken_target(tmp_path):
    text = adr(status="Superseded by ADR-999", decision="No marker.")
    result = RETIRE["score_adr"]("ADR-001", text, ["ADR-001"], tmp_path, {})
    assert result["signals"]["broken_supersession"] == 1.0


def test_supersession_signal_can_be_disabled_by_config(tmp_path):
    text = adr(status="Superseded by ADR-999", decision="No marker.")
    config = {"retirement": {"check_supersession": False}}
    result = RETIRE["score_adr"]("ADR-001", text, ["ADR-001"], tmp_path, config)
    assert result["signals"]["broken_supersession"] == 0.0


def test_policy_mismatch_flags_broad_wildcard_rule():
    block = '## Enforcement\n\n```json\n{"forbid_pattern": [{"pattern": ".*", "path_glob": "**/*"}]}\n```\n'
    assert RETIRE["detect_policy_mismatch"]("ADR-001", adr(enforcement=block), {}) == 1.0


def test_policy_mismatch_accepts_bounded_rule():
    block = '## Enforcement\n\n```json\n{"forbid_pattern": [{"pattern": "\\\\bRedis\\\\b", "path_glob": "src/**/*.py"}]}\n```\n'
    assert RETIRE["detect_policy_mismatch"]("ADR-001", adr(enforcement=block), {}) == 0.0


def test_score_is_average_of_four_signals(tmp_path):
    block = '## Enforcement\n\n```json\n{"forbid_pattern": [{"pattern": ".*", "path_glob": "**/*"}]}\n```\n'
    text = adr(day="2026-01-01", decision="Use `GoneTech`. Superseded by ADR-999.", enforcement=block)
    result = RETIRE["score_adr"]("ADR-001", text, ["ADR-001"], tmp_path, {}, date(2026, 5, 26))
    assert result["retirement_score"] == 1.0
    assert result["recommendation"] == "RETIRE"


def test_non_accepted_adr_has_zero_signals(tmp_path):
    result = RETIRE["score_adr"]("ADR-001", adr(status="Proposed"), ["ADR-001"], tmp_path, {})
    assert result["retirement_score"] == 0.0
    assert all(value == 0.0 for value in result["signals"].values())


def test_recommendation_boundaries(tmp_path):
    text = adr(day="2026-01-01", decision="No technology marker.")
    result = RETIRE["score_adr"]("ADR-001", text, ["ADR-001"], tmp_path, {}, date(2026, 5, 26))
    assert result["retirement_score"] == 0.25
    assert result["recommendation"] == "KEEP"


def test_json_output_includes_all_signal_scores(tmp_path):
    adr_dir = project(tmp_path, {"ADR-001-example.md": adr()})
    result = run_retire(adr_dir, "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert set(payload[0]["signals"]) == {
        "staleness_90day", "tech_removal", "broken_supersession", "policy_mismatch"
    }


def test_markdown_output_is_human_readable(tmp_path):
    adr_dir = project(tmp_path, {"ADR-001-example.md": adr()})
    result = run_retire(adr_dir, "--format", "markdown")
    assert "# ADR Retirement Candidates" in result.stdout
    assert "| Signal | Score |" in result.stdout


def test_threshold_filters_lower_scores(tmp_path):
    adr_dir = project(tmp_path, {"ADR-001-example.md": adr(day="2026-05-25", decision="No marker.")})
    result = run_retire(adr_dir, "--threshold", "0.4", "--format", "json")
    assert json.loads(result.stdout) == []


def test_no_adr_directory_reports_empty_result(tmp_path):
    result = run_retire(tmp_path / "missing", "--format", "json")
    assert result.returncode == 0
    assert json.loads(result.stdout) == []


def test_malformed_config_returns_configuration_error(tmp_path):
    adr_dir = project(tmp_path, {"ADR-001-example.md": adr()})
    config = tmp_path / "bad.json"
    config.write_text("{broken", encoding="utf-8")
    result = run_retire(adr_dir, "--config", str(config))
    assert result.returncode == 2
    assert "Malformed config" in result.stderr


def test_thirty_adr_scan_meets_budget(tmp_path):
    adr_dir = project(
        tmp_path,
        {f"ADR-{number:03d}-example.md": adr(decision="No marker.") for number in range(1, 31)},
    )
    start = time.perf_counter()
    result = run_retire(adr_dir, "--format", "json")
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert len(json.loads(result.stdout)) == 30
    assert elapsed < 2.0
