"""Tests for after-the-fact ADR document + auto-accept flow."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ADR = REPO_ROOT / "bin" / "adr"
ADR_INDEX = REPO_ROOT / "bin" / "adr-index"
ADR_SCHEMA = REPO_ROOT / "bin" / "adr_schema.py"


def _load_schema_module():
    spec = importlib.util.spec_from_file_location("adr_schema", ADR_SCHEMA)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCHEMA = _load_schema_module()


def _body(status: str = "Proposed") -> str:
    return textwrap.dedent(
        f"""\
        # ADR-001 Shipped Local Recall Metadata

        ## Status

        {status}, 2026-07-01.

        ## Context

        A shipped implementation already stores recall metadata locally in source files,
        and the ADR needs to document that existing behavior without using a hosted
        service or an external memory database.

        ## Decision

        Document the shipped local recall metadata contract in canonical ADR
        frontmatter and require local evidence pointers before accepting the ADR, so
        future agents can verify the decision without asking a remote service.

        ## Alternatives Considered

        - Keep the ADR Proposed forever: rejected because the implementation already shipped.
        - Accept without evidence: rejected because future agents cannot validate the claim.

        ## Consequences

        **Positive:**
        - Recall lookup stays local and evidence-backed with 1 source pointer.

        **Negative:**
        - Authors must keep verified_in pointers accurate when files move.

        ## Related Decisions

        - None.

        ## References

        - src/app.py:1
        - https://example.com/adr-kit-local-evidence
        """
    )


def _write_adr(adr_dir: Path, *, documents_shipped=False, verified_in=None) -> Path:
    data = {
        "id": "ADR-001",
        "title": "Shipped Local Recall Metadata",
        "status": "Proposed",
        "date": "2026-07-01",
        "binding": False,
        "gate": None,
        "documents_shipped": documents_shipped,
        "verified_in": verified_in or [],
        "supersedes": [],
        "superseded_by": None,
    }
    path = adr_dir / "ADR-001-shipped-local-recall-metadata.md"
    path.write_text(SCHEMA.render_frontmatter(data) + _body(), encoding="utf-8")
    return path


def _frontmatter(path: Path):
    raw, body = SCHEMA.split_frontmatter(path.read_text(encoding="utf-8"))
    return SCHEMA.parse_frontmatter(raw), body


def _run_adr(*args: str):
    return subprocess.run(
        [sys.executable, str(ADR), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _index_check(adr_dir: Path):
    return subprocess.run(
        [sys.executable, str(ADR_INDEX), "--check", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _repo(tmp_path: Path):
    adr_dir = tmp_path / "docs" / "adr"
    src_dir = tmp_path / "src"
    adr_dir.mkdir(parents=True)
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def shipped_symbol():\n    pass\n", encoding="utf-8")
    return adr_dir


def test_document_requires_verified_in(tmp_path):
    adr_dir = _repo(tmp_path)
    path = _write_adr(adr_dir)

    result = _run_adr("document", "1", "--adr-dir", str(adr_dir))

    assert result.returncode == 2
    data, _body_text = _frontmatter(path)
    assert data["documents_shipped"] is False


def test_document_then_auto_accept_with_verified_evidence(tmp_path):
    adr_dir = _repo(tmp_path)
    path = _write_adr(adr_dir)
    documented = _run_adr(
        "document",
        "1",
        "--adr-dir",
        str(adr_dir),
        "--verified-in",
        "src/app.py:shipped_symbol",
        "--date",
        "2026-07-06",
        "--changed-by",
        "Codex",
    )
    assert documented.returncode == 0, documented.stderr + documented.stdout

    accepted = _run_adr(
        "accept",
        "1",
        "--auto",
        "--adr-dir",
        str(adr_dir),
        "--repo-root",
        str(tmp_path),
        "--date",
        "2026-07-06",
        "--changed-by",
        "Codex",
    )

    assert accepted.returncode == 0, accepted.stderr + accepted.stdout
    data, body = _frontmatter(path)
    assert data["status"] == "Accepted"
    assert data["documents_shipped"] is True
    assert data["verified_in"] == ["src/app.py:shipped_symbol"]
    assert "Auto-accepted already-shipped ADR with verified evidence" in body
    assert _index_check(adr_dir).returncode == 0


def test_auto_accept_blocks_broken_verified_pointer_without_mutation(tmp_path):
    adr_dir = _repo(tmp_path)
    path = _write_adr(
        adr_dir,
        documents_shipped=True,
        verified_in=["src/app.py:missing_symbol"],
    )

    result = _run_adr(
        "accept",
        "1",
        "--auto",
        "--adr-dir",
        str(adr_dir),
        "--repo-root",
        str(tmp_path),
    )

    assert result.returncode == 2
    data, _body_text = _frontmatter(path)
    assert data["status"] == "Proposed"


def test_auto_accept_blocks_documents_shipped_false(tmp_path):
    adr_dir = _repo(tmp_path)
    path = _write_adr(adr_dir, verified_in=["src/app.py:shipped_symbol"])

    result = _run_adr(
        "accept",
        "1",
        "--auto",
        "--adr-dir",
        str(adr_dir),
        "--repo-root",
        str(tmp_path),
    )

    assert result.returncode == 2
    assert "documents_shipped:true" in result.stderr
    data, _body_text = _frontmatter(path)
    assert data["status"] == "Proposed"


def test_assist_mode_reports_eligibility_without_confirmation_or_mutation(tmp_path):
    adr_dir = _repo(tmp_path)
    path = _write_adr(
        adr_dir,
        documents_shipped=True,
        verified_in=["src/app.py:shipped_symbol"],
    )

    result = _run_adr(
        "accept",
        "1",
        "--auto",
        "--auto-mode",
        "assist",
        "--adr-dir",
        str(adr_dir),
        "--repo-root",
        str(tmp_path),
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "rerun with --confirm" in result.stdout
    data, _body_text = _frontmatter(path)
    assert data["status"] == "Proposed"

