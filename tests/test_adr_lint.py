"""End-to-end tests for bin/adr-lint.

Each test runs the CLI as a subprocess and asserts on the JSON output and exit
code. This verifies the public interface, not internal helpers.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def run_lint(*args):
    """Invoke adr-lint with --format json and return (exit_code, parsed_json)."""
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, {"_stdout": result.stdout, "_stderr": result.stderr}


def test_canonical_pass():
    code, out = run_lint(str(FIXTURES / "canonical"))
    assert code == 0
    assert out["summary"] == {"pass": 1, "advisory": 0, "fail": 0, "skipped": 0, "total": 1}


def test_missing_headings_fails_default():
    code, out = run_lint(str(FIXTURES / "missing-headings"))
    assert code == 1
    assert out["summary"]["fail"] == 1
    fnd = out["files"][0]["findings"]
    assert any(f["gate"] == "completeness" and f["level"] == "FAIL" for f in fnd)


def _completeness_details(out):
    for f in out["files"][0]["findings"]:
        if f["gate"] == "completeness" and f["level"] == "FAIL":
            return f["details"]
    return None


def test_present_but_empty_required_section_fails_completeness():
    """A heading on its own is not a section (TASK-198).

    The gate used to test only that the heading matched somewhere in the text,
    so an empty required section passed. `bin/adr accept` runs this gate with
    --strict, which made that enough to accept a record carrying no verifiable
    reference at all.
    """
    code, out = run_lint("--gates", "completeness", str(FIXTURES / "empty-section"))
    assert code == 1
    details = _completeness_details(out)
    assert details is not None
    # The reason has to separate "you never wrote this" from "it is hollow",
    # otherwise the author cannot tell what the gate is asking for.
    assert any("References" in d and "empty" in d for d in details)


def test_placeholder_only_required_section_fails_completeness():
    """The TODO that adr-migrate writes is a hole, not content (TASK-198).

    Without this, migrate and accept together walk an unfinished record into an
    immutable Accepted state, because the placeholder counts as a non-empty body.
    """
    code, out = run_lint(
        "--gates", "completeness", str(FIXTURES / "placeholder-section")
    )
    assert code == 1
    details = _completeness_details(out)
    assert details is not None
    assert any("References" in d for d in details)


def test_absent_section_still_reported_as_plain_missing():
    """The original reason must not be swallowed by the new one (TASK-198)."""
    code, out = run_lint("--gates", "completeness", str(FIXTURES / "missing-headings"))
    assert code == 1
    details = _completeness_details(out)
    assert details is not None
    assert any("empty" not in d for d in details)


def test_bad_filename_consistency_fail():
    code, out = run_lint(str(FIXTURES / "bad-filename"))
    assert code == 1
    fnd = out["files"][0]["findings"]
    assert any(f["gate"] == "consistency" and f["level"] == "FAIL" for f in fnd)


def test_heading_mismatch_consistency_fail():
    code, out = run_lint(str(FIXTURES / "heading-mismatch"))
    assert code == 1
    fnd = out["files"][0]["findings"]
    assert any(f["gate"] == "consistency" and f["level"] == "FAIL" for f in fnd)


def test_marker_skip_whole_file():
    code, out = run_lint(str(FIXTURES / "marker-skip"))
    assert code == 0
    assert out["files"][0]["bucket"] == "SKIPPED"
    assert out["files"][0]["skip_reason"] == "marker"


def test_marker_advisory_demotes_failures():
    code, out = run_lint(str(FIXTURES / "marker-advisory"))
    assert code == 0  # ADVISORY only, no FAIL.
    assert out["summary"]["advisory"] == 1
    assert out["summary"]["fail"] == 0
    fnd = out["files"][0]["findings"]
    assert all(f["level"] == "ADVISORY" for f in fnd)


def test_marker_skip_gate_only():
    code, out = run_lint(str(FIXTURES / "marker-skip-gate"))
    # Completeness skipped; consistency still runs but should pass for this fixture.
    assert code == 0
    assert all(
        f["gate"] != "completeness" for f in out["files"][0]["findings"]
    )


def test_strict_from_boundary():
    """ADR-001 (legacy) should be ADVISORY, ADR-100 (recent) should be PASS."""
    code, out = run_lint(str(FIXTURES / "with-policy"))
    by_num = {f["adr_num"]: f for f in out["files"]}
    assert by_num[1]["bucket"] == "ADVISORY"
    assert by_num[100]["bucket"] == "PASS"
    assert code == 0


def test_strict_from_override_via_cli():
    """--strict-from on the command line overrides the config file."""
    # Override to ADR-001, making the legacy-shape file post-boundary -> FAIL.
    code, out = run_lint(
        "--strict-from", "ADR-001",
        str(FIXTURES / "with-policy"),
    )
    by_num = {f["adr_num"]: f for f in out["files"]}
    assert by_num[1]["bucket"] == "FAIL"
    assert code == 1


def test_gates_filter():
    """--gates limits which checks run."""
    code, out = run_lint(
        "--gates", "completeness",
        str(FIXTURES / "bad-filename"),
    )
    # Filename pattern would normally FAIL consistency, but --gates limits to completeness.
    assert code == 0  # ADR-003 has all canonical sections so completeness passes.
    fnd = out["files"][0]["findings"]
    assert all(f["gate"] == "completeness" for f in fnd)


def test_bad_config_exits_2():
    code, out = run_lint(str(FIXTURES / "bad-config"))
    assert code == 2


def test_unknown_gate_exits_2():
    code, out = run_lint("--gates", "fizzbuzz", str(FIXTURES / "canonical"))
    assert code == 2


def test_missing_path_exits_2():
    code, out = run_lint(str(FIXTURES / "this-does-not-exist"))
    assert code == 2


def test_single_file_lints():
    code, out = run_lint(str(FIXTURES / "canonical" / "ADR-001-clean-baseline.md"))
    assert code == 0
    assert out["summary"]["total"] == 1


def _write_pair(adr_dir: Path) -> Path:
    """Write a clean, bidirectionally linked supersession pair; return the successor."""
    adr_dir.mkdir(parents=True, exist_ok=True)
    (adr_dir / "ADR-001-old-decision.md").write_text(
        '---\nid: "ADR-001"\ntitle: "Old Decision"\nstatus: "Superseded"\n'
        'date: "2026-07-06"\nbinding: false\ngate: null\n'
        "documents_shipped: false\nverified_in: []\nsupersedes: []\n"
        'superseded_by: "ADR-002"\n---\n'
        "# ADR-001 Old Decision\n\n## Status\n\nSuperseded by ADR-002, 2026-07-06.\n",
        encoding="utf-8",
    )
    successor = adr_dir / "ADR-002-new-decision.md"
    successor.write_text(
        '---\nid: "ADR-002"\ntitle: "New Decision"\nstatus: "Accepted"\n'
        'date: "2026-07-06"\nbinding: false\ngate: null\n'
        "documents_shipped: false\nverified_in: []\nsupersedes:\n"
        '  - "ADR-001"\nsuperseded_by: null\n---\n'
        "# ADR-002 New Decision\n\n## Status\n\nAccepted, 2026-07-06.\n\n"
        "## Related Decisions\n\n- Supersedes ADR-001.\n",
        encoding="utf-8",
    )
    return successor


def test_single_file_cannot_resolve_a_cross_reference_without_context(tmp_path):
    """The scoping TASK-67 describes: one file, so the target resolves to nothing."""
    successor = _write_pair(tmp_path / "docs" / "adr")

    code, out = run_lint("--gates", "consistency", str(successor))

    assert code == 1
    summaries = [f["summary"] for f in out["files"][0]["findings"]]
    assert any("supersedes target ADR-001 not found" in s for s in summaries)


def test_context_dir_resolves_cross_references_for_a_single_target(tmp_path):
    """TASK-67: the directory is lookup context; the verdict stays about one file."""
    adr_dir = tmp_path / "docs" / "adr"
    successor = _write_pair(adr_dir)

    code, out = run_lint(
        "--gates", "consistency", "--context-dir", str(adr_dir), str(successor)
    )

    assert code == 0, out
    assert out["summary"]["total"] == 1
    assert out["files"][0]["file"] == "ADR-002-new-decision.md"


def test_context_dir_does_not_leak_an_unrelated_files_findings(tmp_path):
    """A broken ADR elsewhere in the context directory is not this file's problem."""
    adr_dir = tmp_path / "docs" / "adr"
    successor = _write_pair(adr_dir)
    (adr_dir / "ADR-003-broken-decision.md").write_text(
        '---\nid: "ADR-003"\ntitle: "Broken Decision"\nstatus: "Superseded"\n'
        'date: "2026-07-06"\nbinding: false\ngate: null\n'
        "documents_shipped: false\nverified_in: []\nsupersedes:\n"
        '  - "ADR-404"\nsuperseded_by: null\n---\n'
        "# ADR-003 Broken Decision\n\n## Status\n\nSuperseded, 2026-07-06.\n",
        encoding="utf-8",
    )

    code, out = run_lint(
        "--gates", "consistency", "--context-dir", str(adr_dir), str(successor)
    )

    assert code == 0, out
    assert out["summary"]["total"] == 1
    assert "ADR-404" not in json.dumps(out["files"])


def test_context_dir_does_not_count_the_target_twice_as_a_duplicate(tmp_path):
    """The context directory contains the target; identity is the resolved path."""
    adr_dir = tmp_path / "docs" / "adr"
    successor = _write_pair(adr_dir)

    result = subprocess.run(
        [
            sys.executable, str(ADR_LINT), "--format", "json",
            "--gates", "consistency",
            # Relative context dir against an absolute target: the same file
            # reached by two spellings must still be one file.
            "--context-dir", "docs/adr", str(successor.resolve()),
        ],
        capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path),
    )
    out = json.loads(result.stdout)

    assert result.returncode == 0, result.stdout + result.stderr
    assert out["summary"]["total"] == 1
    assert "duplicate" not in json.dumps(out["files"])


def test_missing_context_dir_exits_2(tmp_path):
    successor = _write_pair(tmp_path / "docs" / "adr")

    code, out = run_lint(
        "--context-dir", str(tmp_path / "nope"), str(successor)
    )

    assert code == 2


def test_human_format_runs():
    """Human format produces non-JSON output and still exits cleanly."""
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "human", str(FIXTURES / "canonical")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0
    assert "PASS strictly (1)" in result.stdout
    assert "Aggregate:" in result.stdout
