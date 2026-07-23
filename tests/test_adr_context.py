"""Tests for bin/adr-context — semantic relevance ranking tool.

All subprocess calls use [sys.executable, SCRIPT] to work on Windows
(no shebang execution, no PATH tricks needed).

Performance test measures in-process via load_adr_context() to avoid
Python interpreter cold-start overhead (which can be 80-300ms on Windows).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# ---------------------------------------------------------------------------
# Script location
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).parent.parent / "bin" / "adr-context"


# ---------------------------------------------------------------------------
# Helper: import the module so we can call functions in-process
# ---------------------------------------------------------------------------

def _load_module():
    """Dynamically import bin/adr-context as a Python module.

    spec_from_file_location() returns None for files without a .py extension
    on some Python versions. We work around it by using a SourceFileLoader
    explicitly.
    """
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader("adr_context", str(SCRIPT))
    spec = importlib.util.spec_from_loader("adr_context", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adr_context"] = mod
    loader.exec_module(mod)
    return mod


_mod = _load_module()
extract_keywords = _mod.extract_keywords
infer_task_domain = _mod.infer_task_domain
extract_adr_metadata = _mod.extract_adr_metadata
score_adr = _mod.score_adr
load_adr_context = _mod.load_adr_context


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_adr(
    directory: Path,
    number: int,
    title: str,
    status: str = "Accepted",
    date_str: Optional[str] = None,
    decision: str = "",
    related: Optional[List[str]] = None,
) -> Path:
    """Write a minimal but parseable ADR file."""
    padded = f"{number:03d}"
    slug = title.lower().replace(" ", "-")
    filename = directory / f"ADR-{padded}-{slug}.md"
    date_line = f" Date: {date_str}." if date_str else ""
    related_section = ""
    if related:
        lines = "\n".join(f"- **{r}**: related." for r in related)
        related_section = f"\n\n## Related Decisions\n\n{lines}"
    content = f"""# ADR-{padded} {title}

## Status

{status}.{date_line}

## Context

Test fixture ADR for unit tests.

## Decision

{decision if decision else "This is the decision text."}

## Alternatives Considered

- Alternative A: rejected.
- Alternative B: rejected.

## Consequences

Positive outcome. Trade-off accepted.{related_section}

## References

