"""End-to-end tests for bin/adr-judge --profile and --dry-run-enforcement.

Covers TASK-712 (Performance-Bounded Hooks):
  - --profile: per-rule timing breakdown to stderr with budget reporting
  - --dry-run-enforcement: single-ADR enforcement preview, no state changes
  - Budget warnings driven by .adr-kit.json's judge.pre_commit_timeout_ms

Mirrors test_adr_judge.py's subprocess-driven CLI testing pattern. All tests
set ADR_KIT_NO_LLM=1 so the LLM pass never reaches out to a real `claude`
binary; the LLM row in --profile output still appears (always-on), just with
zero work attributed to it.
"""
import json
import os
import statistics
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_JUDGE = REPO_ROOT / "bin" / "adr-judge"


# ---------- fixtures ----------

BASIC_ADR = """\
# ADR-001 No Foo

## Status

Accepted, 2026-01-01.

## Context

Test.

## Decision

No foo.

## Enforcement

```json
{"forbid_pattern": [{"pattern": "foo\\\\(", "message": "No foo calls"}]}
```
"""

CLEAN_ADR = """\
# ADR-002 No Bar

## Status

Accepted, 2026-01-01.

## Context

Test.

## Decision

No bar.

## Enforcement

```json
{"forbid_pattern": [{"pattern": "bar\\\\(", "message": "No bar calls"}]}
```
"""

# A diff that triggers BASIC_ADR's forbid_pattern (calls `foo(...)`) but
# not CLEAN_ADR's (no `bar(...)`).
FOO_DIFF = """\
diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
+def hello():
+    return foo()
"""

EMPTY_DIFF = ""


# ---------- helpers ----------


def _make_project(tmp_path: Path, adrs: dict, files: dict | None = None,
                  config: dict | None = None) -> Path:
    """Create docs/adr/*.md and optional repo files + .adr-kit.json."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    for name, body in adrs.items():
        (tmp_path / "docs" / "adr" / name).write_text(body, encoding="utf-8")
    for rel, body in (files or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body), encoding="utf-8")
    if config is not None:
        (tmp_path / "docs" / "adr" / ".adr-kit.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
    return tmp_path


def _run(diff_text: str, project_root: Path, *extra_args: str,
         json_mode: bool = False) -> tuple[int, str, str]:
    """Run adr-judge against the project. Returns (returncode, stdout, stderr)."""
    env = os.environ.copy()
    env["ADR_KIT_NO_LLM"] = "1"
    args = [
        sys.executable, str(ADR_JUDGE),
        "--diff", "-",
        "--adr-dir", str(project_root / "docs" / "adr"),
        "--repo-root", str(project_root),
    ]
    if json_mode:
        args.append("--json")
    args.extend(extra_args)
    # Capture as bytes and decode with errors="replace": on Windows the child
    # process can emit cp1252 bytes (em-dashes etc.) via Python's default
    # stderr encoding, which would crash text=True/encoding="utf-8" mode.
    result = subprocess.run(
        args, input=diff_text.encode("utf-8"), capture_output=True, env=env,
    )
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    return result.returncode, stdout, stderr


# ---------- --profile tests ----------


def test_profile_flag_shows_timing_header(tmp_path):
    """--profile prints 'Profile:', a 'Rule' header, and a 'TOTAL' row to stderr."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--profile")
    assert code == 0
    assert "[adr-judge] Profile:" in stderr
    assert "Rule" in stderr
    assert "TOTAL" in stderr


def test_profile_flag_shows_budget_line(tmp_path):
    """--profile prints the 'Budget: pre_commit_timeout_ms=...' summary line."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--profile")
    assert code == 0
    assert "Budget: pre_commit_timeout_ms=" in stderr


def test_profile_no_findings_shows_declarative_row(tmp_path):
    """With no findings, the profile table still shows a 'declarative' bucket row."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--profile")
    assert code == 0
    # Empty diff → no forbid_pattern matches → fallback "declarative" row.
    assert "declarative" in stderr


def test_profile_with_violations_shows_rule_breakdown(tmp_path):
    """A forbid_pattern violation produces a 'forbid_pattern' row in --profile output."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(FOO_DIFF, proj, "--profile")
    assert code == 1, "foo() call should trigger BASIC_ADR's forbid_pattern"
    assert "forbid_pattern" in stderr
    assert "TOTAL" in stderr


def test_profile_budget_from_config(tmp_path):
    """judge.pre_commit_timeout_ms in .adr-kit.json shows up in the budget line."""
    proj = _make_project(
        tmp_path,
        {"ADR-001-no-foo.md": BASIC_ADR},
        config={"judge": {"pre_commit_timeout_ms": 9999}},
    )
    code, _, stderr = _run(EMPTY_DIFF, proj, "--profile")
    assert code == 0
    assert "9999ms" in stderr or "pre_commit_timeout_ms=9999" in stderr


def test_profile_llm_row_always_present(tmp_path):
    """The 'llm_judge' row is always printed in --profile, even with LLM disabled."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--profile")
    assert code == 0
    assert "llm_judge" in stderr


