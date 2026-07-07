"""Strict governance tests for adr-lint frontmatter validation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"
ADR_SCHEMA = REPO_ROOT / "bin" / "adr_schema.py"


def _load_schema_module():
    spec = importlib.util.spec_from_file_location("adr_schema", ADR_SCHEMA)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCHEMA = _load_schema_module()


def _body(num: int, title: str, status: str = "Accepted") -> str:
    return textwrap.dedent(
        f"""\
        # ADR-{num:03d} {title}

        ## Status

        {status}, 2026-07-06.

        ## Context

        Governance metadata improves local recall for agents.

        ## Decision

        Store and lint the decision metadata next to the ADR prose.

        ## Alternatives Considered

        - Prose only: rejected because local tools cannot query it precisely.
        - Hosted service: rejected because the workflow must remain local.

        ## Consequences

        **Positive:**
        - Agents can find the right ADRs with less re-derivation.

        **Negative:**
        - ADR files carry a small metadata block.

        ## Related Decisions

        - None.

        ## References

        - tests/test_adr_lint_governance.py
        """
    )


def _write_adr(
    adr_dir: Path,
    num: int,
    title: str,
    *,
    status: str = "Accepted",
    binding: bool = False,
    gate=None,
    documents_shipped: bool = False,
    verified_in=None,
    supersedes=None,
    superseded_by=None,
) -> Path:
    body = _body(num, title, status=status)
    data = {
        "id": f"ADR-{num:03d}",
        "title": title,
        "status": status,
        "date": "2026-07-06",
        "binding": binding,
        "gate": gate,
        "documents_shipped": documents_shipped,
        "verified_in": verified_in or [],
        "supersedes": supersedes or [],
        "superseded_by": superseded_by,
    }
    path = adr_dir / f"ADR-{num:03d}-{title.lower().replace(' ', '-')}.md"
    path.write_text(SCHEMA.render_frontmatter(data) + body, encoding="utf-8")
    return path


def _run_lint(adr_dir: Path, repo_root: Path, *extra: str):
    result = subprocess.run(
        [
            sys.executable,
            str(ADR_LINT),
            "--strict",
            "--format",
            "json",
            "--repo-root",
            str(repo_root),
            *extra,
            str(adr_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)
    return result.returncode, payload


def test_strict_mode_fails_missing_frontmatter(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-local-memory.md").write_text(_body(1, "Local Memory"), encoding="utf-8")

    code, out = _run_lint(adr_dir, tmp_path)

    assert code == 1
    assert out["strict_mode"] is True
    finding = out["files"][0]["findings"][0]
    assert finding["gate"] == "schema"
    assert finding["level"] == "FAIL"
    assert "missing canonical frontmatter" in finding["summary"]


def test_superseded_status_requires_superseded_by(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, "Old Decision", status="Superseded")

    code, out = _run_lint(adr_dir, tmp_path)

    assert code == 1
    summary = " ".join(
        f["summary"]
        for item in out["files"]
        for f in item["findings"]
        if f["gate"] == "consistency"
    )
    assert "status Superseded requires superseded_by" in summary


def test_supersedes_must_reciprocate(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, "New Decision", supersedes=["ADR-002"])
    _write_adr(adr_dir, 2, "Old Decision", status="Superseded", superseded_by="ADR-003")

    code, out = _run_lint(adr_dir, tmp_path)

    assert code == 1
    by_num = {item["adr_num"]: item for item in out["files"]}
    summary = " ".join(f["summary"] for f in by_num[1]["findings"])
    assert "supersedes ADR-002 but ADR-002.superseded_by is not ADR-001" in summary


def test_verified_in_file_symbol_must_resolve(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    source_dir = tmp_path / "src"
    adr_dir.mkdir(parents=True)
    source_dir.mkdir()
    (source_dir / "app.py").write_text("def important_symbol():\n    pass\n", encoding="utf-8")
    _write_adr(
        adr_dir,
        1,
        "Verified Evidence",
        documents_shipped=True,
        verified_in=["src/app.py:important_symbol"],
    )

    code, out = _run_lint(adr_dir, tmp_path)

    assert code == 0, out
    assert out["summary"]["fail"] == 0


def test_accepted_binding_requires_existing_gate(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, "Binding Gate", binding=True, gate="memory_recall_gate")

    code, out = _run_lint(adr_dir, tmp_path)

    assert code == 1
    summary = " ".join(f["summary"] for f in out["files"][0]["findings"])
    assert "gate 'memory_recall_gate' was not found" in summary


def test_accepted_binding_gate_passes_when_found_locally(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (tmp_path / "evaluate.py").write_text(
        "def memory_recall_gate():\n    return True\n",
        encoding="utf-8",
    )
    _write_adr(adr_dir, 1, "Binding Gate", binding=True, gate="memory_recall_gate")

    code, out = _run_lint(adr_dir, tmp_path)

    assert code == 0, out
    assert out["summary"]["fail"] == 0

