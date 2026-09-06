from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "bin"
READINESS_CLI = BIN_DIR / "adr-readiness"

sys.path.insert(0, str(BIN_DIR))
from adr_readiness import (  # noqa: E402
    FINDING_CODES,
    READINESS_CLASSES,
    architecture_advisories,
    build_readiness_report,
    implementation_evidence,
    readiness_for_record,
)
from adr_schema import render_frontmatter  # noqa: E402


def _write_adr(
    adr_dir: Path,
    num: int,
    *,
    status: str = "Proposed",
    open_questions: str = "None.",
    verified_in: list[str] | None = None,
    references: str = "* tests/test_adr_readiness.py:1",
) -> Path:
    title = f"Decision {num}"
    metadata = {
        "id": f"ADR-{num:03d}",
        "title": title,
        "status": status,
        "date": "2026-07-20",
        "binding": False,
        "gate": None,
        "documents_shipped": False,
        "verified_in": verified_in or [],
        "supersedes": [],
        "superseded_by": None,
        "format": "madr",
    }
    body = textwrap.dedent(
        f"""\
        # ADR-{num:03d} {title}

        ## Status

        {status}, 2026-07-20.

        ## Context and Problem Statement

        A deterministic choice is required.

        ## Decision Drivers

        * Stable local behavior.

        ## Considered Options

        * Local implementation.
        * Hosted implementation.

        ## Decision Outcome

        Chosen option: **local implementation**, because it is deterministic.

        ## Consequences

        Local code must be maintained.

        ## Open Questions

        {open_questions}

        ## Related Decisions

        * None.

        ## References

        {references}
        """
    )
    path = adr_dir / f"ADR-{num:03d}-decision-{num}.md"
    path.write_text(render_frontmatter(metadata) + body, encoding="utf-8")
    return path


def test_report_is_stable_and_open_questions_require_human_input(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 2, open_questions="- [ ] Which owner accepts the risk?")
    _write_adr(adr_dir, 1)

    first = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
    )
    second = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert [item["adr_id"] for item in first["adrs"]] == ["ADR-001", "ADR-002"]
    assert first["adrs"][0]["classification"] == "ready-for-confirmation"
    assert first["adrs"][1]["classification"] == "needs-human-input"
    assert first["adrs"][1]["open_questions"] == [
        "Which owner accepts the risk?"
    ]


def test_explicit_id_plus_verified_path_links_proposed_implementation(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 7, verified_in=["src/service.py"])

    report = build_readiness_report(
        adr_dir,
        evaluated_on=date(2026, 7, 20),
        adr_id="ADR-007",
        changed_paths=["src\\service.py"],
        source_text="Implements ADR-007",
    )
    link = report["adrs"][0]["implementation_link"]

    assert link["linked"] is True
    assert link["blocking_proposed"] is True
    assert link["changed_paths"] == ["src/service.py"]
    assert [item["code"] for item in link["evidence"]] == [
        "ADR_ID_EXPLICIT",
        "VERIFIED_IN_CHANGED",
    ]


def test_architecture_sensitive_path_without_explicit_surface_is_not_linked(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 7)

    report = build_readiness_report(
        adr_dir,
        evaluated_on=date(2026, 7, 20),
        adr_id="7",
        changed_paths=["src/database.py"],
        source_text="large architecture refactor",
    )

    assert report["adrs"][0]["implementation_link"]["linked"] is False
    assert report["summary"]["blocking_count"] == 0


def test_cli_json_uses_injected_date_and_is_read_only(tmp_path):
    root = tmp_path / "repo"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1)
    before = path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "ADR-001",
            "--repo-root",
            str(root),
            "--today",
            "2026-07-20",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["evaluated_on"] == "2026-07-20"
    assert payload["adrs"][0]["classification"] == "ready-for-confirmation"
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("status", "decision", "questions", "superseded_by", "expected"),
    [
        ("Unknown", "", [], None, "needs-mechanical-fix"),
        ("Proposed", "Choose local.", ["Who owns it?"], None, "needs-human-input"),
        ("Proposed", "Choose local.", [], None, "ready-for-confirmation"),
        ("Accepted", "Choose local.", [], None, "accepted"),
        ("Rejected", "Choose local.", [], None, "rejected"),
        ("Superseded", "Choose local.", [], "ADR-002", "supersession-required"),
    ],
)
def test_public_classifications_are_stable(
    status, decision, questions, superseded_by, expected
):
    record = {
        "adr_id": "ADR-001",
        "title": "Choice",
        "path": "ADR-001-choice.md",
        "status": status,
        "format": "madr",
        "decision_text": decision,
        "open_questions": questions,
        "documents_shipped": False,
        "verified_in": [],
        "scope": [],
        "superseded_by": superseded_by,
        "metadata_findings": (
            [{"code": "STATUS_UNKNOWN", "message": "unknown"}]
            if status == "Unknown"
            else []
        ),
    }

    report = readiness_for_record(record, evaluated_on=date(2026, 7, 20))

    assert report["classification"] == expected
    assert expected in READINESS_CLASSES


