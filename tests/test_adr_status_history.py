"""Tests for v0.14 status-history parsing, migration, and audit checks."""

import json
import runpy
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_JUDGE = REPO_ROOT / "bin" / "adr-judge"
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"
JUDGE = runpy.run_path(str(ADR_JUDGE))


def entry(day="2026-05-01", status="Accepted"):
    return {
        "date": day,
        "status": status,
        "changed_by": "tester",
        "reason": "Reviewed",
        "changed_via": "pytest",
    }


def history_block(*entries):
    lines = ["## Status History", "", "```yaml", "status_history:"]
    for item in entries:
        lines.extend(
            [
                f"  - date: {item['date']}",
                f"    status: {item['status']}",
                f"    changed_by: {item['changed_by']}",
                f"    reason: {item['reason']}",
                f"    changed_via: {item['changed_via']}",
            ]
        )
    lines.append("```")
    return "\n".join(lines)


def adr_text(status="Accepted", history=""):
    middle = f"\n{history}\n" if history else "\n"
    return (
        "# ADR-001 Test Status History\n\n"
        f"## Status\n\n{status}, 2026-05-01.\n"
        f"{middle}"
        "## Context\n\nContext.\n\n"
        "## Decision\n\nDecision.\n\n"
        "## Alternatives Considered\n\n- A: rejected.\n- B: rejected.\n\n"
        "## Consequences\n\n**Positive:** Yes.\n\n**Negative:** No.\n\n"
        "## Related Decisions\n\n- None.\n\n"
        "## References\n\n- test.\n"
    )


def write_adr(tmp_path, body):
    path = tmp_path / "ADR-001-test-status-history.md"
    path.write_text(body, encoding="utf-8")
    return path


def run_lint(path, *extra):
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", *extra, str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, json.loads(result.stdout)


def test_parse_status_history_valid_multiple_entries():
    parsed = JUDGE["parse_status_history"](
        adr_text("Accepted", history_block(entry("2026-04-01", "Proposed"), entry()))
    )
    assert [item["status"] for item in parsed] == ["Proposed", "Accepted"]


def test_parse_status_history_missing_is_backward_compatible():
    assert JUDGE["parse_status_history"](adr_text()) == []


def test_parse_status_history_accepts_quoted_scalars():
    parsed = JUDGE["parse_status_history"](
        'status_history:\n  - date: "2026-05-01"\n    status: "Accepted"\n'
    )
    assert parsed[0] == {"date": "2026-05-01", "status": "Accepted"}


def test_validate_requires_all_entry_fields():
    assert "missing fields" in JUDGE["validate_status_history"]([{"date": "2026-05-01"}])[0]


def test_validate_rejects_bad_date():
    invalid = entry(day="yesterday")
    assert "invalid date" in JUDGE["validate_status_history"]([invalid])[0]


def test_validate_rejects_future_date():
    future = entry(day=(date.today() + timedelta(days=1)).isoformat())
    assert "future date" in JUDGE["validate_status_history"]([future])[0]


def test_validate_rejects_non_chronological_entries():
    issues = JUDGE["validate_status_history"]([entry("2026-05-02"), entry("2026-05-01")])
    assert any("earlier" in issue for issue in issues)


def test_validate_checks_latest_status_against_header():
    issues = JUDGE["validate_status_history"]([entry(status="Proposed")], "Accepted")
    assert any("does not match" in issue for issue in issues)


def test_append_preserves_existing_entry_and_adds_one(tmp_path):
    path = write_adr(tmp_path, adr_text("Accepted", history_block(entry("2026-04-01", "Proposed"))))
    original = JUDGE["parse_status_history"](path.read_text(encoding="utf-8"))[0]
    assert JUDGE["append_to_status_history"](path, entry())
    parsed = JUDGE["parse_status_history"](path.read_text(encoding="utf-8"))
    assert parsed[0] == original
    assert len(parsed) == 2


def test_append_creates_status_history_for_legacy_adr(tmp_path):
    path = write_adr(tmp_path, adr_text())
    assert JUDGE["append_to_status_history"](path, entry())
    assert "## Status History" in path.read_text(encoding="utf-8")


def test_append_rejects_invalid_new_entry_without_writing(tmp_path):
    path = write_adr(tmp_path, adr_text())
    before = path.read_text(encoding="utf-8")
    assert not JUDGE["append_to_status_history"](path, {"date": "2026-05-01"})
    assert path.read_text(encoding="utf-8") == before


def test_append_rejects_transition_earlier_than_history(tmp_path):
    path = write_adr(tmp_path, adr_text("Accepted", history_block(entry("2026-05-02"))))
    assert not JUDGE["append_to_status_history"](path, entry("2026-05-01"))


