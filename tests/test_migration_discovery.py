"""Deterministic legacy-format discovery and migration notice contracts."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
MIGRATE = BIN / "adr-migrate"
LINT = BIN / "adr-lint"
INSTALLER_PATH = ROOT / "scripts" / "install-agent-envs.py"

sys.path.insert(0, str(BIN))
from adr_format import classify_format, detect_legacy_profile  # noqa: E402


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


Y_STATEMENT = """# Choose PostgreSQL

In the context of the order service, facing transactional consistency,
we decided for PostgreSQL and neglected MongoDB and SQLite, to achieve
atomic writes and familiar operations, accepting a larger runtime footprint.
"""

TYREE_AKERMAN = """# Select a persistence engine

## Issue

Which engine should store orders?

## Decision

Use PostgreSQL.

## Assumptions

The team operates PostgreSQL.

## Constraints

Writes must be transactional.

## Positions

PostgreSQL, MongoDB, and SQLite.

## Argument

PostgreSQL satisfies the constraints.

## Implications

The service needs schema migrations.
"""

ARC42 = """# System architecture

## 9. Architecture Decisions

### Persistence

Use PostgreSQL for transactional state.
"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (Y_STATEMENT, "y-statement"),
        (TYREE_AKERMAN, "tyree-akerman"),
        (ARC42, "arc42"),
    ],
)
def test_common_external_families_are_conservatively_detected(text, expected):
    assert detect_legacy_profile(text) == expected
    assert classify_format(text) == expected


def test_unrelated_markdown_is_not_a_legacy_format():
    text = "# Team notes\n\nWe discussed deployment and follow-up work.\n"
    assert detect_legacy_profile(text) is None
    assert classify_format(text) == "unknown"


def test_plan_detects_old_nygard_filename_and_never_writes(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    source = ROOT / "tests" / "fixtures" / "nygard" / (
        "0010-use-asynchronous-messaging.md"
    )
    target = adr_dir / source.name
    target.write_bytes(source.read_bytes())
    before = target.read_bytes()

    result = run(str(MIGRATE), "--plan", "--format", "json", str(adr_dir))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["read_only"] is True
    assert payload["summary"]["formats"] == {"nygard": 1}
    assert payload["summary"]["deterministic"] == 1
    notice = payload["files"][0]
    assert "adr-migrate" in notice["preview_command"]
    assert "--dry-run --to-profile nygard" in notice["preview_command"]
    assert notice["rename_to"].startswith("ADR-010-")
    assert notice["writes_automatically"] is False
    assert target.read_bytes() == before


def test_reported_nygard_path_becomes_strict_clean_after_approved_steps(
    tmp_path,
):
    source = ROOT / "tests" / "fixtures" / "nygard" / (
        "0010-use-asynchronous-messaging.md"
    )
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())
    plan = run(str(MIGRATE), "--plan", "--format", "json", str(target))
    notice = json.loads(plan.stdout)["files"][0]

    preview = run(
        str(MIGRATE),
        "--dry-run",
        "--to-profile",
        "nygard",
        str(target),
    )
    assert preview.returncode == 0
    assert target.read_bytes() == source.read_bytes()

    applied = run(
        str(MIGRATE),
        "--to-profile",
        "nygard",
        str(target),
    )
    assert applied.returncode == 0, applied.stdout + applied.stderr
    normalized = target.with_name(notice["rename_to"])
    target.rename(normalized)
    lint = run(str(LINT), "--strict", "--format", "json", str(normalized))

    assert lint.returncode == 0, lint.stdout + lint.stderr
    payload = json.loads(lint.stdout)

    # One advisory survives, and it is the honest one: a Nygard record imported
    # from another toolchain carries no topics, aliases or components, so an
    # agent's query will not surface it. Migration deliberately never invents
    # them. The finding is the migrating team's to-do list, not a defect in the
    # migration -- which is why it is ADVISORY and does not fail the run.
    findings = [f for entry in payload["files"] for f in entry["findings"]]
    assert [f.get("code") for f in findings] == ["SELECTIVE_CONTEXT_METADATA"], findings
    assert findings[0]["level"] == "ADVISORY"
    assert payload["summary"]["fail"] == 0


def test_plan_normalizes_common_madr_frontmatter_deterministically(tmp_path):
    source = ROOT / "tests" / "fixtures" / "madr" / (
        "0009-use-postgresql-for-persistence.md"
    )
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())

    result = run(str(MIGRATE), "--plan", "--format", "json", str(target))

    assert result.returncode == 0
    notice = json.loads(result.stdout)["files"][0]
    assert notice["detected_format"] == "madr"
    assert notice["deterministic"] is True
    assert notice["metadata_issues"] == []
    assert notice["rename_to"] == "ADR-009-use-postgresql-for-persistence.md"


def test_plan_routes_y_statement_to_guided_review(tmp_path):
    path = tmp_path / "0007-choose-postgresql.md"
    path.write_text(Y_STATEMENT, encoding="utf-8")

    result = run(str(MIGRATE), "--plan", "--format", "json", str(path))

    assert result.returncode == 0
    notice = json.loads(result.stdout)["files"][0]
    assert notice["detected_format"] == "y-statement"
    assert notice["deterministic"] is False
    assert notice["guided_command"].startswith("/adr-kit:migrate")
    assert "will not guess" in notice["message"]


def test_lint_reports_noncanonical_legacy_files_even_when_none_are_lintable(
    tmp_path,
):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    source = ROOT / "tests" / "fixtures" / "nygard" / (
        "0010-use-asynchronous-messaging.md"
    )
    (adr_dir / source.name).write_bytes(source.read_bytes())

    result = run(str(LINT), "--format", "json", str(adr_dir))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["total"] == 0
    assert len(payload["migration_notices"]) == 1
    assert payload["migration_notices"][0]["detected_format"] == "nygard"


def test_strict_lint_keeps_failure_and_adds_actionable_legacy_notice(tmp_path):
    path = tmp_path / "ADR-007-choose-postgresql.md"
    path.write_text(Y_STATEMENT, encoding="utf-8")

    result = run(str(LINT), "--strict", "--format", "json", str(path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["migration_notices"][0]["detected_format"] == "y-statement"
    summaries = [
        finding["summary"] for finding in payload["files"][0]["findings"]
    ]
    assert any("/adr-kit:migrate" in summary for summary in summaries)


def test_installer_format_scan_is_read_only_and_fail_open(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location(
        "migration_installer", INSTALLER_PATH
    )
    installer = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = installer
    spec.loader.exec_module(installer)

    source = tmp_path / "adr-kit"
    (source / "bin").mkdir(parents=True)
    (source / "bin" / "adr-migrate").touch()
    project = tmp_path / "project"
    (project / "docs" / "adr").mkdir(parents=True)
    calls = []

    def runner(command):
        calls.append(list(command))
        return subprocess.CompletedProcess(
            command,
            0,
            "No files changed. Migration is never automatic.\n",
            "",
        )

    installer.report_migration_plan(source, project, runner)
    assert "--plan" in calls[0]
    assert str(project / "docs" / "adr") in calls[0]
    assert "never automatic" in capsys.readouterr().out

    installer.report_migration_plan(
        source,
        project,
        lambda command: subprocess.CompletedProcess(command, 2, "", "bad"),
    )
    assert "installation remains valid" in capsys.readouterr().err