def test_not_an_adr_classification_remains_public_for_non_record_input():
    record = {
        "adr_id": "ADR-001",
        "title": "Empty",
        "path": "ADR-001-empty.md",
        "status": "Draft",
        "format": "madr",
        "decision_text": "Not applicable",
        "open_questions": [],
        "documents_shipped": False,
        "verified_in": [],
        "scope": [],
        "superseded_by": None,
        "metadata_findings": [],
    }
    assert (
        readiness_for_record(record, evaluated_on=date(2026, 7, 20))[
            "classification"
        ]
        == "not-an-adr"
    )


def test_malformed_metadata_becomes_a_controlled_finding(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-broken.md").write_text(
        "---\nverified_in:\n  invalid\n---\n"
        "# ADR-001 Broken\n\n## Status\n\nProposed\n\n"
        "## Decision\n\nUse local state.\n",
        encoding="utf-8",
    )

    report = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), adr_id="ADR-001"
    )

    codes = {
        item["code"] for item in report["adrs"][0]["mechanical_findings"]
    }
    assert "FRONTMATTER_MALFORMED" in codes
    assert codes.issubset(set(FINDING_CODES))


def test_permuted_paths_and_annotation_text_are_non_blocking_and_stable(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, verified_in=["src/service.py"])
    paths = ["infra/main.tf", "src\\service.py", "api/schema.json"]

    first = build_readiness_report(
        adr_dir,
        evaluated_on=date(2026, 7, 20),
        changed_paths=paths,
        source_text="title only ::warning:: ADR-001",
    )
    second = build_readiness_report(
        adr_dir,
        evaluated_on=date(2026, 7, 20),
        changed_paths=list(reversed(paths)),
        source_text="title only ::warning:: ADR-001",
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["summary"]["blocking_count"] == 1
    assert [item["path"] for item in first["advisories"]] == [
        "api/schema.json",
        "infra/main.tf",
    ]


def test_explicit_id_without_implementation_surface_never_blocks(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, verified_in=["src/service.py"])
    record = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20)
    )["adrs"][0]
    raw_record = {
        "adr_id": record["adr_id"],
        "path": record["path"],
        "verified_in": ["src/service.py"],
        "scope": [],
        "status": "Proposed",
    }

    link = implementation_evidence(
        raw_record, ["docs/readme.md"], "mentions ADR-001 accidentally"
    )

    assert link["linked"] is False
    assert link["blocking_proposed"] is False


def test_architecture_path_advisories_never_claim_linkage():
    assert architecture_advisories(["infra/main.tf"]) == [
        {
            "code": "ARCHITECTURE_REVIEW_RECOMMENDED",
            "path": "infra/main.tf",
            "classification": "not-an-adr",
            "message": "Architecture-sensitive path changed; review whether a durable decision is present.",
            "next_command": '/adr-kit:grill --source "infra/main.tf"',
        }
    ]


