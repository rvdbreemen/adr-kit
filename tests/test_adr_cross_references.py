"""Reciprocal cross-references and their lint gate (TASK-83, spec R7).

Supersession has always been written on both sides in one transaction, so
neither ADR can carry half the link. A plain cross-reference had no writer at
all: an ADR could cite ADR-042 forever while ADR-042 never learned it was cited,
and nothing noticed when ADR-042 turned out not to exist.

Two mechanisms are asserted here, and one deliberate non-mechanism:

* `bin/adr relate` writes the `related` field on both ADRs at once, unwinds both
  the same way, and refuses the cases where writing would be a lie;
* `adr-lint` FAILs a dangling reference the author can still fix, and drops to
  ADVISORY once the citing record is Accepted, because ADR-009 forbids a gate
  that pressures an author into editing an immutable body;
* reciprocity is NOT demanded of prose citations. A decision log cites backwards
  by nature. Demanding a forward citation in every older ADR produced 57
  advisories on this repository's own healthy set, which is exactly the
  unactionable noise the gate exists to avoid.
"""

# Gate anchor for ADR-028: adr-reference-gate-scope-v1
# Verified here: the declared related link is gated; the prose one is left alone.
import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"
ADR = REPO_ROOT / "bin" / "adr"


def _adr(
    num: int,
    status_line: str = "Accepted, 2026-05-01.",
    related: str = "- None.",
    frontmatter_related: str = "",
) -> str:
    extra = f"related:\n{frontmatter_related}" if frontmatter_related else ""
    return textwrap.dedent(f"""\
        ---
        id: "ADR-{num:03d}"
        title: "Decision {num}"
        status: "{status_line.split(',')[0].split(' by ')[0].strip()}"
        date: "2026-05-01"
        binding: false
        gate: null
        documents_shipped: false
        verified_in: []
        supersedes: []
        superseded_by: null
        {extra}---

        # ADR-{num:03d} Decision {num}

        ## Status

        {status_line}

        ## Context

        Some context, with a concrete pointer to bin/adr-lint.

        ## Decision

        Do the thing.

        ## Alternatives Considered

        - Do nothing: rejected.
        - This: accepted.

        ## Consequences

        **Positive:**
        - Some benefit.

        **Negative:**
        - Some cost.

        ## Related Decisions

        {related}

        ## References

        - bin/adr-lint
        """)


def _seed(adr_dir: Path, num: int, **kwargs) -> Path:
    path = adr_dir / f"ADR-{num:03d}-decision-{num}.md"
    path.write_text(_adr(num, **kwargs), encoding="utf-8")
    return path


def _adr_dir(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Test Runner"}}), encoding="utf-8"
    )
    return adr_dir


def run_lint(target: Path):
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", str(target)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    return result.returncode, json.loads(result.stdout)


def run_relate(adr_dir: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(ADR), "relate", *args, "--adr-dir", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8",
    )


def _reference_findings(payload, adr_num: int):
    by_num = {f["adr_num"]: f for f in payload["files"]}
    return [
        finding
        for finding in by_num[adr_num]["findings"]
        if str(finding.get("code", "")).startswith("REFERENCE")
    ]


# ---------------------------------------------------------------------------
# bin/adr relate -- both sides, one transaction
# ---------------------------------------------------------------------------

def test_relate_writes_the_link_on_both_sides(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)
    _seed(adr_dir, 2)

    result = run_relate(adr_dir, "ADR-001", "--to", "ADR-002")

    assert result.returncode == 0, result.stderr
    assert 'related:\n  - "ADR-002"' in (adr_dir / "ADR-001-decision-1.md").read_text(encoding="utf-8")
    assert 'related:\n  - "ADR-001"' in (adr_dir / "ADR-002-decision-2.md").read_text(encoding="utf-8")


def test_relate_is_idempotent_and_reversible(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)
    _seed(adr_dir, 2)
    run_relate(adr_dir, "ADR-001", "--to", "ADR-002")

    again = run_relate(adr_dir, "ADR-002", "--to", "ADR-001")
    assert again.returncode == 0
    assert "already related" in again.stdout

    removed = run_relate(adr_dir, "ADR-001", "--to", "ADR-002", "--remove")
    assert removed.returncode == 0
    for num in (1, 2):
        text = (adr_dir / f"ADR-{num:03d}-decision-{num}.md").read_text(encoding="utf-8")
        # Absent, not empty: an empty list would claim the question was asked
        # and the answer was none. It was not; the link was removed.
        assert "related:" not in text


def test_relate_refuses_a_pair_that_is_already_a_supersession(tmp_path):
    """The stronger edge is already recorded on both sides; two would mislead."""
    adr_dir = _adr_dir(tmp_path)
    old = _seed(adr_dir, 1, status_line="Superseded by ADR-002, 2026-05-02.")
    old.write_text(
        old.read_text(encoding="utf-8").replace(
            "superseded_by: null", 'superseded_by: "ADR-002"'
        ),
        encoding="utf-8",
    )
    new = _seed(adr_dir, 2)
    new.write_text(
        new.read_text(encoding="utf-8").replace(
            "supersedes: []", 'supersedes:\n  - "ADR-001"'
        ),
        encoding="utf-8",
    )

    result = run_relate(adr_dir, "ADR-001", "--to", "ADR-002")

    assert result.returncode == 2
    assert "supersession is the stronger relationship" in result.stderr


