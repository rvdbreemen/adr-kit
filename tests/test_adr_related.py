"""Tests for bin/adr-related - ADR dependency graph tool.

All subprocess calls use [sys.executable, SCRIPT] to work on Windows
(no shebang execution, no PATH tricks needed).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import pytest

# ---------------------------------------------------------------------------
# Script location
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).parent.parent / "bin" / "adr-related"


# ---------------------------------------------------------------------------
# Helper: import the module so we can call functions in-process
# ---------------------------------------------------------------------------

def _load_module():
    """Dynamically import bin/adr-related as a Python module."""
    loader = importlib.machinery.SourceFileLoader("adr_related", str(SCRIPT))
    spec = importlib.util.spec_from_loader("adr_related", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adr_related"] = mod
    loader.exec_module(mod)
    return mod


_mod = _load_module()
normalize_adr_id = _mod.normalize_adr_id
parse_adr_refs = _mod.parse_adr_refs
load_adr_set = _mod.load_adr_set
build_graph = _mod.build_graph
format_human = _mod.format_human


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_adr(
    directory: Path,
    number: int,
    title: str,
    status_line: str = "Accepted, 2026-01-01.",
    related: Optional[List[str]] = None,
    body_extra: str = "",
) -> Path:
    """Write a minimal but parseable ADR file."""
    padded = f"{number:03d}"
    slug = title.lower().replace(" ", "-")
    path = directory / f"ADR-{padded}-{slug}.md"
    related_lines = "\n".join(related) if related else "- None."
    content = f"""# ADR-{padded} {title}

## Status

{status_line}

## Context

Some context.{body_extra}

## Decision

Some decision.

## Related Decisions