- tests/test_adr_context.py
"""
    filename.write_text(content, encoding="utf-8")
    return filename


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run adr-context via subprocess and return the result."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 1. extract_keywords
# ---------------------------------------------------------------------------

def test_extract_keywords_filters_short_words():
    """Words shorter than 3 characters must be excluded."""
    keywords = extract_keywords("use an API to do it")
    assert "an" not in keywords
    assert "to" not in keywords
    assert "do" not in keywords
    assert "it" not in keywords
    assert "api" in keywords
    assert "use" in keywords


def test_extract_keywords_lowercase_and_sorted():
    keywords = extract_keywords("Cache INVALIDATION Strategy")
    assert keywords == sorted(kw.lower() for kw in keywords)
    assert "cache" in keywords
    assert "invalidation" in keywords
    assert "strategy" in keywords


# ---------------------------------------------------------------------------
# 2. infer_task_domain
# ---------------------------------------------------------------------------

def test_domain_backend_inferred():
    """'database query optimization' should map to data or backend but never frontend."""
    domain = infer_task_domain("database query optimization")
    # Both "data" and "backend" are valid; what matters is not frontend/infra/security
    assert domain in ("data", "backend")


def test_domain_frontend_inferred():
    domain = infer_task_domain("react component styling")
    assert domain == "frontend"


def test_domain_security_inferred():
    domain = infer_task_domain("jwt token validation")
    assert domain == "security"


def test_domain_infra_inferred():
    domain = infer_task_domain("docker deployment pipeline")
    assert domain == "infra"


def test_domain_data_inferred():
    domain = infer_task_domain("postgres index optimization")
    assert domain == "data"


# ---------------------------------------------------------------------------
# 3. Keyword scoring
# ---------------------------------------------------------------------------

def test_keyword_match_in_title(tmp_path):
    """Keywords present in the ADR title should produce a high score."""
    _write_adr(tmp_path, 1, "Redis Cache Invalidation Strategy",
               status="Accepted", date_str="2025-01-01",
               decision="We use Redis for caching with TTL-based invalidation.")
    results = load_adr_context("cache invalidation strategy", tmp_path, limit=5, min_score=0.0)
    assert results, "Expected at least one result"
    assert results[0]["score"] > 0.3, f"Score too low: {results[0]['score']}"


def test_keyword_no_match(tmp_path):
    """A query with no keyword overlap should produce a very low or zero score."""
    _write_adr(tmp_path, 1, "GraphQL Schema Design",
               status="Proposed",
               decision="We adopt GraphQL for the public API.")
    results = load_adr_context("kubernetes terraform deployment", tmp_path, limit=5, min_score=0.0)
    # Either no result, or score should be low
    if results:
        assert results[0]["score"] < 0.3, f"Score unexpectedly high: {results[0]['score']}"


# ---------------------------------------------------------------------------
# 4. Acceptance status ranking
# ---------------------------------------------------------------------------

def test_lifecycle_authority_does_not_change_relevance_score(tmp_path):
    """Accepted and Proposed authority is separate from relevance."""
    _write_adr(tmp_path, 1, "Database Connection Pooling",
               status="Accepted", date_str="2025-06-01",
               decision="We use a connection pool for database access.")
    _write_adr(tmp_path, 2, "Database Connection Pooling Alternative",
               status="Proposed", date_str="2025-06-01",
               decision="We use a connection pool for database access.")
    results = load_adr_context("database connection pool", tmp_path, limit=5, min_score=0.0)
    assert len(results) == 2
    accepted = next(r for r in results if "ADR-001" in r["adr_id"])
    proposed = next(r for r in results if "ADR-002" in r["adr_id"])
    assert accepted["score"] == proposed["score"]
    assert accepted["authority"] == "governing"
    assert proposed["authority"] == "advisory"
    assert [item["adr_id"] for item in results] == ["ADR-001", "ADR-002"]


# ---------------------------------------------------------------------------
# 5. CLI flags
# ---------------------------------------------------------------------------

def test_limit_flag_restricts_results(tmp_path):
    """--limit 2 should return at most 2 results."""
    for i in range(1, 6):
        _write_adr(tmp_path, i, f"Redis Cache Policy {i}",
                   status="Accepted", date_str="2025-01-01",
                   decision="Redis cache invalidation policy.")
    result = _run_cli("--format", "json", "--limit", "2",
                      "--adr-dir", str(tmp_path), "--min-score", "0.0",
                      "cache invalidation")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert len(data) <= 2


def test_default_limit_is_5(tmp_path):
    """Without --limit, result count must not exceed 5."""
    for i in range(1, 9):
        _write_adr(tmp_path, i, f"Cache Strategy {i}",
                   status="Accepted", date_str="2025-01-01",
                   decision="cache invalidation strategy.")
    result = _run_cli("--format", "json", "--min-score", "0.0",
                      "--adr-dir", str(tmp_path), "cache strategy")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert len(data) <= 5


def test_json_output_format(tmp_path):
    """--format json must produce valid JSON."""
    _write_adr(tmp_path, 1, "Authentication Strategy",
               status="Accepted", date_str="2025-03-01",
               decision="JWT tokens for authentication.")
    result = _run_cli("--format", "json", "--adr-dir", str(tmp_path), "authentication")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)  # raises if invalid JSON
    assert isinstance(data, list)


def test_json_has_positive_field_signals_only(tmp_path):
    """JSON signals must explain fields without lifecycle or age boosts."""
    _write_adr(tmp_path, 1, "JWT Authentication",
               status="Accepted", date_str="2025-03-01",
               decision="We use JWT tokens for authentication and authorization.")
    result = _run_cli("--format", "json", "--adr-dir", str(tmp_path),
                      "--min-score", "0.0", "jwt authentication")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data, "Expected at least one result"
    item = data[0]
    assert "signals" in item, "Missing 'signals' key in JSON output"
    signals = item["signals"]
    assert {"title", "decision_summary"} <= set(signals)
    assert {
        "exact_keyword",
        "domain_tag",
        "related_decisions",
        "acceptance_status",
        "recency",
    }.isdisjoint(signals)
    assert {match["field"] for match in item["matches"]} >= {
        "title",
        "decision_summary",
    }


def test_json_results_include_actionable_catalog_metadata(tmp_path):
    _write_adr(
        tmp_path,
        1,
        "JWT Authentication",
        status="Accepted",
        date_str="2025-03-01",
        decision="We use JWT tokens for authentication and authorization.",
        related=["ADR-002"],
    )
    _write_adr(
        tmp_path,
        2,
        "Token Rotation",
        status="Proposed",
        decision="Rotate authentication tokens every hour.",
    )

    result = _run_cli(
        "--format",
        "json",
        "--adr-dir",
        str(tmp_path),
        "--min-score",
        "0.0",
        "jwt authentication",
    )

    assert result.returncode == 0, result.stderr
    item = json.loads(result.stdout)[0]
    assert {
        "adr_id",
        "title",
        "path",
        "status",
        "is_accepted",
        "format",
        "decision_summary",
        "scope",
        "related_ids",
        "metadata",
        "score",
        "signals",
        "authority",
        "role",
        "matches",
        "source",
        "schema_version",
    } <= set(item)
    assert item["path"].endswith("ADR-001-jwt-authentication.md")
    assert item["status"] == "Accepted"
    assert item["is_accepted"] is True
    assert item["format"] in {"canonical", "nygard", "madr"}
    assert item["decision_summary"].startswith("We use JWT tokens")
    assert item["related_ids"] == ["ADR-002"]
    assert set(item["metadata"]) == {
        "binding",
        "gate",
        "documents_shipped",
        "verified_in",
        "supersedes",
        "superseded_by",
    }


def test_text_output_format(tmp_path):
    """--format text must produce human-readable lines."""
    _write_adr(tmp_path, 42, "Use Redis for Session Caching",
               status="Accepted", date_str="2025-06-01",
               decision="Redis is used for session caching.")
    result = _run_cli("--format", "text", "--adr-dir", str(tmp_path), "redis cache session")
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert lines, "Expected at least one output line"
    assert "ADR-042" in lines[0]
    assert "status: Accepted" in lines[0]
    assert "governing primary" in lines[0]
    assert "relevance:" in lines[0]


def test_proposed_result_is_explicitly_non_binding(tmp_path):
    _write_adr(
        tmp_path,
        43,
        "Candidate Session Cache",
        status="Proposed",
        decision="A candidate Redis session cache is under consideration.",
    )

    json_result = _run_cli(
        "--format",
        "json",
        "--adr-dir",
        str(tmp_path),
        "--min-score",
        "0.0",
        "candidate session cache",
    )
    item = json.loads(json_result.stdout)[0]
    assert item["status"] == "Proposed"
    assert item["is_accepted"] is False

    text_result = _run_cli(
        "--format",
        "text",
        "--adr-dir",
        str(tmp_path),
        "--min-score",
        "0.0",
        "candidate session cache",
    )
    assert "status: Proposed" in text_result.stdout
    assert "advisory primary" in text_result.stdout


def test_min_score_filter(tmp_path):
    """ADRs with score below --min-score threshold should be excluded."""
    # Write a very generic ADR unlikely to match "quantum computing blockchain"
    _write_adr(tmp_path, 1, "Code Style Guide",
               status="Proposed",
               decision="We use black for Python formatting.")
    result = _run_cli("--format", "json", "--adr-dir", str(tmp_path),
                      "--min-score", "0.9",
                      "quantum computing blockchain distributed ledger")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    # Should be empty: nothing scores 0.9 on an unrelated query
    assert data == [], f"Expected empty result, got: {data}"


def test_empty_adr_dir_returns_empty(tmp_path):
    """An empty ADR directory should return an empty list without error."""
    result = _run_cli("--format", "json", "--adr-dir", str(tmp_path), "authentication")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data == []


def test_missing_adr_dir_returns_empty():
    """A non-existent ADR directory should return empty without error."""
    result = _run_cli("--format", "json",
                      "--adr-dir", "/nonexistent/path/to/adr",
                      "authentication")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data == []


# ---------------------------------------------------------------------------
# 6. In-process signal correctness
# ---------------------------------------------------------------------------

def test_json_score_matches_signal_sum(tmp_path):
    """The 'score' field must equal the sum of all signal values (within tolerance)."""
    _write_adr(tmp_path, 1, "Redis Cache Invalidation",
               status="Accepted", date_str="2025-01-01",
               decision="We use Redis for cache invalidation with TTL strategy.")
    results = load_adr_context("cache invalidation redis", tmp_path,
                               limit=5, min_score=0.0)
    assert results
    r = results[0]
    signal_sum = round(sum(r["signals"].values()), 4)
    # They should match (both are clamped and rounded the same way)
    # Allow small floating-point tolerance
    assert abs(r["score"] - signal_sum) < 0.01, (
        f"score={r['score']} != signal_sum={signal_sum}"
    )


# ---------------------------------------------------------------------------
# 7. Performance test (in-process)
# ---------------------------------------------------------------------------

def test_performance_under_100ms():
    """Scoring 30 ADRs in-memory should complete in under 100ms.

    We bypass file I/O and call score_adr() directly to measure only the
    scoring algorithm. File I/O latency on Windows temp dirs is highly variable
    and is not part of the ranking algorithm's performance contract.
    """
    today = date.today()
    query = "architecture service layer component"
    keywords = extract_keywords(query)
    domain = infer_task_domain(query)

    # Build 30 synthetic metadata dicts without touching the filesystem
    adrs = []
    for i in range(1, 31):
        adr_date = today - timedelta(days=i * 30)
        adrs.append({
            "adr_id": f"ADR-{i:03d}",
            "title": f"Architecture Decision {i}",
            "status": "Accepted" if i % 2 == 0 else "Proposed",
            "domain_tags": "backend",
            "domain_has_keywords": True,
            "related_ids": [],
            "date": adr_date,
            "decision_text": (
                f"We use component {i} for service layer {i} to handle requests."
            ),
        })

    start = time.perf_counter()
    scores = [score_adr(query, keywords, domain, meta) for meta in adrs]
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 100, (
        f"score_adr() x30 took {elapsed_ms:.1f}ms (limit: 100ms). "
        "Scoring algorithm may have a performance regression."
    )
    assert len(scores) == 30
