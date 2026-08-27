"""Contracts for the shared schema-v2 index-first ADR query engine."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
CONTEXT = BIN / "adr-context"
INDEX = BIN / "adr-index"
sys.path.insert(0, str(BIN))

from adr_query import IndexQueryError, query_adr_context  # noqa: E402
from adr_schema import render_frontmatter  # noqa: E402


def _write_adr(
    adr_dir: Path,
    number: int,
    title: str,
    *,
    status: str = "Accepted",
    decision: str = "Use deterministic local retrieval.",
    topics: list[str] | None = None,
    aliases: list[str] | None = None,
    components: list[str] | None = None,
    symbols: list[str] | None = None,
    context_scope: str = "selective",
    path_glob: str | None = None,
    superseded_by: str | None = None,
    related: list[str] | None = None,
) -> Path:
    adr_dir.mkdir(parents=True, exist_ok=True)
    adr_id = f"ADR-{number:03d}"
    data = {
        "id": adr_id,
        "title": title,
        "status": status,
        "date": "2026-07-23",
        "binding": False,
        "gate": None,
        "documents_shipped": False,
        "verified_in": [],
        "supersedes": [],
        "superseded_by": superseded_by,
        "format": "madr",
        "topics": topics or [],
        "aliases": aliases or [],
        "components": components or [],
        "symbols": symbols or [],
        "context_scope": context_scope,
    }
    related_text = "\n".join(f"* {item}" for item in (related or [])) or "* None."
    rule = (
        {
            "forbid_pattern": [
                {
                    "pattern": "Forbidden",
                    "path_glob": path_glob,
                    "message": "Use Allowed.",
                }
            ],
            "forbid_import": [],
            "require_pattern": [],
            "llm_judge": False,
        }
        if path_glob
        else {
            "forbid_pattern": [],
            "forbid_import": [],
            "require_pattern": [],
            "llm_judge": False,
        }
    )
    body = f"""# {adr_id} {title}

## Status

{status}, 2026-07-23.

## Context and Problem Statement

The repository needs deterministic selective context.

## Decision Drivers

* Local retrieval.

## Considered Options

* Generated graph.
* Parse every Markdown ADR.

## Decision Outcome

{decision}

## Decision Contract

### Must

* Query the generated graph.

### Must Not

* Parse every source ADR on a healthy query.

### Exceptions

* Use a visible Markdown fallback.

### Verification

* Run the index-first-retrieval gate.

## Consequences

* Faster bounded retrieval.

## Related Decisions

{related_text}

## References

* tests/test_adr_query.py

## Enforcement

