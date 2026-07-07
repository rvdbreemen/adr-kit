"""Tests for canonical frontmatter migration and schema-gate reuse."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
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

