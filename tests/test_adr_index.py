"""Tests for bin/adr-index: compact ADR index for context injection (ADR-004).

Design invariants under test:
  - one row per ADR, sorted by ADR number
  - status / scope / one-line decision extracted from the pinned canonical fields
  - Phase 0 no-drift lock: adr-index's status and enforcement-glob readers agree
    byte-for-byte with bin/adr-watch's (which mirror bin/adr-judge)
  - empty / absent adr-dir yields an index with no rows, exit 0
  - --format json is machine-readable
  - output carries no timestamp (reproducible, CI-diffable)
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "bin" / "adr-index"
WATCH = REPO_ROOT / "bin" / "adr-watch"


def _load(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_index = _load("adr_index", INDEX)
_watch = _load("adr_watch", WATCH)


def _run(args, cwd):
    result = subprocess.run(
        [sys.executable, str(INDEX)] + args,
        capture_output=True, text=True, encoding="utf-8", cwd=str(cwd),
    )
    return result.returncode, result.stdout, result.stderr


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


def _make(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-002-cache.md").write_text(ADR_PROPOSED, encoding="utf-8")
    (adr_dir / "ADR-001-repo.md").write_text(ADR_GLOB, encoding="utf-8")
    (adr_dir / "ADR-010-gov.md").write_text(ADR_MANUAL, encoding="utf-8")
    return adr_dir


class TestRows:

    def test_one_row_per_adr_sorted(self, tmp_path):
        adr_dir = _make(tmp_path)
        rows = _index.load_index(adr_dir)
        assert [r["adr_id"] for r in rows] == ["ADR-001", "ADR-002", "ADR-010"]

    def test_status_and_scope_and_decision(self, tmp_path):
        adr_dir = _make(tmp_path)
        rows = {r["adr_id"]: r for r in _index.load_index(adr_dir)}
        assert rows["ADR-001"]["status"] == "Accepted"
        assert rows["ADR-001"]["scope"] == ["src/**/*.py"]
        assert rows["ADR-001"]["decision"].startswith("All database access")
        assert rows["ADR-002"]["status"] == "Proposed"
        assert rows["ADR-010"]["scope"] == []  # manual-review block, no globs

    def test_markdown_table_and_json(self, tmp_path):
        adr_dir = _make(tmp_path)
        rc, out, _ = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert rc == 0
        assert "| ADR | Status | Scope | Decision |" in out
        assert "`src/**/*.py`" in out
        rc, jout, _ = _run(["--adr-dir", str(adr_dir), "--format", "json"], cwd=tmp_path)
        assert rc == 0
        data = json.loads(jout)
        assert {d["adr_id"] for d in data} == {"ADR-001", "ADR-002", "ADR-010"}

    def test_no_timestamp_in_output(self, tmp_path):
        adr_dir = _make(tmp_path)
        rc, out1, _ = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        rc, out2, _ = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert out1 == out2  # reproducible: nothing date/time-dependent


class TestSelfGuard:

    def test_empty_dir_no_rows_exit_zero(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        rc, out, _ = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert rc == 0
        assert "# ADR Index" in out
        assert "_(none)_" in out


class TestNoDriftWithWatch:
    """Phase 0: the index readers must agree with adr-watch's readers."""

    SAMPLES = [ADR_GLOB, ADR_PROPOSED, ADR_MANUAL]

    def test_status_reader_matches_watch(self):
        for text in self.SAMPLES:
            assert _index.adr_status(text) == _watch._adr_status(text)

    def test_enforcement_glob_reader_matches_watch(self):
        for text in self.SAMPLES:
            assert _index.enforcement_globs(text) == list(
                dict.fromkeys(_watch._parse_enforcement_globs(text)))