def test_profile_does_not_modify_adr_files(tmp_path):
    """Running with --profile must not mutate any ADR file on disk."""
    adr_path = tmp_path / "docs" / "adr" / "ADR-001-no-foo.md"
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    before = adr_path.read_text(encoding="utf-8")
    mtime_before = adr_path.stat().st_mtime
    _run(FOO_DIFF, proj, "--profile")
    after = adr_path.read_text(encoding="utf-8")
    assert before == after
    assert adr_path.stat().st_mtime == mtime_before


# ---------- --dry-run-enforcement tests ----------


def test_dry_run_enforces_single_adr(tmp_path):
    """--dry-run-enforcement ADR-001 processes only that ADR, ignoring siblings.

    We seed two ADRs: ADR-001 (BASIC) and ADR-002 (CLEAN). The diff calls
    foo() — which only ADR-001 forbids. ADR-002 forbids bar(), which isn't
    in the diff. Without dry-run, both ADRs would be processed but only
    ADR-001 would fire. With dry-run on ADR-001, the finding's `adr` field
    should be ADR-001 (and only ADR-001).
    """
    proj = _make_project(
        tmp_path,
        {"ADR-001-no-foo.md": BASIC_ADR, "ADR-002-no-bar.md": CLEAN_ADR},
    )
    code, stdout, _ = _run(
        FOO_DIFF, proj, "--dry-run-enforcement", "ADR-001", json_mode=True,
    )
    assert code == 1
    payload = json.loads(stdout)
    assert payload["summary"]["adrs_checked"] == 1
    assert all(f["adr"] == "ADR-001" for f in payload["findings"])


def test_dry_run_prints_announcement(tmp_path):
    """Dry-run mode announces itself on stderr with the (no state changes written) tag."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--dry-run-enforcement", "ADR-001")
    assert code == 0
    assert "dry-run-enforcement: ADR-001 (no state changes written)" in stderr


def test_dry_run_no_state_changes(tmp_path):
    """ADR files on disk must be byte-identical after a --dry-run-enforcement run."""
    adr_path = tmp_path / "docs" / "adr" / "ADR-001-no-foo.md"
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    before = adr_path.read_text(encoding="utf-8")
    _run(FOO_DIFF, proj, "--dry-run-enforcement", "ADR-001")
    after = adr_path.read_text(encoding="utf-8")
    assert before == after


def test_dry_run_not_found_exits_2(tmp_path):
    """--dry-run-enforcement ADR-999 (nonexistent) exits 2 with a WARN message."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--dry-run-enforcement", "ADR-999")
    assert code == 2
    assert "ADR-999" in stderr
    assert "not found" in stderr


def test_dry_run_bad_format_exits_2(tmp_path):
    """A non-numeric id like 'BAD-FORMAT' is rejected up front with exit 2."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(EMPTY_DIFF, proj, "--dry-run-enforcement", "BAD-FORMAT")
    assert code == 2
    assert "ERROR" in stderr
    assert "dry-run-enforcement" in stderr


def test_dry_run_no_violation_exit_0(tmp_path):
    """Dry-run on a clean ADR (no violating content in diff) returns 0."""
    proj = _make_project(tmp_path, {"ADR-002-no-bar.md": CLEAN_ADR})
    # FOO_DIFF triggers foo(), but CLEAN_ADR forbids bar() — no overlap.
    code, stdout, _ = _run(
        FOO_DIFF, proj, "--dry-run-enforcement", "ADR-002", json_mode=True,
    )
    assert code == 0
    payload = json.loads(stdout)
    assert payload["summary"]["violations"] == 0


def test_dry_run_with_violation_exit_1(tmp_path):
    """Dry-run on an ADR whose rules the diff violates returns 1."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, _ = _run(FOO_DIFF, proj, "--dry-run-enforcement", "ADR-001")
    assert code == 1


