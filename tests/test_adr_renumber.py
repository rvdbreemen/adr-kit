"""End-to-end tests for bin/adr-renumber, plus the duplicate-number lint
regression test for the post-merge collision scenario.

Each test runs the CLI as a subprocess and asserts on output, exit code, and
file system effects. This verifies the public interface, not internal helpers.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_RENUMBER = REPO_ROOT / "bin" / "adr-renumber"
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"


def run_renumber(*args):
    result = subprocess.run(
        [sys.executable, str(ADR_RENUMBER), *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


def run_lint_json(*args):
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, json.loads(result.stdout)


def adr(num, title_slug, heading_title, body=""):
    """Return (filename, content) for a minimal ADR fixture."""
    name = f"ADR-{num:03d}-{title_slug}.md"
    content = (
        f"# ADR-{num:03d} {heading_title}\n\n"
        f"## Status\n\nAccepted, 2026-06-01.\n\n"
        f"## Context\n\nFixture.\n\n"
        f"## Decision\n\nFixture decision.\n\n"
        f"## Alternatives Considered\n\n- Do nothing: rejected.\n"
        f"- Another way: rejected.\n\n"
        f"## Consequences\n\nNone, 0 impact.\n\n"
        f"## Related Decisions\n\n- None.\n\n"
        f"## References\n\n- None.\n"
        f"{body}"
    )
    return name, content


def write_set(tmp_path):
    """Build an ADR set exercising every cross-reference kind.

    ADR-043 is the one to renumber. ADR-007 references it from Related
    Decisions, a Superseded-by status string, a Status History mention, and
    a plain reference. ADR-430 exists to prove word-boundary safety, and
    ADR-008 contains an ADR-0430 token that must never be touched.
    """
    d = tmp_path / "adr"
    d.mkdir()
    name43, content43 = adr(43, "use-sqlite", "Use SQLite")
    (d / name43).write_text(content43, encoding="utf-8")

    name7 = "ADR-007-storage-layer.md"
    content7 = (
        "# ADR-007 Storage Layer\n\n"
        "## Status\n\nSuperseded by ADR-043, 2026-06-02.\n"
        "Amended by ADR-043 earlier that week.\n\n"
        "status_history:\n"
        "  - date: 2026-06-02\n"
        "    status: Superseded\n"
        "    changed_by: robert\n"
        "    reason: replaced by ADR-043\n"
        "    changed_via: manual\n\n"
        "## Context\n\nSee ADR-043 for the follow-up.\n\n"
        "## Decision\n\nFixture decision.\n\n"
        "## Alternatives Considered\n\n- Do nothing: rejected.\n\n"
        "## Consequences\n\nNone.\n\n"
        "## Related Decisions\n\n- ADR-043: supersedes this decision.\n\n"
        "## References\n\n- None.\n"
    )
    (d / name7).write_text(content7, encoding="utf-8")

    name430, content430 = adr(430, "big-number", "Big Number")
    (d / name430).write_text(content430, encoding="utf-8")

    name8 = "ADR-008-boundary.md"
    content8 = (
        "# ADR-008 Boundary\n\n"
        "## Status\n\nAccepted, 2026-06-01.\n\n"
        "## Context\n\nMentions ADR-0430 which must never be rewritten.\n\n"
        "## Decision\n\nFixture.\n\n"
        "## Alternatives Considered\n\n- None: rejected.\n\n"
        "## Consequences\n\nNone.\n\n"
        "## Related Decisions\n\n- ADR-430: the real big one.\n\n"
        "## References\n\n- None.\n"
    )
    (d / name8).write_text(content8, encoding="utf-8")
    return d


def test_dry_run_plan_is_complete_and_changes_nothing(tmp_path):
    d = write_set(tmp_path)
    before = {p.name: p.read_text(encoding="utf-8") for p in d.glob("*.md")}

    code, out, err = run_renumber("ADR-043", "--to", "ADR-051", "--adr-dir", str(d))
    assert code == 0, err
    assert "Plan: renumber ADR-043 -> ADR-051" in out
    assert "ADR-043-use-sqlite.md" in out and "ADR-051-use-sqlite.md" in out
    # Heading rewrite of the source file, with file:line.
    assert "ADR-043-use-sqlite.md:1" in out
    assert "# ADR-051 Use SQLite" in out
    # Every cross-reference kind in ADR-007 appears with file:line.
    plan_lines = [ln for ln in out.splitlines() if "ADR-007-storage-layer.md:" in ln]
    referenced = "\n".join(plan_lines)
    assert "Superseded by ADR-043" in referenced
    assert "Amended by ADR-043" in referenced
    assert "replaced by ADR-043" in referenced  # Status History mention
    assert "See ADR-043" in referenced  # plain reference
    assert "ADR-043: supersedes this decision" in referenced  # Related Decisions
    assert "Dry run: no changes made" in out

    after = {p.name: p.read_text(encoding="utf-8") for p in d.glob("*.md")}
    assert before == after


def test_apply_renames_file_heading_and_cross_refs(tmp_path):
    d = write_set(tmp_path)
    code, out, err = run_renumber(
        "ADR-043", "--to", "ADR-051", "--adr-dir", str(d), "--apply"
    )
    assert code == 0, err
    assert not (d / "ADR-043-use-sqlite.md").exists()
    new_file = d / "ADR-051-use-sqlite.md"
    assert new_file.exists()
    assert new_file.read_text(encoding="utf-8").startswith("# ADR-051 Use SQLite")

    sibling = (d / "ADR-007-storage-layer.md").read_text(encoding="utf-8")
    assert "ADR-043" not in sibling
    assert "Superseded by ADR-051" in sibling
    assert "Amended by ADR-051" in sibling
    assert "reason: replaced by ADR-051" in sibling
    assert "See ADR-051 for the follow-up" in sibling
    assert "- ADR-051: supersedes this decision" in sibling


def test_word_boundary_safety(tmp_path):
    d = write_set(tmp_path)
    code, out, err = run_renumber(
        "ADR-043", "--to", "ADR-051", "--adr-dir", str(d), "--apply"
    )
    assert code == 0, err
    # ADR-0430 token and ADR-430 file are untouched.
    boundary = (d / "ADR-008-boundary.md").read_text(encoding="utf-8")
    assert "ADR-0430" in boundary
    assert "- ADR-430: the real big one." in boundary
    assert (d / "ADR-430-big-number.md").exists()
    big = (d / "ADR-430-big-number.md").read_text(encoding="utf-8")
    assert big.startswith("# ADR-430 Big Number")


def test_target_taken_refused_exit_2(tmp_path):
    d = write_set(tmp_path)
    code, out, err = run_renumber(
        "ADR-043", "--to", "ADR-007", "--adr-dir", str(d), "--apply"
    )
    assert code == 2
    assert "already taken" in err
    assert "ADR-007-storage-layer.md" in err
    # Nothing changed.
    assert (d / "ADR-043-use-sqlite.md").exists()


def test_missing_source_refused_exit_2(tmp_path):
    d = write_set(tmp_path)
    code, out, err = run_renumber("ADR-099", "--adr-dir", str(d))
    assert code == 2
    assert "no ADR with number 099" in err


def test_default_target_is_next_free_number(tmp_path):
    d = write_set(tmp_path)
    # Highest in use is 430, so the default target is ADR-431.
    code, out, err = run_renumber("ADR-043", "--adr-dir", str(d))
    assert code == 0, err
    assert "Plan: renumber ADR-043 -> ADR-431" in out


def test_ambiguous_duplicate_source_requires_file_path(tmp_path):
    d = write_set(tmp_path)
    name, content = adr(43, "use-postgres", "Use Postgres")
    (d / name).write_text(content, encoding="utf-8")

    code, out, err = run_renumber("ADR-043", "--to", "ADR-051", "--adr-dir", str(d))
    assert code == 2
    assert "ambiguous" in err

    # Passing the file path resolves the ambiguity.
    code, out, err = run_renumber(
        str(d / "ADR-043-use-postgres.md"), "--to", "ADR-051",
        "--adr-dir", str(d), "--apply",
    )
    assert code == 0, err
    assert (d / "ADR-051-use-postgres.md").exists()
    assert (d / "ADR-043-use-sqlite.md").exists()


def test_lint_fails_on_duplicate_numbers_post_merge(tmp_path):
    """Regression: two ADRs with the same number and different titles, the
    post-merge collision scenario. The consistency gate must FAIL, name both
    files, and point at bin/adr-renumber."""
    d = tmp_path / "adr"
    d.mkdir()
    for slug, title in (("use-sqlite", "Use SQLite"), ("use-postgres", "Use Postgres")):
        name, content = adr(43, slug, title)
        (d / name).write_text(content, encoding="utf-8")

    code, out = run_lint_json(str(d))
    assert code == 1
    assert out["summary"]["fail"] == 2
    for f in out["files"]:
        dup = [
            fnd for fnd in f["findings"]
            if fnd["gate"] == "consistency" and "duplicate ADR-043" in fnd["summary"]
        ]
        assert dup, f"no duplicate finding for {f['file']}"
        assert dup[0]["level"] == "FAIL"
        assert "ADR-043-use-sqlite.md" in dup[0]["summary"]
        assert "ADR-043-use-postgres.md" in dup[0]["summary"]
        assert "adr-renumber" in dup[0]["summary"]


def test_lint_duplicate_fail_survives_strict_from(tmp_path):
    """Consistency is always_strict by default even when strict_from would
    make other gates advisory for old ADRs."""
    d = tmp_path / "adr"
    d.mkdir()
    for slug, title in (("one", "One"), ("two", "Two")):
        name, content = adr(43, slug, title)
        (d / name).write_text(content, encoding="utf-8")

    code, out = run_lint_json(str(d), "--strict-from", "ADR-100")
    assert code == 1
    assert out["summary"]["fail"] == 2
