"""End-to-end tests for bin/adr-audit.

The scanner is deterministic — given the same project state, the candidate
JSON is reproducible. These tests verify shape and key signal extraction.
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_AUDIT = REPO_ROOT / "bin" / "adr-audit"


def _run(project_root: Path, *extra):
    result = subprocess.run(
        [sys.executable, str(ADR_AUDIT), "--root", str(project_root), *extra],
        capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    return result.returncode, json.loads(result.stdout)


def test_empty_project_zero_candidates(tmp_path):
    code, out = _run(tmp_path)
    assert code == 0
    assert out["candidate_count"] == 0
    assert out["candidates"] == []


def test_tooling_markers_detected(tmp_path):
    (tmp_path / "Makefile").write_text("all:\n\techo ok\n")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    code, out = _run(tmp_path)
    assert code == 0
    ids = {c["id"] for c in out["candidates"]}
    assert "tooling-makefile" in ids
    assert "tooling-dockerfile" in ids


def test_package_json_dependency_extraction(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.0", "express": "^4.0"},
                    "devDependencies": {"jest": "^29.0"}})
    )
    code, out = _run(tmp_path)
    assert code == 0
    deps_candidate = next(c for c in out["candidates"] if c["id"] == "deps-package-json")
    assert "react" in deps_candidate["details"]["sample"]
    assert "jest" in deps_candidate["details"]["sample"]


def test_doc_decision_phrase_grouped_per_file(tmp_path):
    """A doc with three decision phrases produces ONE candidate, not three."""
    (tmp_path / "README.md").write_text(textwrap.dedent("""\
        # Project

        We chose React over Vue for ecosystem reasons.
        We decided to use TypeScript instead of plain JS.
        Rejected: Mongoose, because we prefer raw queries.
    """))
    code, out = _run(tmp_path)
    assert code == 0
    doc_cands = [c for c in out["candidates"] if c["decision_type"] == "documented"]
    assert len(doc_cands) == 1
    snippets = doc_cands[0]["details"]["snippets"]
    assert len(snippets) >= 2
    assert doc_cands[0]["details"]["match_count"] >= 3


def test_skip_glob_excludes_path(tmp_path):
    """--skip pattern excludes matching paths from the doc scan."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "noisy.md").write_text("we decided to keep this out\n")
    code, out = _run(tmp_path, "--skip", "docs/**")
    assert code == 0
    doc_cands = [c for c in out["candidates"] if c["decision_type"] == "documented"]
    assert all("docs/noisy.md" not in (c["evidence_files"][0] if c["evidence_files"] else "") for c in doc_cands)


def test_default_skip_excludes_existing_adrs(tmp_path):
    """docs/adr/** is in the default skip list so existing ADRs don't recurse."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "ADR-001-foo.md").write_text(
        "# ADR-001\n\nWe decided to do foo instead of bar.\n"
    )
    code, out = _run(tmp_path)
    assert code == 0
    assert out["candidates"] == []


def test_output_writes_file(tmp_path):
    (tmp_path / "Makefile").write_text("all:\n\techo ok\n")
    out_path = tmp_path / "candidates.json"
    result = subprocess.run(
        [sys.executable, str(ADR_AUDIT), "--root", str(tmp_path), "--output", str(out_path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["candidate_count"] >= 1