def test_linkage_status_path_fuzz_and_changed_adr_surface_controls():
    base = {
        "adr_id": "ADR-007",
        "path": "ADR-007-storage.md",
        "verified_in": [],
        "scope": ["services/storage/**"],
        "status": "Proposed",
    }
    linked = implementation_evidence(
        base,
        ["docs/adr/ADR-007-storage.md", "services/storage/new.py"],
    )
    assert linked["linked"] is True
    assert linked["blocking_proposed"] is True
    assert [item["code"] for item in linked["evidence"]] == [
        "ADR_FILE_CHANGED",
        "ENFORCEMENT_SCOPE_CHANGED",
    ]

    accepted = implementation_evidence(
        {**base, "status": "Accepted"},
        ["services/storage/new.py"],
        "ADR-007",
    )
    assert accepted["linked"] is True
    assert accepted["blocking_proposed"] is False

    superseded = implementation_evidence(
        {**base, "status": "Superseded"},
        ["services/storage/new.py"],
        "ADR-007",
    )
    assert superseded["linked"] is True
    assert superseded["blocking_proposed"] is False

    fuzzy = implementation_evidence(
        base,
        ["services/storage-old/new.py", "monorepo/services/storage/new.py"],
        "ADR-007",
    )
    assert fuzzy["linked"] is False


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_cli_supports_staged_and_base_head_modes_with_all_renderers(tmp_path):
    root = tmp_path / "repo"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, verified_in=["src/service.py"])
    (root / "src").mkdir()
    service = root / "src" / "service.py"
    service.write_text("VALUE = 1\n", encoding="utf-8")
    assert _git(root, "init").returncode == 0
    assert _git(root, "config", "user.email", "tests@example.com").returncode == 0
    assert _git(root, "config", "user.name", "ADR Kit Tests").returncode == 0
    assert _git(root, "add", ".").returncode == 0
    assert _git(root, "commit", "-m", "initial").returncode == 0
    base = _git(root, "rev-parse", "HEAD").stdout.strip()
    service.write_text("VALUE = 2  # ADR-001\n", encoding="utf-8")
    assert _git(root, "add", "src/service.py").returncode == 0

    staged = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "--all-proposed",
            "--diff",
            "--repo-root",
            str(root),
            "--today",
            "2026-07-20",
            "--format",
            "human",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert staged.returncode == 0
    assert "LINKED_PROPOSED_IMPLEMENTATION" in staged.stdout

    assert _git(root, "commit", "-m", "implement ADR-001").returncode == 0
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    github = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "--all-proposed",
            "--base",
            base,
            "--head",
            head,
            "--repo-root",
            str(root),
            "--today",
            "2026-07-20",
            "--format",
            "github",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert github.returncode == 0
    assert "## ADR readiness" in github.stdout
    assert "**ADR-001**" in github.stdout

    assert _git(root, "checkout", "--detach", head).returncode == 0
    detached = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "--diff",
            "--repo-root",
            str(root),
            "--today",
            "2026-07-20",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert detached.returncode == 0
    assert json.loads(detached.stdout)["schema_version"] == 1


