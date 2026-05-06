"""End-to-end tests for bin/adr-judge.

Mirrors test_adr_lint.py — runs the CLI as a subprocess and asserts on the
JSON output and exit code.
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_JUDGE = REPO_ROOT / "bin" / "adr-judge"


def _make_project(tmp_path: Path, adrs: dict, files: dict) -> Path:
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    for name, body in adrs.items():
        (tmp_path / "docs" / "adr" / name).write_text(textwrap.dedent(body), encoding="utf-8")
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body), encoding="utf-8")
    return tmp_path


def _run(diff_text: str, project_root: Path):
    result = subprocess.run(
        [
            sys.executable, str(ADR_JUDGE),
            "--diff", "-",
            "--adr-dir", str(project_root / "docs" / "adr"),
            "--repo-root", str(project_root),
            "--json",
        ],
        input=diff_text, capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    return result.returncode, json.loads(result.stdout)


CANONICAL_ADR = """\
# ADR-001 No Foo

## Status

Accepted, 2026-04-25.

## Context

Foo fragments the heap.

## Decision

Don't use Foo.

## Alternatives Considered

- Use Foo: rejected.
- Use Bar: accepted.

## Consequences

**Positive:**
- No Foo.

**Negative:**
- Need Bar.

## Related Decisions

- None.

## References

- ./bench/results.txt

## Enforcement

```json
{
  "forbid_pattern": [
    {"pattern": "\\\\bFoo\\\\b", "path_glob": "src/**/*.py", "message": "No Foo."}
  ]
}
```
"""


SAMPLE_DIFF = """\
diff --git a/src/test.py b/src/test.py
--- a/src/test.py
+++ b/src/test.py
@@ -1 +1,2 @@
+def hello():
+    return Foo()
"""


def test_violation_detected(tmp_path):
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": CANONICAL_ADR}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 1
    assert out["summary"]["violations"] == 1
    f = out["findings"][0]
    assert f["adr"] == "ADR-001"
    assert f["rule"] == "forbid_pattern"
    assert f["path"] == "src/test.py"
    assert f["line"] == 2
    assert "Foo" in f["snippet"]


def test_no_enforcement_block_skipped(tmp_path):
    """ADR without an Enforcement section is silently skipped."""
    no_enforce = CANONICAL_ADR.split("## Enforcement")[0]
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": no_enforce}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 0
    assert out["summary"]["adrs_checked"] == 0
    assert out["findings"] == []


def test_proposed_status_skipped(tmp_path):
    """Only Accepted ADRs are enforced; Proposed are advisory in spirit."""
    proposed = CANONICAL_ADR.replace("Accepted, 2026-04-25.", "Proposed, 2026-04-25.")
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": proposed}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 0
    assert out["findings"] == []


def test_path_glob_filter(tmp_path):
    """Rule path_glob limits which diff files are checked."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": CANONICAL_ADR}, {})
    diff = SAMPLE_DIFF.replace("src/test.py", "tests/test_x.py")
    code, out = _run(diff, proj)
    assert code == 0
    assert out["findings"] == []


def test_llm_judge_only_is_advisory(tmp_path):
    """Free-form ADRs (llm_judge:true, no rules) emit advisory, not violation."""
    body = CANONICAL_ADR.split("## Enforcement")[0] + textwrap.dedent("""
        ## Enforcement

        ```json
        {"llm_judge": true}
        ```
    """)
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": body}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 0
    assert out["summary"]["advisories"] == 1
    assert out["findings"][0]["rule"] == "llm_judge"
    assert out["findings"][0]["severity"] == "advisory"


def test_malformed_enforcement_json_errors(tmp_path):
    """Bad JSON in Enforcement block → exit 2, clear error."""
    bad = CANONICAL_ADR.replace('"forbid_pattern"', "BROKEN_JSON")
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": bad}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 2


def test_clean_diff_passes(tmp_path):
    """Diff that doesn't match the forbid pattern returns 0."""
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": CANONICAL_ADR}, {})
    clean = SAMPLE_DIFF.replace("Foo()", "Bar()")
    code, out = _run(clean, proj)
    assert code == 0
    assert out["findings"] == []


def test_status_with_period_form(tmp_path):
    """Status body 'Accepted. Date: ...' is accepted just like 'Accepted, ...'."""
    period_form = CANONICAL_ADR.replace(
        "Accepted, 2026-04-25.", "Accepted. Date: 2026-04-25."
    )
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": period_form}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 1, "Period-form status should still register as Accepted and enforce rules"
    assert out["summary"]["violations"] == 1


def test_superseded_status_skipped(tmp_path):
    """Superseded ADRs don't enforce — same as Proposed/Deprecated."""
    superseded = CANONICAL_ADR.replace(
        "Accepted, 2026-04-25.", "Superseded by ADR-099, 2026-05-01."
    )
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": superseded}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 0
    assert out["findings"] == []


def test_bold_inline_status_recognised(tmp_path):
    """Legacy `**Status:** Accepted` (bold-inline) ADRs are seen as Accepted by the judge.

    adr-lint still flags these on Completeness (correct — they lack a `## Status`
    heading). The judge only needs the value to decide whether to enforce.
    Added in v0.12.1 to unblock projects mid-migration: diff-vs-Enforcement
    coverage works without first running /adr-kit:migrate.
    """
    bold_inline = textwrap.dedent("""\
        # ADR-001: No Foo

        **Status:** Accepted
        **Date:** 2024-01-01

        ## Context

        Foo fragments the heap.

        ## Decision

        Don't use Foo.

        ## Enforcement

        ```json
        {
          "forbid_pattern": [
            {"pattern": "\\\\bFoo\\\\b", "path_glob": "src/**/*.py", "message": "No Foo."}
          ]
        }
        ```
    """)
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": bold_inline}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 1, "Bold-inline Accepted ADR should still enforce its Enforcement rules"
    assert out["summary"]["violations"] == 1


def test_bold_inline_proposed_does_not_enforce(tmp_path):
    """Bold-inline Proposed status is also recognised — but Proposed never enforces."""
    bold_inline_proposed = textwrap.dedent("""\
        # ADR-001: No Foo

        **Status:** Proposed
        **Date:** 2024-01-01

        ## Decision

        Don't use Foo.

        ## Enforcement

        ```json
        {"forbid_pattern": [{"pattern": "\\\\bFoo\\\\b"}]}
        ```
    """)
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": bold_inline_proposed}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 0
    assert out["findings"] == []


def test_bold_inline_fully_bracketed(tmp_path):
    """`**Status: Accepted**` (everything bold) is also recognised."""
    body = textwrap.dedent("""\
        # ADR-001: No Foo

        **Status: Accepted**

        ## Decision

        Don't use Foo.

        ## Enforcement

        ```json
        {"forbid_pattern": [{"pattern": "\\\\bFoo\\\\b"}]}
        ```
    """)
    proj = _make_project(tmp_path, {"ADR-001-no-foo.md": body}, {})
    code, out = _run(SAMPLE_DIFF, proj)
    assert code == 1
    assert out["summary"]["violations"] == 1
