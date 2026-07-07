"""Tests for bin/adr-doctor."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DOCTOR = REPO_ROOT / "bin" / "adr-doctor"
ADR_SCHEMA = REPO_ROOT / "bin" / "adr_schema.py"


def _load_schema_module():
    spec = importlib.util.spec_from_file_location("adr_schema", ADR_SCHEMA)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCHEMA = _load_schema_module()


def _body(num: int, title: str, status: str, date: str) -> str:
    return textwrap.dedent(
        f"""\
        # ADR-{num:03d} {title}

        ## Status

        {status}, {date}.

        ## Context

        Doctor checks keep local ADR memory fresh for agents.

        ## Decision

        Run local doctor checks around ADR work so generated indexes and recall
        metadata stay synchronized with the repository.

        ## Alternatives Considered

        - Manual review: rejected because agents forget to run it consistently.
        - Hosted scanner: rejected because adr-kit must remain local.

        ## Consequences

        **Positive:**
        - Local ADR health is visible before and after edits.

        **Negative:**
        - The doctor command adds one more local check to run.

        ## Related Decisions

        - None.

        ## References

        - tests/test_adr_doctor.py
        """
    )


def _write_adr(
    adr_dir: Path,
    *,
    num: int = 1,
    title: str = "Doctor Check",
    status: str = "Proposed",
    date: str = "2026-07-06",
    binding: bool = False,
    gate=None,
    verified_in=None,
) -> Path:
    data = {
        "id": f"ADR-{num:03d}",
        "title": title,
        "status": status,
        "date": date,
        "binding": binding,
        "gate": gate,
        "documents_shipped": bool(verified_in),
        "verified_in": verified_in or [],
        "supersedes": [],
        "superseded_by": None,
    }
    path = adr_dir / f"ADR-{num:03d}-{title.lower().replace(' ', '-')}.md"
    path.write_text(
        SCHEMA.render_frontmatter(data) + _body(num, title, status, date),
        encoding="utf-8",
    )
    return path


def _run_doctor(adr_dir: Path, repo_root: Path, *extra: str):
    result = subprocess.run(
        [
            sys.executable,
            str(ADR_DOCTOR),
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
    return result.returncode, json.loads(result.stdout)


def _repo(tmp_path: Path):
    adr_dir = tmp_path / "docs" / "adr"
    src_dir = tmp_path / "src"
    adr_dir.mkdir(parents=True)
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def shipped_symbol():\n    pass\n", encoding="utf-8")
    return adr_dir


def test_doctor_detects_stale_index_and_fix_index_cleans_it(tmp_path):
    adr_dir = _repo(tmp_path)
    _write_adr(adr_dir)

    stale_code, stale = _run_doctor(adr_dir, tmp_path)
    fixed_code, fixed = _run_doctor(adr_dir, tmp_path, "--fix-index")

    assert stale_code == 1
    assert stale["summary"]["index_ok"] is False
    assert fixed_code == 0
    assert fixed["summary"]["index_ok"] is True


def test_doctor_reports_shipped_but_proposed(tmp_path):
    adr_dir = _repo(tmp_path)
    _write_adr(adr_dir, verified_in=["src/app.py:shipped_symbol"])

    code, out = _run_doctor(adr_dir, tmp_path, "--fix-index")

    assert code == 1
    assert any(f["type"] == "shipped_but_proposed" for f in out["findings"])


def test_doctor_reports_old_proposed(tmp_path):
    adr_dir = _repo(tmp_path)
    _write_adr(adr_dir, date="2000-01-01")

    code, out = _run_doctor(adr_dir, tmp_path, "--fix-index", "--stale-days", "30")

    assert code == 1
    assert any(f["type"] == "old_proposed" for f in out["findings"])
    assert out["audit"]["triggered"] is False


def test_doctor_reports_accepted_evidence_changed_after_acceptance(tmp_path):
    adr_dir = _repo(tmp_path)
    _write_adr(
        adr_dir,
        status="Accepted",
        date="2000-01-01",
        verified_in=["src/app.py:shipped_symbol"],
    )

    code, out = _run_doctor(adr_dir, tmp_path, "--fix-index")

    assert code == 1
    assert any(f["type"] == "accepted_evidence_changed" for f in out["findings"])
    assert out["audit"]["triggered"] is True
    assert out["audit"]["reason"] == "material_drift"


def test_doctor_surfaces_missing_named_gate_from_strict_lint(tmp_path):
    adr_dir = _repo(tmp_path)
    _write_adr(
        adr_dir,
        status="Accepted",
        binding=True,
        gate="missing_memory_gate",
    )

    code, out = _run_doctor(adr_dir, tmp_path, "--fix-index")

    assert code == 1
    assert out["summary"]["lint_ok"] is False
    assert any(f["type"] == "missing_gate" for f in out["findings"])
    assert out["audit"]["triggered"] is True
    assert out["audit"]["reason"] == "material_drift"
