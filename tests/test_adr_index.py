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
_judge = _load("adr_judge_for_index_test", REPO_ROOT / "bin" / "adr-judge")
_lint = _load("adr_lint_for_index_test", REPO_ROOT / "bin" / "adr-lint")
_retire = _load("adr_retire_for_index_test", REPO_ROOT / "bin" / "adr-retire")
_catalog = _load("adr_catalog_for_index_test", REPO_ROOT / "bin" / "adr_catalog.py")


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
{"forbid_pattern": [{"pattern": "legacy_api", "path_glob": "src/**/*.py"}]}
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
        assert all({"title", "format", "path"} <= set(row) for row in data)

    def test_graph_output_contains_versioned_nodes_and_edges(self, tmp_path):
        adr_dir = _make_context_set(tmp_path)
        related = adr_dir / "ADR-002-cache.md"
        related.write_text(
            related.read_text(encoding="utf-8")
            + "\n## Related Decisions\n\n- ADR-001\n- ADR-999\n",
            encoding="utf-8",
        )

        result = _run(
            ["--adr-dir", str(adr_dir), "--format", "graph"],
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        graph = json.loads(result.stdout)
        assert graph["schema_version"] == 2
        assert graph["$schema"] == "../../schemas/adr-index.schema.json"
        assert [node["id"] for node in graph["adrs"]] == [
            "ADR-001",
            "ADR-002",
            "ADR-010",
        ]
        node = graph["adrs"][0]
        assert node["scope"]["path_globs"] == ["src/**/*.py"]
        assert node["decision_summary"].startswith("All database access")
        assert node["topics"] == []
        assert node["aliases"] == []
        assert node["components"] == []
        assert node["symbols"] == []
        assert node["context_scope"] == "selective"
        assert node["decision_contract"] == {
            "must": [],
            "must_not": [],
            "exceptions": [],
            "verification": [],
        }
        assert set(node["metadata"]) == {
            "binding",
            "gate",
            "documents_shipped",
            "verified_in",
            "supersedes",
            "superseded_by",
        }
        edges = {
            (edge["source"], edge["target"]): edge
            for edge in graph["relationships"]
        }
        assert edges[("ADR-002", "ADR-001")]["resolved"] is True
        assert edges[("ADR-002", "ADR-999")]["resolved"] is False

    def test_no_timestamp_in_output(self, tmp_path):
        adr_dir = _make_context_set(tmp_path)
        first = _run(
            ["--adr-dir", str(adr_dir), "--format", "graph"],
            cwd=tmp_path,
        )
        second = _run(
            ["--adr-dir", str(adr_dir), "--format", "graph"],
            cwd=tmp_path,
        )
        assert first.stdout == second.stdout
        assert "generated_at" not in first.stdout

    def test_graph_projects_bounded_retrieval_metadata_and_contract(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        data = {
            "id": "ADR-001",
            "title": "Choose Indexed Retrieval",
            "status": "Accepted",
            "date": "2026-07-23",
            "binding": False,
            "gate": None,
            "documents_shipped": False,
            "verified_in": [],
            "supersedes": [],
            "superseded_by": None,
            "format": "madr",
            "topics": ["Selective context", "ADR retrieval"],
            "aliases": ["index first"],
            "components": ["adr-context"],
            "symbols": ["load_graph"],
            "context_scope": "global",
        }
        contract_items = "\n".join(
            f"* Verification item {index}" for index in range(25)
        )
        body = """\
# ADR-001 Choose Indexed Retrieval

## Status

Accepted, 2026-07-23.

## Decision Outcome

Use the generated graph for selective context.

## Decision Contract

### Must

* Query the generated graph
  without opening every Markdown ADR.

### Must Not

* Parse every source ADR.

### Exceptions

* Fall back visibly when the graph is unavailable.

### Verification

""" + contract_items
        path = adr_dir / "ADR-001-choose-indexed-retrieval.md"
        path.write_text(
            _schema.render_frontmatter(data) + body,
            encoding="utf-8",
        )

        result = _run(
            ["--adr-dir", str(adr_dir), "--format", "graph"],
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        node = json.loads(result.stdout)["adrs"][0]
        assert node["topics"] == ["ADR retrieval", "Selective context"]
        assert node["aliases"] == ["index first"]
        assert node["components"] == ["adr-context"]
        assert node["symbols"] == ["load_graph"]
        assert node["context_scope"] == "global"
        assert node["decision_contract"]["must"] == [
            "Query the generated graph without opening every Markdown ADR."
        ]
        assert node["decision_contract"]["must_not"] == [
            "Parse every source ADR."
        ]
        assert len(node["decision_contract"]["verification"]) == 20

    def test_malformed_optional_retrieval_metadata_is_rejected_by_schema_helper(self):
        data = {
            "id": "ADR-001",
            "title": "Invalid Retrieval Metadata",
            "status": "Proposed",
            "date": "2026-07-23",
            "binding": False,
            "gate": None,
            "documents_shipped": False,
            "verified_in": [],
            "supersedes": [],
            "superseded_by": None,
            "topics": "not-a-list",
            "aliases": ["duplicate", "DUPLICATE"],
            "context_scope": "sometimes",
        }

        issues = _schema.validate_frontmatter(data)

        assert any("topics must be a list" in issue for issue in issues)
        assert any("aliases entries must be unique" in issue for issue in issues)
        assert "context_scope must be one of: global, selective" in issues


class TestContextSelfGuard:

    def test_empty_dir_no_rows_exit_zero(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        result = _run(["--adr-dir", str(adr_dir)], cwd=tmp_path)
        assert result.returncode == 0
        assert "# ADR Index" in result.stdout
        assert "_(none)_" in result.stdout

    def test_malformed_frontmatter_falls_back_to_invariant_prose(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001-fallback.md").write_text(
            "---\n- invalid\n---\n" + ADR_GLOB,
            encoding="utf-8",
        )

        result = _run(
            ["--adr-dir", str(adr_dir), "--format", "graph"],
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        node = json.loads(result.stdout)["adrs"][0]
        assert node["id"] == "ADR-001"
        assert node["status"] == "Accepted"
        assert node["scope"]["path_globs"] == ["src/**/*.py"]


class TestNoDriftWithWatch:
    """Phase 0: the context index readers must agree with adr-watch."""

    SAMPLES = [ADR_GLOB, ADR_PROPOSED, ADR_MANUAL]

    def test_status_reader_matches_watch(self):
        # adr-index derives status from the authoritative load_adr_records path;
        # the lightweight regex reader now lives once in adr_catalog, and every
        # tool (including watch) delegates to it, so they cannot drift.
        for text in self.SAMPLES:
            assert _watch._adr_status(text) == _catalog.adr_status(text)

    def test_enforcement_glob_reader_matches_watch(self):
        for text in self.SAMPLES:
            assert _index.enforcement_globs(text) == list(
                dict.fromkeys(_watch._parse_enforcement_globs(text))
            )


class TestStatusReaderUnification:
    """All five status readers share one canonical extractor (adr_catalog).

    Follow-up to the forked-regex finding documented in PR #38: the two
    pre-canonical single-line 'Status: X' variants disagreed, so the same ADR
    could read as Accepted by one tool and Unknown by another. Every reader now
    delegates to adr_catalog.adr_status, so they can never diverge again.
    """

    # (input, expected status word or None). The first two are the exact forms
    # that used to split the tools: leading indent (old judge/lint/retire form
    # missed it) and a missing colon (old index/watch form missed it).
    CASES = [
        ("  Status: Accepted", "accepted"),
        ("Status Accepted", "accepted"),
        ("Status: Accepted", "accepted"),
        ("## Status\n\nProposed, 2026-01-01.\n", "proposed"),
        ("**Status:** Deprecated", "deprecated"),
        ("## Status History\n\n- date: 2026-01-01\n", None),
    ]

    # adr-index reads status through the authoritative load_adr_records path,
    # so it has no lightweight regex reader; the canonical adr_catalog reader is
    # the reference every other tool must match.
    READERS = (
        ("catalog", lambda t: _catalog.adr_status(t)),
        ("watch", lambda t: _watch._adr_status(t)),
        ("judge", lambda t: _judge.adr_status(t)),
        ("lint", lambda t: _lint._current_status(t)),
        ("retire", lambda t: _retire.extract_status(t)),
    )

    def test_all_tools_agree_on_status(self):
        for text, expected in self.CASES:
            values = {name: reader(text) for name, reader in self.READERS}
            normalized = {
                None if value is None else value.lower() for value in values.values()
            }
            assert len(normalized) == 1, (text, values)
            got = next(iter(normalized))
            assert got == expected, (text, values)


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
        assert (adr_dir / "ADR-INDEX.md").exists()
        graph = json.loads((adr_dir / "ADR-INDEX.json").read_text(encoding="utf-8"))
        assert graph["schema_version"] == 2
        assert len(graph["adrs"]) == 2

    def test_index_check_fails_when_readme_missing_or_stale(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        _write_adr(adr_dir, 1, "Local Recall")

        missing = _run(["--check", "--format", "json", str(adr_dir)], cwd=tmp_path)

        assert missing.returncode == 1
        payload = json.loads(missing.stdout)
        assert payload["summary"]["changed"] is True

    def test_index_check_detects_stale_json_graph(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        _write_adr(adr_dir, 1, "Local Recall")
        assert _run([str(adr_dir)], cwd=tmp_path).returncode == 0
        (adr_dir / "ADR-INDEX.json").write_text("{}\n", encoding="utf-8")

        stale = _run(
            ["--check", "--format", "json", str(adr_dir)],
            cwd=tmp_path,
        )

        assert stale.returncode == 1
        payload = json.loads(stale.stdout)
        assert payload["summary"]["context_json_changed"] is True
        assert payload["summary"]["readme_changed"] is False

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


def test_repository_graph_matches_versioned_schema_surface():
    schema = json.loads(
        (REPO_ROOT / "schemas" / "adr-index.schema.json").read_text(
            encoding="utf-8"
        )
    )
    graph = json.loads(
        (REPO_ROOT / "docs" / "adr" / "ADR-INDEX.json").read_text(
            encoding="utf-8"
        )
    )

    assert graph["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert set(graph) == {"$schema", "schema_version", "adrs", "relationships"}
    adr_required = set(schema["$defs"]["adr"]["required"])
    edge_required = set(schema["$defs"]["relationship"]["required"])
    assert all(set(node) == adr_required for node in graph["adrs"])
    assert all(set(edge) == edge_required for edge in graph["relationships"])
    assert all(len(node["decision_summary"]) <= 120 for node in graph["adrs"])
    # Normalised rather than `st_size`, because the budget is about how much
    # graph an agent has to carry, and a carriage return is not context. On a
    # Windows checkout `core.autocrlf` adds one byte per line -- 2661 of them
    # here -- which put the file 1958 bytes over a budget it clears by 703 on
    # the LF checkout CI uses. That is a platform artefact reported as a
    # governance failure, and the same shape as the drift false positive in
    # TASK-57.
    def _content_bytes(path):
        return len(path.read_bytes().replace(b"\r\n", b"\n"))

    graph_bytes = _content_bytes(REPO_ROOT / "docs" / "adr" / "ADR-INDEX.json")
    markdown_bytes = sum(
        _content_bytes(path)
        for path in (REPO_ROOT / "docs" / "adr").glob("ADR-*.md")
    )
    # Per-ADR allowance raised from 2 KB to 2.5 KB in 0.55.0. At 41 records the
    # old bound left 4 bytes of headroom (100348 of 100352), so it had stopped
    # measuring growth: it would fire on whichever ADR was edited next, whatever
    # the edit was. TASK-187 tripped it by adding three `verified_in` paths to
    # ADR-029, which is the record becoming more accurate rather than the graph
    # becoming fat. The ratio assertion below is the bound that actually limits
    # what an agent pays to carry the graph, and it still clears comfortably.
    assert graph_bytes <= 16 * 1024 + 5 * 512 * len(graph["adrs"])
    assert graph_bytes <= markdown_bytes * 0.25
    assert graph["adrs"] == sorted(
        graph["adrs"],
        key=lambda node: int(node["id"].split("-")[1]),
    )
    assert graph["relationships"] == sorted(
        graph["relationships"],
        key=lambda edge: (edge["source"], edge["target"], edge["type"]),
    )