```json
{json.dumps(rule, indent=2)}
```
"""
    path = adr_dir / f"{adr_id}-{title.lower().replace(' ', '-')}.md"
    path.write_text(render_frontmatter(data) + body, encoding="utf-8")
    return path


def _build_index(adr_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INDEX), str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def _run_context(adr_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(CONTEXT),
            "--adr-dir",
            str(adr_dir),
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )


def test_healthy_index_query_opens_no_markdown_sources(tmp_path, monkeypatch):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(
        adr_dir,
        1,
        "Indexed Retrieval",
        topics=["selective context"],
    )
    _build_index(adr_dir)
    original = Path.read_text

    def guarded_read(path: Path, *args, **kwargs):
        if path.name.startswith("ADR-") and path.suffix == ".md":
            raise AssertionError(f"healthy query opened source ADR: {path}")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)
    outcome = query_adr_context("selective context", adr_dir)

    assert outcome["source"] == "index-v2"
    assert outcome["warnings"] == []
    assert outcome["results"][0]["adr_id"] == "ADR-001"


def test_schema_v1_index_reader_preserves_legacy_result_fields(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    graph = {
        "$schema": "../../schemas/adr-index.schema.json",
        "schema_version": 1,
        "adrs": [
            {
                "id": "ADR-001",
                "title": "Legacy Index",
                "path": "ADR-001-legacy-index.md",
                "format": "canonical",
                "status": "Accepted",
                "date": "2026-07-23",
                "decision_summary": "Use a legacy generated index.",
                "scope": {"path_globs": []},
                "metadata": {
                    "binding": False,
                    "gate": None,
                    "documents_shipped": False,
                    "verified_in": [],
                    "supersedes": [],
                    "superseded_by": None,
                },
            }
        ],
        "relationships": [],
    }
    (adr_dir / "ADR-INDEX.json").write_text(
        json.dumps(graph),
        encoding="utf-8",
    )

    outcome = query_adr_context("legacy generated index", adr_dir)

    assert outcome["source"] == "index-v1"
    item = outcome["results"][0]
    assert item["adr_id"] == "ADR-001"
    assert item["topics"] == []
    assert item["context_scope"] == "selective"
    assert item["decision_contract"]["must"] == []


def test_missing_invalid_unsupported_and_stale_indexes_are_visible(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    path = _write_adr(adr_dir, 1, "Fallback Retrieval")

    missing = query_adr_context("fallback retrieval", adr_dir)
    assert missing["source"] == "markdown-fallback"
    assert "missing" in missing["warnings"][0]
    with pytest.raises(IndexQueryError, match="missing"):
        query_adr_context("fallback retrieval", adr_dir, strict_index=True)

    index_path = adr_dir / "ADR-INDEX.json"
    index_path.write_text("{", encoding="utf-8")
    invalid = query_adr_context("fallback retrieval", adr_dir)
    assert "invalid" in invalid["warnings"][0]

    index_path.write_text(
        json.dumps({"schema_version": 99, "adrs": [], "relationships": []}),
        encoding="utf-8",
    )
    unsupported = query_adr_context("fallback retrieval", adr_dir)
    assert "unsupported" in unsupported["warnings"][0]

    malformed_v2 = _performance_graph(1)
    malformed_v2["adrs"][0].pop("topics")
    index_path.write_text(json.dumps(malformed_v2), encoding="utf-8")
    malformed = query_adr_context("fallback retrieval", adr_dir)
    assert "schema-v2 retrieval field" in malformed["warnings"][0]

    _build_index(adr_dir)
    time.sleep(0.01)
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    stale = query_adr_context("fallback retrieval", adr_dir)
    assert "stale" in stale["warnings"][0]
    with pytest.raises(IndexQueryError, match="stale"):
        query_adr_context("fallback retrieval", adr_dir, strict_index=True)


def test_cli_strict_index_fails_without_silent_fallback(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(adr_dir, 1, "Strict Retrieval")

    normal = _run_context(adr_dir, "--format", "json", "strict retrieval")
    strict = _run_context(
        adr_dir,
        "--strict-index",
        "--format",
        "json",
        "strict retrieval",
    )

    assert normal.returncode == 0
    assert "Markdown compatibility fallback" in normal.stderr
    assert strict.returncode == 2
    assert "ERROR" in strict.stderr
    assert strict.stdout == ""


def test_field_priority_is_explainable_and_has_no_authority_or_age_signal(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(
        adr_dir,
        1,
        "Query Architecture",
        topics=["selective context"],
        aliases=["index first"],
        components=["adr-context"],
        symbols=["query_adr_context"],
        path_glob="src/query/**/*.py",
    )
    _build_index(adr_dir)

    outcome = query_adr_context(
        "index first selective context",
        adr_dir,
        paths=("src/query/core/engine.py",),
        symbols=("query_adr_context",),
        components=("adr-context",),
        topics=("selective context",),
    )

    item = outcome["results"][0]
    assert item["score"] == 1.0
    assert {"path", "symbols", "components", "topics", "aliases"} <= set(
        item["signals"]
    )
    assert {"recency", "acceptance_status", "related_decisions"}.isdisjoint(
        item["signals"]
    )
    assert {match["field"] for match in item["matches"]} >= {
        "path",
        "symbols",
        "components",
        "topics",
        "aliases",
    }


def test_authority_history_and_successor_redirection(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(
        adr_dir,
        1,
        "Legacy Cache",
        status="Superseded",
        decision="Use the legacy cache protocol.",
        superseded_by="ADR-002",
    )
    _write_adr(
        adr_dir,
        2,
        "Current Storage",
        status="Accepted",
        decision="Use the current storage protocol.",
    )
    _write_adr(
        adr_dir,
        3,
        "Rejected Cache",
        status="Rejected",
        decision="Use the rejected cache protocol.",
    )
    _write_adr(
        adr_dir,
        4,
        "Candidate Cache",
        status="Proposed",
        decision="Use the candidate cache protocol.",
    )
    _build_index(adr_dir)

    redirected = query_adr_context("legacy cache protocol", adr_dir)
    assert redirected["results"][0]["adr_id"] == "ADR-002"
    assert redirected["results"][0]["redirected_from"] == "ADR-001"
    assert redirected["results"][0]["authority"] == "governing"

    default = query_adr_context("rejected candidate", adr_dir)
    assert {item["adr_id"] for item in default["results"]} == {"ADR-004"}
    assert default["results"][0]["authority"] == "advisory"

    historical = query_adr_context(
        "rejected candidate",
        adr_dir,
        include_history=True,
    )
    by_id = {item["adr_id"]: item for item in historical["results"]}
    assert by_id["ADR-003"]["authority"] == "historical"
    assert by_id["ADR-004"]["authority"] == "advisory"


def test_status_authority_filters_and_windows_paths_are_deterministic(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(
        adr_dir,
        1,
        "Windows Scoped Governing Decision",
        status="Accepted",
        path_glob="src/query/**/*.py",
    )
    _write_adr(
        adr_dir,
        2,
        "Windows Scoped Advisory Decision",
        status="Proposed",
        path_glob="src/query/**/*.py",
    )
    _build_index(adr_dir)

    governing = query_adr_context(
        "scoped decision",
        adr_dir,
        paths=(r"src\query\core\engine.py",),
        statuses=("Accepted",),
        authorities=("governing",),
    )
    advisory = query_adr_context(
        "scoped decision",
        adr_dir,
        paths=(r"src\query\core\engine.py",),
        authorities=("advisory",),
    )

    assert [item["adr_id"] for item in governing["results"]] == ["ADR-001"]
    assert governing["results"][0]["engine"] == "index-first"
    assert governing["results"][0]["matches"][0]["field"] == "path"
    assert [item["adr_id"] for item in advisory["results"]] == ["ADR-002"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"limit": 0}, "limit"),
        ({"min_score": 2}, "min_score"),
        ({"statuses": ("Imaginary",)}, "status"),
        ({"authorities": ("binding",)}, "authority"),
        ({"paths": ("x" * 241,)}, "paths"),
    ],
)
def test_query_input_contract_is_bounded(tmp_path, kwargs, message):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(adr_dir, 1, "Bounded Query")
    _build_index(adr_dir)

    with pytest.raises(ValueError, match=message):
        query_adr_context("bounded query", adr_dir, **kwargs)


def test_relationship_expansion_is_one_hop_and_capped_at_two(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(
        adr_dir,
        1,
        "Unique Orchestrator",
        decision="Use the quasar orchestrator.",
        related=["ADR-002", "ADR-003", "ADR-004"],
    )
    for number in (2, 3, 4):
        _write_adr(
            adr_dir,
            number,
            f"Supporting Decision {number}",
            decision=f"Supporting detail {number}.",
        )
    _build_index(adr_dir)

    outcome = query_adr_context("quasar orchestrator", adr_dir, limit=5)

    assert outcome["results"][0]["adr_id"] == "ADR-001"
    supporting = [
        item for item in outcome["results"] if item["role"] == "supporting"
    ]
    assert [item["adr_id"] for item in supporting] == ["ADR-002", "ADR-003"]
    assert all(item["score"] == 0.0 for item in supporting)


def test_explicit_no_match_returns_no_governing_result(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_adr(adr_dir, 1, "Local Queue", decision="Use an in-memory queue.")
    _build_index(adr_dir)

    outcome = query_adr_context("quantum satellite telemetry", adr_dir)

    assert outcome["results"] == []


def test_representative_otgw_probes_meet_top_k_quality_gate(tmp_path):
    graph_path = tmp_path / "ADR-INDEX.json"
    corpus = ROOT / "tests" / "testsets" / "otgw-firmware" / "adrs"
    generated = subprocess.run(
        [
            sys.executable,
            str(INDEX),
            "--adr-dir",
            str(corpus),
            "--format",
            "graph",
            "--output",
            str(graph_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert generated.returncode == 0, generated.stderr
    probes = {
        "mqtt source specific topics": "ADR-040",
        "wifi reconnect timeout tuning": "ADR-075",
        "retained discovery verification": "ADR-062",
        "heap tier machine contract": "ADR-089",
        # ADR-046, not ADR-045. ADR-045 reads `**Status:** Superseded by
        # ADR-046`, and until issue #118 the frontmatter inference could not
        # read that shape and labelled it Proposed, so a superseded decision
        # was ranked as the governing answer. This probe was passing because
        # of that bug. Retrieval now returns its successor, which is what a
        # reader asking about PS=1 summary parsing should be given.
        "ps1 print summary parsing": "ADR-046",
    }
    top1 = 0
    top3 = 0
    for query, required in probes.items():
        outcome = query_adr_context(
            query,
            tmp_path,
            limit=3,
            strict_index=True,
        )
        ids = [item["adr_id"] for item in outcome["results"]]
        top1 += bool(ids and ids[0] == required)
        top3 += required in ids
        assert all(item["authority"] != "historical" for item in outcome["results"])

    assert top1 / len(probes) >= 0.90
    assert top3 == len(probes)


def _performance_graph(count: int) -> dict:
    nodes = []
    for number in range(1, count + 1):
        nodes.append(
            {
                "id": f"ADR-{number:04d}" if number >= 1000 else f"ADR-{number:03d}",
                "title": f"Selective Retrieval Decision {number}",
                "path": f"ADR-{number:04d}-decision.md",
                "format": "madr",
                "status": "Accepted",
                "date": "2026-07-23",
                "decision_summary": "Use deterministic graph retrieval.",
                "topics": ["selective retrieval"],
                "aliases": [],
                "components": ["adr-context"],
                "symbols": [],
                "context_scope": "selective",
                "decision_contract": {
                    "must": ["Query the generated graph."],
                    "must_not": [],
                    "exceptions": [],
                    "verification": [],
                },
                "scope": {"path_globs": []},
                "metadata": {
                    "binding": False,
                    "gate": None,
                    "documents_shipped": False,
                    "verified_in": [],
                    "supersedes": [],
                    "superseded_by": None,
                },
            }
        )
    return {
        "$schema": "../../schemas/adr-index.schema.json",
        "schema_version": 2,
        "adrs": nodes,
        "relationships": [],
    }


@pytest.mark.skipif(
    os.environ.get("ADR_KIT_RUN_PERF") != "1",
    reason="absolute cold-process gate runs during explicit release certification",
)
@pytest.mark.parametrize(("count", "budget_ms"), [(200, 250.0), (1000, 500.0)])
def test_30_sample_cold_process_query_p95_budget(tmp_path, count, budget_ms):
    adr_dir = tmp_path / f"adrs-{count}"
    adr_dir.mkdir()
    (adr_dir / "ADR-INDEX.json").write_text(
        json.dumps(_performance_graph(count)),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        str(CONTEXT),
        "--adr-dir",
        str(adr_dir),
        "--strict-index",
        "--format",
        "json",
        "selective retrieval",
    ]
    subprocess.run(command, check=True, capture_output=True, cwd=ROOT)
    samples = []
    for _ in range(30):
        start = time.perf_counter()
        result = subprocess.run(command, capture_output=True, cwd=ROOT)
        samples.append((time.perf_counter() - start) * 1000)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
    p95 = sorted(samples)[27]
    print(
        f"index-first-retrieval count={count} samples=30 "
        f"p95_ms={p95:.1f} budget_ms={budget_ms:.1f}"
    )
    assert p95 <= budget_ms, (
        f"{count}-ADR cold-process/warm-filesystem p95 {p95:.1f}ms "
        f"exceeds {budget_ms:.1f}ms"
    )