def test_append_rejects_malformed_existing_history(tmp_path):
    malformed = history_block({"date": "bad", "status": "Accepted", "changed_by": "x", "reason": "x", "changed_via": "x"})
    path = write_adr(tmp_path, adr_text("Accepted", malformed))
    assert not JUDGE["append_to_status_history"](path, entry())


def test_migrate_status_history_adds_initial_canonical_entry(tmp_path):
    path = write_adr(tmp_path, adr_text())
    assert JUDGE["migrate_status_history"](path)
    assert JUDGE["parse_status_history"](path.read_text(encoding="utf-8"))[0]["status"] == "Accepted"


def test_migrate_status_history_supports_bold_inline_legacy_status(tmp_path):
    path = write_adr(tmp_path, "# ADR-001 Old\n\n**Status:** Proposed\n\n## Context\n\nOld.\n")
    assert JUDGE["migrate_status_history"](path)
    assert JUDGE["parse_status_history"](path.read_text(encoding="utf-8"))[0]["status"] == "Proposed"


def test_migration_is_idempotent(tmp_path):
    path = write_adr(tmp_path, adr_text())
    assert JUDGE["migrate_status_history"](path)
    assert not JUDGE["migrate_status_history"](path)
    assert len(JUDGE["parse_status_history"](path.read_text(encoding="utf-8"))) == 1


def test_normal_judge_run_does_not_auto_migrate(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = write_adr(adr_dir, adr_text())
    result = subprocess.run(
        [sys.executable, str(ADR_JUDGE), "--adr-dir", str(adr_dir), "--json"],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert "status_history:" not in path.read_text(encoding="utf-8")


def test_migrate_cli_reports_modified_adr_ids(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    write_adr(adr_dir, adr_text())
    result = subprocess.run(
        [
            sys.executable,
            str(ADR_JUDGE),
            "--adr-dir",
            str(adr_dir),
            "--migrate-status-history",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"migrated": ["ADR-001"], "count": 1}


def test_audit_gate_accepts_valid_history(tmp_path):
    path = write_adr(tmp_path, adr_text("Accepted", history_block(entry())))
    code, out = run_lint(path, "--gates", "audit")
    assert code == 0
    assert out["files"][0]["findings"] == []


def test_audit_gate_leaves_unmigrated_legacy_adr_compatible(tmp_path):
    path = write_adr(tmp_path, adr_text())
    code, out = run_lint(path, "--gates", "audit")
    assert code == 0
    assert out["files"][0]["bucket"] == "PASS"


def test_audit_gate_fails_missing_required_field(tmp_path):
    block = history_block({**entry(), "reason": ""})
    path = write_adr(tmp_path, adr_text("Accepted", block))
    code, out = run_lint(path, "--gates", "audit")
    assert code == 1
    assert "missing fields" in out["files"][0]["findings"][0]["summary"]


def test_audit_gate_fails_future_transition(tmp_path):
    block = history_block(entry((date.today() + timedelta(days=1)).isoformat()))
    path = write_adr(tmp_path, adr_text("Accepted", block))
    code, out = run_lint(path, "--gates", "audit")
    assert code == 1
    assert "future date" in out["files"][0]["findings"][0]["summary"]


def test_audit_gate_fails_status_mismatch(tmp_path):
    path = write_adr(tmp_path, adr_text("Accepted", history_block(entry(status="Proposed"))))
    code, out = run_lint(path, "--gates", "audit")
    assert code == 1
    assert "does not match" in out["files"][0]["findings"][0]["summary"]


def test_audit_gate_checks_bold_inline_status_after_migration(tmp_path):
    body = "# ADR-001 Old\n\n**Status:** Accepted\n\n" + history_block(entry(status="Proposed"))
    path = write_adr(tmp_path, body)
    code, out = run_lint(path, "--gates", "audit")
    assert code == 1
    assert "does not match" in out["files"][0]["findings"][0]["summary"]


def test_parse_and_append_meet_small_set_budget(tmp_path):
    path = write_adr(tmp_path, adr_text("Accepted", history_block(entry("2026-04-01"))))
    text = path.read_text(encoding="utf-8")
    start = time.perf_counter()
    for _ in range(30):
        JUDGE["parse_status_history"](text)
    parse_elapsed = time.perf_counter() - start
    start = time.perf_counter()
    assert JUDGE["append_to_status_history"](path, entry())
    append_elapsed = time.perf_counter() - start
    assert parse_elapsed < 0.05
    assert append_elapsed < 0.1
