"""Tests for the ADR_KIT_OVERRIDE audit trail (task-10).

A judge FAIL can be overridden for ONE named ADR per commit via the
ADR_KIT_OVERRIDE env var ("ADR-NNN: reason"). The override:
  - downgrades only that ADR's violations (others still block),
  - refuses an empty reason,
  - appends a JSONL record to docs/adr/.adr-kit-overrides.jsonl,
  - is reconcilable against ADR-Override commit trailers via
    `adr-judge --audit-overrides` (read-only report).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_JUDGE = REPO_ROOT / "bin" / "adr-judge"

OVERRIDE_LOG = ".adr-kit-overrides.jsonl"


def _adr(num: int, word: str) -> str:
    """Canonical Accepted ADR forbidding `word` in src/**/*.py."""
    return textwrap.dedent(f"""\
        # ADR-{num:03d} No {word}

        ## Status

        Accepted, 2026-04-25.

        ## Context

        {word} fragments the heap.

        ## Decision

        Don't use {word}.

        ## Alternatives Considered

        - Use {word}: rejected.

        ## Consequences

        **Negative:**
        - Need an alternative.

        ## Related Decisions

        - None.

        ## References

        - None.

        ## Enforcement

        ```json
        {{
          "forbid_pattern": [
            {{"pattern": "\\\\b{word}\\\\b", "path_glob": "src/**/*.py",
              "message": "No {word}."}}
          ]
        }}
        ```
        """)


def _make_project(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-no-foo.md").write_text(_adr(1, "Foo"), encoding="utf-8")
    (adr_dir / "ADR-002-no-bar.md").write_text(_adr(2, "Bar"), encoding="utf-8")
    return tmp_path


DIFF_BOTH = """\
diff --git a/src/test.py b/src/test.py
--- a/src/test.py
+++ b/src/test.py
@@ -1 +1,3 @@
+def hello():
+    x = Foo()
+    y = Bar()
"""

DIFF_FOO_ONLY = """\
diff --git a/src/test.py b/src/test.py
--- a/src/test.py
+++ b/src/test.py
@@ -1 +1,2 @@
+def hello():
+    return Foo()
"""


def _run(project: Path, diff_text: str, override=None, *extra_args):
    env = dict(os.environ)
    env.pop("ADR_KIT_OVERRIDE", None)
    if override is not None:
        env["ADR_KIT_OVERRIDE"] = override
    result = subprocess.run(
        [
            sys.executable, str(ADR_JUDGE),
            "--diff", "-",
            "--adr-dir", str(project / "docs" / "adr"),
            "--repo-root", str(project),
            "--json",
            *extra_args,
        ],
        input=diff_text, capture_output=True, text=True, encoding="utf-8",
        env=env,
    )
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    return result.returncode, payload, result.stderr


def test_override_downgrades_only_named_adr(tmp_path):
    """ADR-001 override leaves the ADR-002 FAIL blocking."""
    proj = _make_project(tmp_path)
    code, out, err = _run(proj, DIFF_BOTH, "ADR-001: incident 42 hotfix")
    assert code == 1, "ADR-002 violation must still block"
    by_adr = {}
    for f in out["findings"]:
        by_adr.setdefault(f["adr"], []).append(f)
    assert all(f["severity"] == "advisory" for f in by_adr["ADR-001"])
    assert all(f.get("overridden") is True for f in by_adr["ADR-001"])
    assert all(f["severity"] == "violation" for f in by_adr["ADR-002"])
    assert "OVERRIDE ACTIVE" in err


def test_override_unblocks_when_only_named_adr_fails(tmp_path):
    proj = _make_project(tmp_path)
    code, out, err = _run(proj, DIFF_FOO_ONLY, "ADR-001: incident 42 hotfix")
    assert code == 0
    assert out["summary"]["violations"] == 0
    assert "ADR-Override: ADR-001 incident 42 hotfix" in err


def test_empty_reason_refused(tmp_path):
    proj = _make_project(tmp_path)
    code, out, err = _run(proj, DIFF_FOO_ONLY, "ADR-001:")
    assert code == 1, "override without reason must not weaken the gate"
    assert "REFUSED" in err
    assert not (proj / "docs" / "adr" / OVERRIDE_LOG).exists()


def test_garbage_override_refused(tmp_path):
    proj = _make_project(tmp_path)
    code, out, err = _run(proj, DIFF_FOO_ONLY, "just let me commit")
    assert code == 1
    assert "REFUSED" in err
    assert not (proj / "docs" / "adr" / OVERRIDE_LOG).exists()


def test_jsonl_record_written_with_expected_fields(tmp_path):
    proj = _make_project(tmp_path)
    code, _out, _err = _run(proj, DIFF_FOO_ONLY, "ADR-001: incident 42 hotfix")
    assert code == 0
    log = proj / "docs" / "adr" / OVERRIDE_LOG
    assert log.exists()
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["adr"] == "ADR-001"
    assert rec["reason"] == "incident 42 hotfix"
    assert rec["overridden_findings"] >= 1
    assert rec["user"]  # git config or env fallback, never empty
    assert rec["timestamp"]
    # text=True pipes translate LF to os.linesep before the judge reads stdin,
    # so accept the hash of either newline flavour.
    candidates = {
        hashlib.sha256(DIFF_FOO_ONLY.encode("utf-8")).hexdigest(),
        hashlib.sha256(
            DIFF_FOO_ONLY.replace("\n", "\r\n").encode("utf-8")
        ).hexdigest(),
    }
    assert rec["staged_diff_sha256"] in candidates


def test_no_record_when_override_unused(tmp_path):
    """An override naming an ADR that did not fail writes no log entry."""
    proj = _make_project(tmp_path)
    clean = DIFF_FOO_ONLY.replace("Foo()", "Baz()")
    code, _out, _err = _run(proj, clean, "ADR-001: just in case")
    assert code == 0
    assert not (proj / "docs" / "adr" / OVERRIDE_LOG).exists()


def test_check_override_flag(tmp_path):
    proj = _make_project(tmp_path)
    code, _out, err = _run(proj, "", "ADR-001: valid reason", "--check-override")
    assert code == 0
    assert "override valid: ADR-001" in err
    code, _out, err = _run(proj, "", None, "--check-override")
    assert code == 2
    code, _out, err = _run(proj, "", "ADR-001:", "--check-override")
    assert code == 2


def test_audit_overrides_without_log(tmp_path):
    proj = _make_project(tmp_path)
    code, out, _err = _run(proj, "", None, "--audit-overrides")
    assert code == 0
    assert out["log_present"] is False
    assert out["entries"] == []
    assert out["summary"]["logged"] == 0


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
def test_audit_overrides_reconciles_trailers(tmp_path):
    """A logged override with a matching ADR-Override trailer is RECONCILED;
    one without stays UNMATCHED."""
    proj = _make_project(tmp_path)

    def git(*args):
        subprocess.run(
            ["git", "-C", str(proj), *args],
            check=True, capture_output=True, text=True,
        )

    git("init", "-q")
    git("config", "user.name", "Test User")
    git("config", "user.email", "test@example.com")
    git("config", "commit.gpgsign", "false")
    (proj / "file.txt").write_text("x\n", encoding="utf-8")
    git("add", "file.txt")
    git(
        "commit", "-q", "-m",
        "fix: hot patch\n\nADR-Override: ADR-001 incident 42 hotfix",
    )

    log = proj / "docs" / "adr" / OVERRIDE_LOG
    records = [
        {"timestamp": "2026-06-12T00:00:00+00:00", "adr": "ADR-001",
         "reason": "incident 42 hotfix", "user": "Test User",
         "staged_diff_sha256": "0" * 64, "overridden_findings": 1},
        {"timestamp": "2026-06-12T01:00:00+00:00", "adr": "ADR-002",
         "reason": "never trailered", "user": "Test User",
         "staged_diff_sha256": "1" * 64, "overridden_findings": 1},
    ]
    log.write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )

    code, out, _err = _run(proj, "", None, "--audit-overrides")
    assert code == 0
    by_adr = {e["adr"]: e for e in out["entries"]}
    assert by_adr["ADR-001"]["reconciled"] is True
    assert by_adr["ADR-001"]["trailer_commits"]
    assert by_adr["ADR-002"]["reconciled"] is False
    assert out["summary"] == {"logged": 2, "reconciled": 1, "unmatched": 1}
