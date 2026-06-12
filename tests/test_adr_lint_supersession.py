"""Tests for concurrent-supersession detection in the consistency gate (task-10).

Two or more Accepted ADRs claiming to supersede the same target ADR is an
ambiguity that breaks the audit trail: the target's Status line can name at
most one successor. The consistency gate FAILs every claimant and names all
involved files. A single clean supersession passes.
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"


def _adr(num: int, slug_title: str, status_line: str, related: str = "- None.") -> str:
    title = slug_title.replace("-", " ").title()
    return textwrap.dedent(f"""\
        # ADR-{num:03d} {title}

        ## Status

        {status_line}

        ## Context

        Some context.

        ## Decision

        Some decision.

        ## Alternatives Considered

        - Do nothing: rejected.
        - This: accepted.

        ## Consequences

        **Positive:**
        - Some benefit.

        ## Related Decisions

        {related}

        ## References

        - None.
        """)


def _write(adr_dir: Path, num: int, slug: str, body: str) -> None:
    (adr_dir / f"ADR-{num:03d}-{slug}.md").write_text(body, encoding="utf-8")


def run_lint(target: Path):
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", str(target)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    return result.returncode, json.loads(result.stdout)


def test_double_supersession_fails_with_both_files_cited(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write(adr_dir, 1, "old-decision",
           _adr(1, "old-decision", "Superseded by ADR-002, 2026-05-01."))
    _write(adr_dir, 2, "new-decision",
           _adr(2, "new-decision", "Accepted, 2026-05-01.",
                related="- Supersedes ADR-001."))
    _write(adr_dir, 3, "rival-decision",
           _adr(3, "rival-decision", "Accepted, 2026-05-02.",
                related="- Supersedes ADR-001."))

    code, out = run_lint(adr_dir)
    assert code == 1
    by_num = {f["adr_num"]: f for f in out["files"]}
    for claimant in (2, 3):
        consistency = [
            fnd for fnd in by_num[claimant]["findings"]
            if fnd["gate"] == "consistency" and fnd["level"] == "FAIL"
        ]
        assert consistency, f"ADR-{claimant:03d} should FAIL consistency"
        summary = consistency[0]["summary"]
        assert "concurrent supersession of ADR-001" in summary
        assert "ADR-002-new-decision.md" in summary
        assert "ADR-003-rival-decision.md" in summary
    # The victim itself is not blamed for the claimants' conflict.
    assert not any(
        "concurrent supersession" in fnd.get("summary", "")
        for fnd in by_num[1]["findings"]
    )


def test_single_clean_supersession_passes(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write(adr_dir, 1, "old-decision",
           _adr(1, "old-decision", "Superseded by ADR-002, 2026-05-01."))
    _write(adr_dir, 2, "new-decision",
           _adr(2, "new-decision", "Accepted, 2026-05-01.",
                related="- Supersedes ADR-001."))

    code, out = run_lint(adr_dir)
    assert code == 0
    assert out["summary"]["fail"] == 0


def test_non_accepted_claimant_does_not_conflict(tmp_path):
    """A Proposed rival claim does not trigger the concurrent-supersession FAIL."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write(adr_dir, 1, "old-decision",
           _adr(1, "old-decision", "Superseded by ADR-002, 2026-05-01."))
    _write(adr_dir, 2, "new-decision",
           _adr(2, "new-decision", "Accepted, 2026-05-01.",
                related="- Supersedes ADR-001."))
    _write(adr_dir, 3, "rival-decision",
           _adr(3, "rival-decision", "Proposed, 2026-05-02.",
                related="- Supersedes ADR-001."))

    code, out = run_lint(adr_dir)
    assert code == 0
    assert out["summary"]["fail"] == 0


def test_double_supersession_message_names_target_successor(tmp_path):
    """The FAIL message reports what the target's Status actually says."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    # Target still Accepted: its status names NO successor at all.
    _write(adr_dir, 1, "old-decision",
           _adr(1, "old-decision", "Accepted, 2026-04-01."))
    _write(adr_dir, 2, "new-decision",
           _adr(2, "new-decision", "Accepted, 2026-05-01.",
                related="- Supersedes ADR-001."))
    _write(adr_dir, 3, "rival-decision",
           _adr(3, "rival-decision", "Accepted, 2026-05-02.",
                related="- Supersedes ADR-001."))

    code, out = run_lint(adr_dir)
    assert code == 1
    by_num = {f["adr_num"]: f for f in out["files"]}
    summary = next(
        fnd["summary"] for fnd in by_num[2]["findings"]
        if fnd["gate"] == "consistency"
    )
    assert "does not name a successor" in summary
