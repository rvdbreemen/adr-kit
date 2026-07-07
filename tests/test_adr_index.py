"""Tests for bin/adr-index."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "bin" / "adr-index"
WATCH = REPO_ROOT / "bin" / "adr-watch"
SCHEMA_PATH = REPO_ROOT / "bin" / "adr_schema.py"


def _load(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_index = _load("adr_index", INDEX)
_watch = _load("adr_watch", WATCH)
_schema = _load("adr_schema_for_test", SCHEMA_PATH)


def _run(args, cwd):
    return subprocess.run(
        [sys.executable, str(INDEX), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
    )


ADR_GLOB = """# ADR-001 No direct database calls outside the repository layer

## Status

Accepted, 2026-01-15.

## Decision

All database access goes through the repository layer. It keeps handlers thin.

## Enforcement

```json
{"forbid_pattern": [{"pattern": "cursor", "path_glob": "src/**/*.py"}]}
```
"""

ADR_PROPOSED = """# ADR-002 Everything cached forever

## Status

Proposed, 2026-03-01.

## Decision

Cache the entire universe.
"""

ADR_MANUAL = """# ADR-010 Governance only

## Status

Accepted, 2026-04-01.

## Decision

Team reviews all releases on Fridays.

## Enforcement

```json
{"llm_judge": false}
```
"""


def _make_context_set(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-002-cache.md").write_text(ADR_PROPOSED, encoding="utf-8")
    (adr_dir / "ADR-001-repo.md").write_text(ADR_GLOB, encoding="utf-8")
    (adr_dir / "ADR-010-gov.md").write_text(ADR_MANUAL, encoding="utf-8")
    (adr_dir / "ADR-INDEX.md").write_text("generated artifact", encoding="utf-8")
    return adr_dir


class TestContextRows:

    def test_one_row_per_adr_sorted(self, tmp_path):
        adr_dir = _make_context_set(tmp_path)
        rows = _index.load_index(adr_dir)
        assert [r["adr_id"] for r in rows] == ["ADR-001", "ADR-002", "ADR-010"]

    def test_status_and_scope_and_decision(self, tmp_path):
        adr_dir = _make_context_set(tmp_path)
        rows = {r["adr_id"]: r for r in _index.load_index(adr_dir)}
        assert rows["ADR-001"]["status"] == "Accepted"
        assert rows["ADR-001"]["scope"] == ["src/**/*.py"]
        assert rows["ADR-001"]["decision"].startswith("All database access")
        assert rows["ADR-002"]["status"] == "Proposed"
        assert rows["ADR-010"]["scope"] == []

    def test_markdown_table_and_json(self, tmp_path):
        adr_dir = _make_context_set(tmp_path)
        result = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert result.returncode == 0
        assert "| ADR | Status | Scope | Decision |" in result.stdout
        assert "`src/**/*.py`" in result.stdout

        result = _run(["--adr-dir", str(adr_dir), "--format", "json"], cwd=tmp_path)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert {d["adr_id"] for d in data} == {"ADR-001", "ADR-002", "ADR-010"}

    def test_no_timestamp_in_output(self, tmp_path):
        adr_dir = _make_context_set(tmp_path)
        first = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        second = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert first.stdout == second.stdout


class TestContextSelfGuard:

    def test_empty_dir_no_rows_exit_zero(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        result = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert result.returncode == 0
        assert "# ADR Index" in result.stdout
        assert "_(none)_" in result.stdout


class TestNoDriftWithWatch:
    """Phase 0: the context index readers must agree with adr-watch."""

    SAMPLES = [ADR_GLOB, ADR_PROPOSED, ADR_MANUAL]

    def test_status_reader_matches_watch(self):
        for text in self.SAMPLES:
            assert _index.adr_status(text) == _watch._adr_status(text)

    def test_enforcement_glob_reader_matches_watch(self):
        for text in self.SAMPLES:
            assert _index.enforcement_globs(text) == list(
                dict.fromkeys(_watch._parse_enforcement_globs(text))
            )


def _body(num: int, title: str) -> str:
    return textwrap.dedent(
        f"""\
        # ADR-{num:03d} {title}

        ## Status

        Accepted, 2026-07-06.

        ## Context

        Indexes should be generated from local ADR files.

        ## Decision

        Generate the README index from canonical metadata.

        ## Alternatives Considered

        - Manual table: rejected because it drifts.
        - Hosted index: rejected because adr-kit must stay local.

        ## Consequences

        **Positive:**
        - The index is reproducible.

        **Negative:**
        - A generated block owns part of README.md.

        ## Related Decisions

        - None.

        ## References

        - tests/test_adr_index.py
        """
    )


def _write_adr(adr_dir: Path, num: int, title: str, **overrides) -> Path:
    data = {
        "id": f"ADR-{num:03d}",
        "title": title,
        "status": "Accepted",
        "date": "2026-07-06",
        "binding": False,
        "gate": None,
        "documents_shipped": False,
        "verified_in": [],
        "supersedes": [],
        "superseded_by": None,
    }
    data.update(overrides)
    path = adr_dir / f"ADR-{num:03d}-{title.lower().replace(' ', '-')}.md"
    path.write_text(_schema.render_frontmatter(data) + _body(num, title), encoding="utf-8")
    return path


class TestReadmeMode:

    def test_index_generates_readme_and_check_is_idempotent(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        _write_adr(adr_dir, 1, "Local Recall")
        _write_adr(adr_dir, 2, "Strict Governance")

        write = _run([str(adr_dir)], cwd=tmp_path)
        check = _run(["--check", str(adr_dir)], cwd=tmp_path)

        assert write.returncode == 0, write.stderr + write.stdout
        assert check.returncode == 0, check.stderr + check.stdout
        readme = (adr_dir / "README.md").read_text(encoding="utf-8")
        assert "<!-- adr-kit-index:begin -->" in readme
        assert "| Total ADRs | 2 |" in readme
        assert "ADR-001" in readme
        assert "ADR-002" in readme

    def test_index_check_fails_when_readme_missing_or_stale(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        _write_adr(adr_dir, 1, "Local Recall")

        missing = _run(["--check", "--format", "json", str(adr_dir)], cwd=tmp_path)

        assert missing.returncode == 1
        payload = json.loads(missing.stdout)
        assert payload["summary"]["changed"] is True

    def test_index_preserves_human_prose_outside_sentinels(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        _write_adr(adr_dir, 1, "Local Recall")
        (adr_dir / "README.md").write_text(
            "# Human Title\n\nKeep this intro.\n\n"
            "<!-- adr-kit-index:begin -->\nold\n<!-- adr-kit-index:end -->\n"
            "\nKeep this tail.\n",
            encoding="utf-8",
        )

        result = _run([str(adr_dir)], cwd=tmp_path)

        assert result.returncode == 0, result.stderr + result.stdout
        readme = (adr_dir / "README.md").read_text(encoding="utf-8")
        assert "# Human Title" in readme
        assert "Keep this intro." in readme
        assert "Keep this tail." in readme
        assert "old" not in readme
        assert "| Total ADRs | 1 |" in readme

    def test_index_reports_duplicate_adr_ids(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        _write_adr(adr_dir, 1, "First")
        duplicate = adr_dir / "ADR-001-second.md"
        duplicate.write_text(_body(1, "Second"), encoding="utf-8")

        result = _run(["--format", "json", str(adr_dir)], cwd=tmp_path)

        assert result.returncode == 1
        payload = json.loads(result.stdout)
        assert payload["summary"]["duplicates"] == 1
        assert "ADR-001 appears in multiple files" in payload["issues"][0]
