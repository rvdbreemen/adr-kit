"""Tests for canonical frontmatter migration and schema-gate reuse."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap

import pytest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_MIGRATE = REPO_ROOT / "bin" / "adr-migrate"
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"
ADR_SCHEMA = REPO_ROOT / "bin" / "adr_schema.py"


def _load_schema_module():
    spec = importlib.util.spec_from_file_location("adr_schema", ADR_SCHEMA)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCHEMA = _load_schema_module()


def _legacy_adr(num: int = 1) -> str:
    return textwrap.dedent(
        f"""\
        # ADR-{num:03d} Local Memory Recall

        ## Status

        Accepted, 2026-07-06.

        ## Context

        Agents need local recall that survives a new session.

        ## Decision

        Store structured ADR metadata locally, next to the prose.

        ## Alternatives Considered

        - Keep prose only: rejected because tools cannot reliably query it.
        - Use a hosted index: rejected because adr-kit must work locally.

        ## Consequences

        **Positive:**
        - Local recall improves.

        **Negative:**
        - ADR files gain a small metadata block.

        ## Related Decisions

        - None.

        ## References

        - tests/test_adr_migrate.py
        """
    )


def _run_migrate(*args: str):
    return subprocess.run(
        [sys.executable, str(ADR_MIGRATE), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _run_lint(*args: str):
    return subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_migrate_adds_frontmatter_and_preserves_body(tmp_path):
    original_body = _legacy_adr()
    adr = tmp_path / "ADR-001-local-memory-recall.md"
    adr.write_text(original_body, encoding="utf-8")

    result = _run_migrate(str(adr))

    assert result.returncode == 0, result.stderr + result.stdout
    raw_frontmatter, body = SCHEMA.split_frontmatter(adr.read_text(encoding="utf-8"))
    assert body == original_body
    data = SCHEMA.parse_frontmatter(raw_frontmatter)
    assert data["id"] == "ADR-001"
    assert data["title"] == "Local Memory Recall"
    assert data["status"] == "Accepted"
    assert data["date"] == "2026-07-06"
    assert data["binding"] is False
    assert data["documents_shipped"] is False
    assert data["verified_in"] == []


def test_migrate_is_idempotent_after_first_write(tmp_path):
    adr = tmp_path / "ADR-001-local-memory-recall.md"
    adr.write_text(_legacy_adr(), encoding="utf-8")
    first = _run_migrate(str(adr))
    assert first.returncode == 0, first.stderr + first.stdout
    after_first = adr.read_text(encoding="utf-8")

    second = _run_migrate(str(adr))

    assert second.returncode == 0, second.stderr + second.stdout
    assert adr.read_text(encoding="utf-8") == after_first


def test_check_mode_reports_needed_migration_without_writing(tmp_path):
    original_body = _legacy_adr()
    adr = tmp_path / "ADR-001-local-memory-recall.md"
    adr.write_text(original_body, encoding="utf-8")

    result = _run_migrate("--check", "--format", "json", str(adr))

    assert result.returncode == 1
    assert adr.read_text(encoding="utf-8") == original_body
    payload = json.loads(result.stdout)
    assert payload["summary"]["changed"] == 1
    assert payload["files"][0]["changed"] is True


def test_directory_migration_ignores_generated_adr_index(tmp_path):
    adr = tmp_path / "ADR-001-local-memory-recall.md"
    adr.write_text(_legacy_adr(), encoding="utf-8")
    generated = tmp_path / "ADR-INDEX.md"
    generated.write_text("# ADR Index\n\nGenerated artifact.\n", encoding="utf-8")

    result = _run_migrate("--check", "--format", "json", str(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["total"] == 1
    assert payload["files"][0]["file"].endswith("ADR-001-local-memory-recall.md")


def test_lint_schema_gate_fails_missing_frontmatter(tmp_path):
    adr = tmp_path / "ADR-001-local-memory-recall.md"
    adr.write_text(_legacy_adr(), encoding="utf-8")

    result = _run_lint("--gates", "schema", str(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    finding = payload["files"][0]["findings"][0]
    assert finding["gate"] == "schema"
    assert "missing canonical frontmatter" in finding["summary"]


def test_lint_schema_gate_passes_after_migration(tmp_path):
    adr = tmp_path / "ADR-001-local-memory-recall.md"
    adr.write_text(_legacy_adr(), encoding="utf-8")
    migrated = _run_migrate(str(adr))
    assert migrated.returncode == 0, migrated.stderr + migrated.stdout

    result = _run_lint("--gates", "schema", str(tmp_path))

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary"]["pass"] == 1
    assert payload["summary"]["fail"] == 0



# --- issue #118: the writer must not invent a status it could not read -------

_STATUS_SHAPES = [
    (
        "heading with a bare word",
        "# ADR-001 T\n\n## Status\n\nAccepted, 2026-01-01\n",
        "Accepted",
    ),
    (
        "bold inline **Status:** X",
        "# ADR-001 T\n\n**Status:** Accepted\n",
        "Accepted",
    ),
    (
        "heading-colon, unreadable",
        "# ADR-001 T\n\n## Status: Accepted\n",
        None,
    ),
    (
        "bold status word, unreadable",
        "# ADR-001 T\n\n## Status\n\n**Rejected, 2026-06-18.**\n",
        None,
    ),
    (
        "link-wrapped supersession, unreadable",
        "# ADR-001 T\n\n## Status\n\n**Superseded by [ADR-124](ADR-124-x.md)**\n",
        None,
    ),
]


@pytest.mark.parametrize("label,body,expected", _STATUS_SHAPES)
def test_inferred_status_is_read_or_left_undetermined_never_guessed(label, body, expected):
    """Issue #118: a shape it cannot read must not become `status: Proposed`.

    `status` decides whether a decision is binding and whether it is injected
    at all, so a guess is not a harmless default: it silently downgrades an
    Accepted record. Four of these five shapes used to come back `Proposed`,
    including one that recovered the date and not the status, producing a
    record that contradicted itself.
    """
    schema = _load_schema_module()
    inferred = schema.infer_frontmatter(body, Path("ADR-001-t.md"))
    assert inferred.get("status") == expected, label


@pytest.mark.parametrize("label,body,_expected", _STATUS_SHAPES)
def test_inferred_status_agrees_with_the_shared_reader(label, body, _expected):
    """The writer and the cross-tool reader must not disagree about a record.

    They are now the same function. Before, `infer_frontmatter` had a private
    matcher that recognised exactly one shape and guessed on the rest, while
    `adr_status` - whose docstring claims tools "can never disagree on an ADR's
    status" - was never consulted by the code that writes the field.
    """
    schema = _load_schema_module()
    inferred = schema.infer_frontmatter(body, Path("ADR-001-t.md"))
    reader = schema.adr_status(body)
    expected = reader.capitalize() if reader in schema.VALID_STATUSES else None
    assert inferred.get("status") == expected, label


def test_superseded_by_survives_a_link_wrapped_reference():
    """Real bodies write `Superseded by [ADR-124](...)`, not a bare ADR-124."""
    schema = _load_schema_module()
    body = "# ADR-001 T\n\n## Status\n\n**Superseded by [ADR-124](ADR-124-x.md)**\n"
    inferred = schema.infer_frontmatter(body, Path("ADR-001-t.md"))
    assert inferred.get("superseded_by") == "ADR-124"


def test_migrate_refuses_rather_than_writing_a_guessed_status(tmp_path):
    """The refusal is the point: adr-migrate used to exit 0 having guessed.

    `migrate_text` already had an issues channel; an undetermined status now
    reaches it instead of being papered over, so the file is left untouched
    and the caller is told which field could not be derived.
    """
    schema = _load_schema_module()
    body = "# ADR-001 T\n\n## Status: Accepted\n\n## Context\n\nx\n"
    path = tmp_path / "ADR-001-t.md"
    path.write_text(body, encoding="utf-8")

    new_text, changed, issues = schema.migrate_text(body, path)

    assert not changed, "a record whose status could not be read must not be rewritten"
    assert new_text == body
    assert any("status" in issue for issue in issues), issues