{related_lines}
"""
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def adr_set(tmp_path: Path) -> Path:
    """A small ADR set with every edge kind present.

    ADR-001: superseded by ADR-002; related to ADR-003.
    ADR-002: supersedes ADR-001 (claim in Related Decisions).
    ADR-003: plain mention of ADR-001 in body, no declared relationship.
    ADR-004: amended by ADR-002; related to dangling ADR-099.
    """
    d = tmp_path / "adr"
    d.mkdir()
    _write_adr(
        d, 1, "Old decision",
        status_line="Superseded by ADR-002, 2026-02-01.",
        related=["- **ADR-003 (Sibling)**: complements."],
    )
    _write_adr(
        d, 2, "New decision",
        related=["- **ADR-001 (Old decision)**: Supersedes ADR-001."],
    )
    _write_adr(
        d, 3, "Sibling",
        body_extra=" See also ADR-001 for background.",
    )
    _write_adr(
        d, 4, "Amended one",
        status_line="Amended by ADR-002, 2026-03-01.",
        related=["- **ADR-099 (Ghost)**: depends on."],
    )
    return d


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _edge_kinds(edges, adr_id):
    return sorted(e["kind"] for e in edges if e["adr_id"] == adr_id)


# ---------------------------------------------------------------------------
# normalize_adr_id
# ---------------------------------------------------------------------------

class TestNormalizeAdrId:
    def test_full_form(self):
        assert normalize_adr_id("ADR-007") == "ADR-007"

    def test_lowercase_and_bare_number(self):
        assert normalize_adr_id("adr-7") == "ADR-007"
        assert normalize_adr_id("7") == "ADR-007"

    def test_four_digits(self):
        assert normalize_adr_id("ADR-0430") == "ADR-430"

    def test_invalid(self):
        assert normalize_adr_id("banana") is None
        assert normalize_adr_id("ADR-") is None
        assert normalize_adr_id("ADR-12345") is None


# ---------------------------------------------------------------------------
# Outbound edges
# ---------------------------------------------------------------------------

class TestOutbound:
    def test_related_edge(self, adr_set: Path):
        graph = build_graph("ADR-001", load_adr_set(adr_set))
        assert _edge_kinds(graph["outbound"], "ADR-003") == ["related"]

    def test_superseded_by_status_ref(self, adr_set: Path):
        graph = build_graph("ADR-001", load_adr_set(adr_set))
        assert _edge_kinds(graph["outbound"], "ADR-002") == ["superseded-by"]

    def test_supersedes_claim(self, adr_set: Path):
        graph = build_graph("ADR-002", load_adr_set(adr_set))
        kinds = _edge_kinds(graph["outbound"], "ADR-001")
        # Both the explicit "Supersedes ADR-001" claim and the Related
        # Decisions entry are reported.
        assert kinds == ["related", "supersedes"]

    def test_amended_by_status_ref(self, adr_set: Path):
        graph = build_graph("ADR-004", load_adr_set(adr_set))
        assert _edge_kinds(graph["outbound"], "ADR-002") == ["amended-by"]

    def test_plain_mention_not_outbound(self, adr_set: Path):
        graph = build_graph("ADR-003", load_adr_set(adr_set))
        # ADR-003 only mentions ADR-001 in prose; that is not a declared
        # outbound edge.
        assert _edge_kinds(graph["outbound"], "ADR-001") == []


# ---------------------------------------------------------------------------
# Inbound edges
# ---------------------------------------------------------------------------

class TestInbound:
    def test_supersedes_inbound(self, adr_set: Path):
        graph = build_graph("ADR-001", load_adr_set(adr_set))
        kinds = _edge_kinds(graph["inbound"], "ADR-002")
        assert "supersedes" in kinds

    def test_mention_inbound(self, adr_set: Path):
        graph = build_graph("ADR-001", load_adr_set(adr_set))
        assert _edge_kinds(graph["inbound"], "ADR-003") == ["mention"]

    def test_superseded_by_inbound(self, adr_set: Path):
        graph = build_graph("ADR-002", load_adr_set(adr_set))
        assert "superseded-by" in _edge_kinds(graph["inbound"], "ADR-001")
        assert "amended-by" in _edge_kinds(graph["inbound"], "ADR-004")

    def test_no_self_edges(self, adr_set: Path):
        for adr_id in ("ADR-001", "ADR-002", "ADR-003", "ADR-004"):
            graph = build_graph(adr_id, load_adr_set(adr_set))
            assert _edge_kinds(graph["outbound"], adr_id) == []
            assert _edge_kinds(graph["inbound"], adr_id) == []


# ---------------------------------------------------------------------------
# Dangling references
# ---------------------------------------------------------------------------

class TestDangling:
    def test_dangling_flagged(self, adr_set: Path):
        graph = build_graph("ADR-004", load_adr_set(adr_set))
        assert graph["dangling"] == ["ADR-099"]
        ghost = [e for e in graph["outbound"] if e["adr_id"] == "ADR-099"]
        assert ghost and ghost[0]["exists"] is False

    def test_dangling_in_human_output(self, adr_set: Path):
        graph = build_graph("ADR-004", load_adr_set(adr_set))
        text = format_human(graph)
        assert "DANGLING" in text
        assert "ADR-099" in text

    def test_clean_graph_no_dangling(self, adr_set: Path):
        graph = build_graph("ADR-001", load_adr_set(adr_set))
        assert graph["dangling"] == []


# ---------------------------------------------------------------------------
# Whole-token matching
# ---------------------------------------------------------------------------

class TestWholeToken:
    def test_no_prefix_match(self, tmp_path: Path):
        d = tmp_path / "adr"
        d.mkdir()
        _write_adr(d, 43, "Target")
        # ADR-0430 must not be read as a reference to ADR-043.
        _write_adr(d, 5, "Noisy", body_extra=" Mentions ADR-0430 only.")
        graph = build_graph("ADR-043", load_adr_set(d))
        assert graph["inbound"] == []

    def test_exact_token_matches(self, tmp_path: Path):
        d = tmp_path / "adr"
        d.mkdir()
        _write_adr(d, 43, "Target")
        _write_adr(d, 5, "Pointer", related=["- **ADR-043 (Target)**: depends on."])
        graph = build_graph("ADR-043", load_adr_set(d))
        assert _edge_kinds(graph["inbound"], "ADR-005") == ["related"]


# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------

class TestCli:
    def test_unknown_id_exit_2(self, adr_set: Path):
        result = _run("ADR-777", "--adr-dir", str(adr_set))
        assert result.returncode == 2
        assert "not found" in result.stderr

    def test_invalid_id_exit_2(self, adr_set: Path):
        result = _run("banana", "--adr-dir", str(adr_set))
        assert result.returncode == 2
        assert "invalid ADR id" in result.stderr

    def test_missing_dir_exit_2(self, tmp_path: Path):
        result = _run("ADR-001", "--adr-dir", str(tmp_path / "nope"))
        assert result.returncode == 2
        assert "directory not found" in result.stderr

    def test_success_exit_0_human(self, adr_set: Path):
        result = _run("ADR-001", "--adr-dir", str(adr_set))
        assert result.returncode == 0
        assert "Outbound" in result.stdout
        assert "Inbound" in result.stdout
        assert "ADR-002" in result.stdout

    def test_json_format_parses(self, adr_set: Path):
        result = _run("ADR-001", "--adr-dir", str(adr_set), "--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["adr"]["adr_id"] == "ADR-001"
        assert {"adr", "outbound", "inbound", "dangling"} <= set(data.keys())
        for edge in data["outbound"]:
            assert {"adr_id", "kind", "exists", "title", "status", "path"} <= set(edge.keys())

    def test_bare_number_accepted(self, adr_set: Path):
        result = _run("1", "--adr-dir", str(adr_set), "--format", "json")
        assert result.returncode == 0
        assert json.loads(result.stdout)["adr"]["adr_id"] == "ADR-001"