def test_dry_run_accepts_short_form(tmp_path):
    """Normalisation: '1', '001', 'ADR-1', 'ADR-001' all resolve to ADR-001."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    for form in ("ADR-001", "ADR-1", "001", "1"):
        code, _, stderr = _run(EMPTY_DIFF, proj, "--dry-run-enforcement", form)
        assert code == 0, f"form {form!r} should resolve to ADR-001"
        assert "ADR-001" in stderr


# ---------- combined-flag tests ----------


def test_profile_combined_with_dry_run(tmp_path):
    """--profile and --dry-run-enforcement together: both behaviours fire."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, _, stderr = _run(
        FOO_DIFF, proj, "--profile", "--dry-run-enforcement", "ADR-001",
    )
    assert code == 1
    assert "[adr-judge] Profile:" in stderr
    assert "dry-run-enforcement: ADR-001 (no state changes written)" in stderr
    assert "TOTAL" in stderr


def test_profile_combined_with_json(tmp_path):
    """--profile with --json: JSON to stdout, profile table to stderr."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": BASIC_ADR})
    code, stdout, stderr = _run(FOO_DIFF, proj, "--profile", json_mode=True)
    assert code == 1
    payload = json.loads(stdout)  # stdout must remain valid JSON
    assert payload["summary"]["violations"] == 1
    assert "[adr-judge] Profile:" in stderr


# ---------- wall-clock performance tests (slow, opt-in) ----------


def _make_synthetic_adrs(tmp_path, count=50):
    """Create count synthetic ADR files with Enforcement blocks."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for i in range(1, count + 1):
        adr_file = adr_dir / f"ADR-{i:03d}-synthetic-decision.md"
        adr_file.write_text(f"""# ADR-{i:03d}: Synthetic Decision {i}

## Status
Accepted

## Context
This is a synthetic ADR for performance testing. It covers topic {i}.

## Decision
We decided to use approach {i} for this component.

## Consequences
Performance improvement of approximately {i * 2}%.

## Enforcement
```json
{{
  "rules": [{{
    "id": "rule-{i}",
    "name": "No forbidden pattern {i}",
    "type": "forbid_pattern",
    "pattern": "FORBIDDEN_PATTERN_{i}",
    "message": "Found forbidden pattern {i}"
  }}]
}}
```
""")
    return adr_dir


@pytest.mark.slow
def test_adr_judge_performance_50_adrs(tmp_path):
    """adr-judge on 50 ADRs + 100-file synthetic diff should complete in < 3000ms."""
    adr_dir = _make_synthetic_adrs(tmp_path, 50)
    # Create synthetic diff with 100 files
    diff_lines = []
    for f in range(100):
        diff_lines.append(f"diff --git a/src/file{f}.py b/src/file{f}.py")
        diff_lines.append(f"--- a/src/file{f}.py")
        diff_lines.append(f"+++ b/src/file{f}.py")
        diff_lines.append("@@ -1,3 +1,4 @@")
        diff_lines.append("+# added line")
        diff_lines.append(" existing line")
    diff_content = "\n".join(diff_lines)

    judge_path = Path(__file__).parent.parent / "bin" / "adr-judge"
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(judge_path), "--diff", "-", "--adr-dir", str(adr_dir)],
        input=diff_content, capture_output=True, text=True
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"adr-judge took {elapsed:.2f}s on 50 ADRs (limit: 3s)"


@pytest.mark.slow
def test_adr_status_performance_50_adrs(tmp_path):
    """Warm median adr-status latency on 50 ADRs should stay below 500ms."""
    adr_dir = _make_synthetic_adrs(tmp_path, 50)
    status_path = Path(__file__).parent.parent / "bin" / "adr-status"
    command = [sys.executable, str(status_path), str(adr_dir), "--format", "json"]
    subprocess.run(command, capture_output=True, text=True, check=True)
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        subprocess.run(command, capture_output=True, text=True, check=True)
        samples.append(time.perf_counter() - start)
    elapsed = statistics.median(samples)
    assert elapsed < 0.5, f"adr-status took {elapsed:.2f}s on 50 ADRs (limit: 500ms)"


@pytest.mark.slow
def test_adr_context_performance_50_adrs(tmp_path):
    """Warm median adr-context latency on 50 ADRs should stay below 600ms."""
    adr_dir = _make_synthetic_adrs(tmp_path, 50)
    context_path = Path(__file__).parent.parent / "bin" / "adr-context"
    command = [
        sys.executable,
        str(context_path),
        "--adr-dir",
        str(adr_dir),
        "performance optimization backend",
    ]
    subprocess.run(command, capture_output=True, text=True, check=True)
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        subprocess.run(command, capture_output=True, text=True, check=True)
        samples.append(time.perf_counter() - start)
    elapsed = statistics.median(samples)
    # 600ms budget: Python subprocess cold-start on Windows is ~300-400ms baseline
    assert elapsed < 0.6, f"adr-context took {elapsed:.2f}s on 50 ADRs (limit: 600ms)"
