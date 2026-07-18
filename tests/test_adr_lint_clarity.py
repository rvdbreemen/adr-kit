"""End-to-end tests for the clarity gate of bin/adr-lint.

The gate flags ALL-CAPS acronyms that are never expanded. These tests pin the
three refinements that keep it from firing on records it cannot help:
allowlisted vocabulary, the 'expansion (ACRONYM)' word order, and YAML
frontmatter, where an inline expansion cannot be written at all.

Each test runs the CLI as a subprocess and asserts on the JSON output, so it
verifies the public interface rather than internal helpers.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"

FRONTMATTER = """---
id: "ADR-042"
title: "JSON Graph Index"
status: "Proposed"
date: "2026-07-18"
format: "madr"
---
"""


def lint_clarity(tmp_path: Path, body: str):
    """Lint a single generated ADR with only the clarity gate enabled."""
    path = tmp_path / "ADR-042-sample.md"
    path.write_text(FRONTMATTER + body, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", "--gates", "clarity",
         str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, json.loads(result.stdout)


def clarity_finding(out):
    """Return the clarity finding for the single linted file, or None."""
    findings = out["files"][0]["findings"]
    return next((f for f in findings if f["gate"] == "clarity"), None)


def test_unexplained_acronyms_still_fail(tmp_path):
    """Three distinct unexplained, non-allowlisted acronyms remain a failure."""
    code, out = lint_clarity(tmp_path, "# ADR-042\n\nThe GHZ, FWQ and PLM parts.\n")
    assert code != 0
    assert clarity_finding(out)["level"] == "FAIL"


def test_allowlisted_acronyms_do_not_fail(tmp_path):
    """Universal technical vocabulary needs no inline expansion."""
    code, out = lint_clarity(tmp_path, "# ADR-042\n\nThe JSON, YAML and HTTP parts.\n")
    assert code == 0
    assert clarity_finding(out) is None


def test_expansion_before_acronym_counts_as_expanded(tmp_path):
    """'expansion (ACRONYM)' is accepted, not only 'ACRONYM (expansion)'."""
    body = (
        "# ADR-042\n\n"
        "The generic host protocol (GHZ), fast write queue (FWQ) and "
        "platform layer module (PLM) parts.\n"
    )
    code, out = lint_clarity(tmp_path, body)
    assert code == 0
    assert clarity_finding(out) is None


def test_frontmatter_acronyms_are_ignored(tmp_path):
    """Metadata cannot carry an inline expansion, so it must not be flagged."""
    frontmatter = FRONTMATTER.replace(
        '"JSON Graph Index"', '"GHZ FWQ PLM Index"'
    )
    path = tmp_path / "ADR-042-sample.md"
    path.write_text(frontmatter + "# ADR-042\n\nA plain body.\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", "--gates", "clarity",
         str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0
    assert clarity_finding(json.loads(result.stdout)) is None


def test_summary_counts_every_distinct_acronym(tmp_path):
    """Details are capped at five hits; the summary still counts them all."""
    acronyms = ["GHZ", "FWQ", "PLM", "KZT", "VBQ", "XRD", "NJP"]
    body = "# ADR-042\n\n" + "".join(f"The {a} part.\n" for a in acronyms)
    code, out = lint_clarity(tmp_path, body)
    assert code != 0
    finding = clarity_finding(out)
    assert len(finding["details"]) == 5
    assert finding["summary"].startswith(f"{len(acronyms)} acronym(s)")


def test_shipped_adrs_pass_the_acceptance_gate_set(tmp_path):
    """The records this repository ships must be acceptable by its own tooling."""
    for adr in ("ADR-006", "ADR-007"):
        matches = sorted((REPO_ROOT / "docs" / "adr").glob(f"{adr}-*.md"))
        assert matches, f"{adr} not found"
        result = subprocess.run(
            [sys.executable, str(ADR_LINT), "--format", "json", "--strict",
             "--gates", "schema,completeness,audit,evidence,clarity,consistency,policy",
             "--repo-root", str(REPO_ROOT), str(matches[0])],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0, f"{adr} fails its own acceptance gates"