def test_relate_refuses_self_and_unknown_targets(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)

    itself = run_relate(adr_dir, "ADR-001", "--to", "ADR-001")
    assert itself.returncode == 2
    assert "cannot be related to itself" in itself.stderr

    missing = run_relate(adr_dir, "ADR-001", "--to", "ADR-999")
    assert missing.returncode == 2


def test_relate_regenerates_the_indexes_in_the_same_transaction(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)
    _seed(adr_dir, 2)

    run_relate(adr_dir, "ADR-001", "--to", "ADR-002")

    for name in ("README.md", "ADR-INDEX.md", "ADR-INDEX.json"):
        assert (adr_dir / name).exists(), f"{name} was not regenerated"


def test_a_related_link_reaches_the_graph(tmp_path):
    """The point of writing it: the generated graph carries the edge."""
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)
    _seed(adr_dir, 2)
    run_relate(adr_dir, "ADR-001", "--to", "ADR-002")

    graph = json.loads((adr_dir / "ADR-INDEX.json").read_text(encoding="utf-8"))
    edges = {
        (edge["source"], edge["target"], edge["type"])
        for edge in graph.get("relationships", [])
    }
    assert ("ADR-001", "ADR-002", "related") in edges
    assert ("ADR-002", "ADR-001", "related") in edges


# ---------------------------------------------------------------------------
# adr-lint -- dangling and one-sided
# ---------------------------------------------------------------------------

def test_a_dangling_declared_link_fails(tmp_path):
    """`adr relate` resolves the target before writing, so this cannot happen by tool."""
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1, frontmatter_related='  - "ADR-042"\n')

    code, payload = run_lint(adr_dir)

    findings = _reference_findings(payload, 1)
    assert [f["level"] for f in findings] == ["FAIL"]
    assert findings[0]["code"] == "REFERENCE_DANGLING"
    assert "ADR-042" in findings[0]["summary"]
    assert code == 1


def test_a_dangling_prose_citation_is_never_flagged(tmp_path):
    """Prose is free-form, and adr-lint routinely runs on a fragment.

    `bin/adr accept` lints exactly one file, where every prose reference
    resolves to nothing. Flagging that would report a fact about the
    invocation, not about the code -- the unactionable finding ADR-009 forbids.
    Prose also legitimately names decisions from another repository and ADRs
    not written yet. `bin/adr-related` still lists them for a human who asks.
    """
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1, status_line="Proposed, 2026-05-01.",
          related="- **ADR-042 Never written:** cited on purpose.")

    code, payload = run_lint(adr_dir)

    assert not _reference_findings(payload, 1)
    assert code == 0


def test_linting_one_file_of_a_set_reports_no_reference_noise(tmp_path):
    """The regression that narrowed this gate: a fragment is not a defect."""
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1, related="- **ADR-002 Decision 2:** the reason this works.")
    _seed(adr_dir, 2)

    code, payload = run_lint(adr_dir / "ADR-001-decision-1.md")

    assert not _reference_findings(payload, 1)
    assert code == 0


def test_a_one_sided_declared_link_fails(tmp_path):
    """Only `adr relate` writes this field, and it writes both sides."""
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1, frontmatter_related='  - "ADR-002"\n')
    _seed(adr_dir, 2)

    code, payload = run_lint(adr_dir)

    findings = _reference_findings(payload, 1)
    assert [f["code"] for f in findings] == ["REFERENCE_ONE_SIDED"]
    assert findings[0]["level"] == "FAIL"
    assert "adr relate ADR-001 --to ADR-002" in findings[0]["summary"]
    assert code == 1
    # The ADR that was silently left out is not the one blamed for it.
    assert not _reference_findings(payload, 2)


def test_a_backwards_only_prose_citation_is_never_flagged(tmp_path):
    """The normal shape of a decision log, and the reason this gate is narrow."""
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)
    _seed(adr_dir, 2, related="- **ADR-001 Decision 1:** the reason this is possible.")

    code, payload = run_lint(adr_dir)

    assert not _reference_findings(payload, 1)
    assert not _reference_findings(payload, 2)
    assert code == 0


def test_relate_leaves_the_pair_clean_under_lint(tmp_path):
    """End to end: the command's output is what the gate wants to see."""
    adr_dir = _adr_dir(tmp_path)
    _seed(adr_dir, 1)
    _seed(adr_dir, 2)
    run_relate(adr_dir, "ADR-001", "--to", "ADR-002")

    code, payload = run_lint(adr_dir)

    assert not _reference_findings(payload, 1)
    assert not _reference_findings(payload, 2)
    assert code == 0


def test_this_repository_carries_no_reference_findings(tmp_path):
    """The gate has to be quiet on a healthy set, or nobody will read it."""
    _code, payload = run_lint(REPO_ROOT / "docs" / "adr")

    offenders = [
        (f["file"], finding["level"], finding["code"])
        for f in payload["files"]
        for finding in f["findings"]
        if str(finding.get("code", "")).startswith("REFERENCE")
    ]
    assert not offenders, offenders
