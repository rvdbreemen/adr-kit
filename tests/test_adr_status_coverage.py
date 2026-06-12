"""Tests for the Enforcement coverage metric in bin/adr-status (task-4).

Coverage definitions (over Accepted ADRs only):
  coverage_pct:  percent of Accepted ADRs with a parseable Enforcement block
                 carrying at least one rule.
  llm_judge_pct: percent of Accepted ADRs whose Enforcement includes
                 llm_judge: true.

Uses the same importlib + subprocess strategy as test_adr_status.py.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_STATUS = REPO_ROOT / "bin" / "adr-status"


# ---------------------------------------------------------------------------
# importlib loader (no .py extension on the binary)
# ---------------------------------------------------------------------------

def _load_module():
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("adr_status_cov", str(ADR_STATUS))
    spec = importlib.util.spec_from_loader("adr_status_cov", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_module()
compute_summary = _mod.compute_summary
load_adr_set = _mod.load_adr_set


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_ENF_RULES_ONLY = json.dumps({
    "forbid_pattern": [{"pattern": "\\bFoo\\b", "path_glob": "src/**/*.py",
                        "message": "Do not use Foo."}],
    "forbid_import": [],
    "require_pattern": [],
    "llm_judge": False,
})

_ENF_LLM_JUDGE = json.dumps({
    "forbid_pattern": [],
    "forbid_import": [],
    "require_pattern": [],
    "llm_judge": True,
})

_ENF_EMPTY = json.dumps({
    "forbid_pattern": [],
    "forbid_import": [],
    "require_pattern": [],
    "llm_judge": False,
})

_ENF_BROKEN = "{ this is not valid json }"


def _write_adr(
    adr_dir: Path,
    num: int,
    status: str = "Accepted",
    enforcement_json: str | None = None,
) -> None:
    enf_block = ""
    if enforcement_json is not None:
        enf_block = f"\n## Enforcement\n\n```json\n{enforcement_json}\n```\n"
    content = (
        f"# ADR-{num:03d} Test ADR {num}\n\n"
        f"## Status\n\n{status}, 2024-01-15\n\n"
        f"## Decision\n\nSomething.\n{enf_block}"
    )
    adr_dir.mkdir(parents=True, exist_ok=True)
    (adr_dir / f"ADR-{num:03d}-test.md").write_text(content, encoding="utf-8")


def _summary_for(adr_dir: Path) -> dict:
    return compute_summary(load_adr_set(adr_dir))


def _run_cli(args: list) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(ADR_STATUS)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# coverage_pct
# ---------------------------------------------------------------------------

class TestCoveragePct:

    def test_zero_percent_no_enforcement(self, tmp_path):
        """Accepted ADRs without Enforcement: 0% coverage."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1)
        _write_adr(adr_dir, 2)
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 0.0
        assert s["llm_judge_pct"] == 0.0

    def test_partial_coverage(self, tmp_path):
        """1 of 2 Accepted ADRs enforced: 50%."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_RULES_ONLY)
        _write_adr(adr_dir, 2)
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 50.0

    def test_full_coverage(self, tmp_path):
        """All Accepted ADRs enforced: 100%."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_RULES_ONLY)
        _write_adr(adr_dir, 2, enforcement_json=_ENF_LLM_JUDGE)
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 100.0

    def test_llm_judge_split(self, tmp_path):
        """4 Accepted: 2 enforced, 1 of them llm_judge -> 50% / 25%."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_RULES_ONLY)
        _write_adr(adr_dir, 2, enforcement_json=_ENF_LLM_JUDGE)
        _write_adr(adr_dir, 3)
        _write_adr(adr_dir, 4)
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 50.0
        assert s["llm_judge_pct"] == 25.0

    def test_empty_rules_not_counted(self, tmp_path):
        """A parseable Enforcement block with zero rules does not count."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_EMPTY)
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 0.0

    def test_broken_json_not_counted(self, tmp_path):
        """An unparseable Enforcement block does not count as coverage."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_BROKEN)
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 0.0

    def test_non_accepted_excluded_from_denominator(self, tmp_path):
        """Proposed/Superseded ADRs do not dilute or inflate the percentage."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, status="Accepted", enforcement_json=_ENF_RULES_ONLY)
        _write_adr(adr_dir, 2, status="Proposed")
        _write_adr(adr_dir, 3, status="Superseded", enforcement_json=_ENF_RULES_ONLY)
        s = _summary_for(adr_dir)
        # 1 Accepted, 1 enforced -> 100%
        assert s["coverage_pct"] == 100.0

    def test_empty_dir_is_zero(self, tmp_path):
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        s = _summary_for(adr_dir)
        assert s["coverage_pct"] == 0.0
        assert s["llm_judge_pct"] == 0.0


# ---------------------------------------------------------------------------
# Output format stability (additive only)
# ---------------------------------------------------------------------------

class TestOutputFormats:

    def test_json_field_names_stable(self, tmp_path):
        """Existing summary keys are untouched; new keys are additive."""
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_RULES_ONLY)
        _write_adr(adr_dir, 2)
        rc, out, err = _run_cli(["--format", "json", "--adr-dir", str(adr_dir)])
        assert rc == 0
        data = json.loads(out)
        summary = data["summary"]
        # Pre-existing keys must still be present under the same names.
        for key in ("total", "by_status", "health_pct", "avg_age_days",
                    "with_enforcement", "enforcement_valid_pct"):
            assert key in summary
        # New additive keys.
        assert summary["coverage_pct"] == 50.0
        assert summary["llm_judge_pct"] == 0.0
        # Top-level structure unchanged.
        assert "adrs" in data
        assert "retirement_candidates" in data

    def test_table_output_has_coverage_line(self, tmp_path):
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_LLM_JUDGE)
        rc, out, err = _run_cli(["--format", "table", "--adr-dir", str(adr_dir)])
        assert rc == 0
        assert "Coverage:" in out
        assert "100.0% of Accepted ADRs enforced" in out
        assert "llm_judge: 100.0%" in out

    def test_markdown_output_has_coverage_row(self, tmp_path):
        adr_dir = tmp_path / "adr"
        _write_adr(adr_dir, 1, enforcement_json=_ENF_RULES_ONLY)
        rc, out, err = _run_cli(["--format", "markdown", "--adr-dir", str(adr_dir)])
        assert rc == 0
        assert "| Enforcement coverage | 100.0% of Accepted (llm_judge: 0.0%) |" in out
