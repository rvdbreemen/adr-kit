"""Tests for template-profile detection and the adr-discover template_profile
finding (task-5: MADR / Nygard format compatibility).

Three layers:
1. detect_template_profile() classifies the fixtures correctly
   (canonical, madr, nygard, plus migrated counterparts as canonical).
2. bin/adr-discover accepts supported MADR / Nygard shapes and flags only
   unsupported or hybrid profiles.
3. The hand-migrated canonical versions of both fixtures pass bin/adr-lint
   strictly. The migrate skill performs the live mapping; these fixtures
   document the expected lint-clean outcome.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DISCOVER = REPO_ROOT / "bin" / "adr-discover"
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"
FIXTURES = REPO_ROOT / "tests" / "fixtures"

MADR_FIXTURE = FIXTURES / "madr" / "0009-use-postgresql-for-persistence.md"
NYGARD_FIXTURE = FIXTURES / "nygard" / "0010-use-asynchronous-messaging.md"
CANONICAL_FIXTURE = FIXTURES / "canonical" / "ADR-001-clean-baseline.md"
MADR_MIGRATED = FIXTURES / "madr-migrated" / "ADR-009-use-postgresql-for-persistence.md"
NYGARD_MIGRATED = FIXTURES / "nygard-migrated" / "ADR-010-use-asynchronous-messaging.md"


def _load_audit_module():
    """bin/adr-discover has no .py extension; load it via SourceFileLoader."""
    loader = importlib.machinery.SourceFileLoader("adr_discover", str(ADR_DISCOVER))
    spec = importlib.util.spec_from_loader("adr_discover", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


AUDIT = _load_audit_module()


def _detect(path: Path) -> str:
    return AUDIT.detect_template_profile(path.read_text(encoding="utf-8"))


# ---------- layer 1: detection ----------


def test_detects_madr_fixture():
    assert _detect(MADR_FIXTURE) == "madr"


def test_detects_nygard_fixture():
    assert _detect(NYGARD_FIXTURE) == "nygard"


def test_detects_canonical_fixture():
    assert _detect(CANONICAL_FIXTURE) == "canonical"


def test_migrated_fixtures_detect_as_canonical():
    assert _detect(MADR_MIGRATED) == "canonical"
    assert _detect(NYGARD_MIGRATED) == "canonical"


def test_unknown_for_unrelated_markdown():
    text = "# Release notes\n\n## Highlights\n\n- Faster.\n"
    assert AUDIT.detect_template_profile(text) == "unknown"


def test_headings_inside_code_fences_are_ignored():
    """A Nygard skeleton quoted inside a fence must not trigger detection."""
    text = (
        "# Style guide\n\n"
        "## Example\n\n"
        "```markdown\n"
        "## Status\n## Context\n## Decision\n## Consequences\n"
        "```\n"
    )
    assert AUDIT.detect_template_profile(text) == "unknown"


def test_frontmatter_status_counts_as_madr_signal():
    """Frontmatter status plus one MADR heading is enough (two signals)."""
    text = (
        "---\nstatus: proposed\n---\n\n"
        "# Pick a queue\n\n"
        "## Context and Problem Statement\n\nWhich queue?\n"
    )
    assert AUDIT.detect_template_profile(text) == "madr"


def test_single_madr_signal_is_not_enough():
    text = "# Doc\n\n## Considered Options\n\n- A\n- B\n"
    assert AUDIT.detect_template_profile(text) == "unknown"


# ---------- layer 2: adr-discover flags madr / nygard ADRs ----------


def _run_audit(project_root: Path):
    result = subprocess.run(
        [sys.executable, str(ADR_DISCOVER), "--root", str(project_root)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_audit_accepts_supported_madr_and_nygard_adrs(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    shutil.copy(MADR_FIXTURE, adr_dir / MADR_FIXTURE.name)
    shutil.copy(NYGARD_FIXTURE, adr_dir / NYGARD_FIXTURE.name)

    out = _run_audit(tmp_path)
    findings = [c for c in out["candidates"] if c["decision_type"] == "template_profile"]
    assert findings == []


def test_audit_does_not_flag_canonical_adrs(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    shutil.copy(CANONICAL_FIXTURE, adr_dir / CANONICAL_FIXTURE.name)

    out = _run_audit(tmp_path)
    findings = [c for c in out["candidates"] if c["decision_type"] == "template_profile"]
    assert findings == []


def test_audit_does_not_flag_configured_supported_profile(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    shutil.copy(NYGARD_FIXTURE, adr_dir / NYGARD_FIXTURE.name)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"template": {"profile": "nygard"}}), encoding="utf-8"
    )

    out = _run_audit(tmp_path)
    findings = [c for c in out["candidates"] if c["decision_type"] == "template_profile"]
    assert findings == []


def test_audit_flags_hybrid_profile_with_declared_project_default(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    hybrid = (
        "# ADR-001 Hybrid\n\n"
        "## Status\n\nProposed\n\n"
        "## Context\n\nA.\n\n"
        "## Context and Problem Statement\n\nB.\n\n"
        "## Decision\n\nA.\n\n"
        "## Decision Outcome\n\nB.\n\n"
        "## Consequences\n\nC.\n"
    )
    (adr_dir / "ADR-001-hybrid.md").write_text(hybrid, encoding="utf-8")
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"template": {"profile": "madr"}}), encoding="utf-8"
    )
    out = _run_audit(tmp_path)
    findings = [c for c in out["candidates"] if c["decision_type"] == "template_profile"]
    assert len(findings) == 1
    assert findings[0]["details"]["template_profile"] == "hybrid"
    assert findings[0]["details"]["declared_profile"] == "madr"


# ---------- layer 3: migrated fixtures pass adr-lint ----------


def _run_lint(target: Path):
    return subprocess.run(
        [sys.executable, str(ADR_LINT), str(target)],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_migrated_madr_fixture_passes_lint():
    result = _run_lint(MADR_MIGRATED.parent)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS strictly (1)" in result.stdout
    assert "FAIL (0)" in result.stdout


def test_migrated_nygard_fixture_passes_lint():
    result = _run_lint(NYGARD_MIGRATED.parent)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS strictly (1)" in result.stdout
    assert "FAIL (0)" in result.stdout