def test_cli_empty_unknown_and_invalid_ref_are_controlled(tmp_path):
    root = tmp_path / "repo"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    empty = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "--all-proposed",
            "--repo-root",
            str(root),
            "--today",
            "2026-07-20",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert empty.returncode == 0
    assert json.loads(empty.stdout)["summary"]["total"] == 0

    unknown = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "ADR-999",
            "--repo-root",
            str(root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert unknown.returncode == 2
    assert "ADR not found" in unknown.stderr

    _write_adr(adr_dir, 1)
    assert _git(root, "init").returncode == 0
    invalid = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "--base",
            "missing-base",
            "--head",
            "HEAD",
            "--repo-root",
            str(root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert invalid.returncode == 2
    assert "adr-readiness:" in invalid.stderr


def test_github_renderer_escapes_untrusted_title(tmp_path):
    root = tmp_path / "repo"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1)
    text = path.read_text(encoding="utf-8").replace(
        "Decision 1", "Bad <script> `title`"
    )
    path.write_text(text, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(READINESS_CLI),
            "ADR-001",
            "--repo-root",
            str(root),
            "--format",
            "github",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert "<script>" not in result.stdout
    assert "&lt;script&gt;" in result.stdout


# ---------------------------------------------------------------------------
# Migration placeholders (TASK-199)
# ---------------------------------------------------------------------------

PLACEHOLDER_LIST_ITEM = "- TODO: add verifiable references."
PLACEHOLDER_HTML_COMMENT = "<!-- TODO: add verifiable references. -->"


def _placeholder_codes(record: dict) -> list[str]:
    return [
        finding["code"]
        for finding in record["human_findings"]
        if finding["code"] == "SECTION_PLACEHOLDER_ONLY"
    ]


@pytest.mark.parametrize(
    "placeholder",
    [
        pytest.param(PLACEHOLDER_LIST_ITEM, id="cli-list-item"),
        pytest.param(PLACEHOLDER_HTML_COMMENT, id="skill-html-comment"),
    ],
)
def test_a_placeholder_section_is_reported_and_needs_human_input(tmp_path, placeholder):
    """The record that reached acceptance unfinished (TASK-199).

    Measured before this signal existed: a Proposed record whose `## References`
    held only the line `bin/adr-migrate` writes classified
    `ready-for-confirmation` with `next_command: None` and no finding at all.
    That verdict was the defect. Both spellings are covered because
    `tests/test_adr_policy.py` pins them as equivalent, and only one of them
    used to be recognised.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, references=placeholder)

    report = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
    )
    record = report["adrs"][0]

    assert _placeholder_codes(record) == ["SECTION_PLACEHOLDER_ONLY"]
    # Naming the section is the whole point: "something is unfinished" sends the
    # reader back to diff the record against the template.
    assert any(
        "## References" in finding["message"]
        for finding in record["human_findings"]
    )
    assert record["classification"] == "needs-human-input"
    assert record["next_command"] == "/adr-kit:grill ADR-001"


def test_a_placeholder_does_not_block_the_gate_that_accept_runs(tmp_path):
    """Readiness reports; it must never become the refusal (TASK-198 policy).

    `tests/test_adr_policy.py` and `tests/test_migration_discovery.py` decided
    that an imported record must not fail a blocking gate on arrival. This
    asserts the same record from the other side, so the two halves cannot drift:
    readiness has something to say, and lint still has nothing.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, references=PLACEHOLDER_LIST_ITEM)

    report = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
    )
    assert _placeholder_codes(report["adrs"][0]) == ["SECTION_PLACEHOLDER_ONLY"]

    lint = subprocess.run(
        [
            sys.executable,
            str(BIN_DIR / "adr-lint"),
            "--gates",
            "completeness",
            "--context-dir",
            str(adr_dir),
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert lint.returncode == 0, lint.stdout


def test_an_empty_section_is_not_called_a_placeholder(tmp_path):
    """Two different holes, two different owners (TASK-199).

    An empty required heading already FAILs completeness, so acceptance refuses
    it without help here. Calling it a placeholder would be a false statement
    about a record that is already blocked, and would send the author looking
    for a TODO that is not there.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, references="")

    report = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
    )

    assert _placeholder_codes(report["adrs"][0]) == []


def test_placeholder_scan_stays_silent_when_the_file_cannot_be_read(tmp_path):
    """Records reach readiness with no file behind them, and that is normal.

    `readiness_for_record` is called with hand-built dicts carrying a bare
    filename that exists nowhere. A raise here would be invisible in production:
    `bin/adr-guardian` swallows every exception from the in-process refresh and
    returns 0, so the queue would silently go stale for 24 hours while looking
    healthy.
    """
    record = {
        "adr_id": "ADR-001",
        "path": "ADR-001-nowhere.md",
        "status": "Proposed",
        "title": "Nowhere",
        "format": "madr",
        "decision_text": "Chosen option: something.",
        "open_questions": [],
        "metadata_findings": [],
        "verified_in": [],
        "scope": [],
    }

    result = readiness_for_record(record, evaluated_on=date(2026, 7, 20))

    assert _placeholder_codes(result) == []
    assert result["classification"] == "ready-for-confirmation"


@pytest.mark.parametrize("fmt", ["hybrid", "unknown"])
def test_placeholder_scan_stays_silent_on_a_format_with_no_required_sections(
    tmp_path, fmt
):
    """`hybrid` and `unknown` are legal values of record["format"].

    They are what `detect_profile` returns for a record adr-kit cannot classify,
    and `normalize_profile` raises on both. Neither resolves to a required
    section list, so there is nothing to report -- and the raise must not
    escape, for the same reason as the unreadable-file case above.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, references=PLACEHOLDER_LIST_ITEM)
    record = {
        "adr_id": "ADR-001",
        "path": path.name,
        "status": "Proposed",
        "title": "Decision 1",
        "format": fmt,
        "decision_text": "Chosen option: something.",
        "open_questions": [],
        "metadata_findings": [],
        "verified_in": [],
        "scope": [],
    }

    result = readiness_for_record(
        record, evaluated_on=date(2026, 7, 20), adr_dir=adr_dir
    )

    assert _placeholder_codes(result) == []


def test_every_placeholder_section_is_reported_in_a_stable_order(tmp_path):
    """The report is asserted byte-stable across runs, so order is contract.

    `unfilled_required_sections` returns role-tuple order, not sorted order, so
    the emission sorts explicitly rather than inheriting whatever the profile
    table happens to list first.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, references=PLACEHOLDER_LIST_ITEM)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "* Local implementation.\n* Hosted implementation.",
        "- TODO: record the considered options.",
    )
    path.write_text(text, encoding="utf-8")

    report = build_readiness_report(
        adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
    )
    messages = [
        finding["message"]
        for finding in report["adrs"][0]["human_findings"]
        if finding["code"] == "SECTION_PLACEHOLDER_ONLY"
    ]

    assert messages == [
        "## Considered Options holds a migration placeholder, not an answer.",
        "## References holds a migration placeholder, not an answer.",
    ]
