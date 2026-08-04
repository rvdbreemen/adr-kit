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

import pytest

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
    """The records this repository ships must be acceptable by its own tooling.

    `--context-dir` is not optional decoration here: it is what `bin/adr accept`
    passes, and without it this test does not reproduce the acceptance path it
    claims to. A single-file lint cannot resolve a declared `related` link,
    because the target is a file it was never given -- so the moment any shipped
    ADR gained a cross-reference, this test failed on a record that accepts
    cleanly. Reproduced: ADR-007 with `related: [ADR-021]` fails without the flag
    and passes with it.
    """
    for adr in ("ADR-006", "ADR-007"):
        matches = sorted((REPO_ROOT / "docs" / "adr").glob(f"{adr}-*.md"))
        assert matches, f"{adr} not found"
        result = subprocess.run(
            [sys.executable, str(ADR_LINT), "--format", "json", "--strict",
             "--gates", "schema,completeness,audit,evidence,clarity,consistency,policy",
             "--repo-root", str(REPO_ROOT),
             "--context-dir", str(REPO_ROOT / "docs" / "adr"),
             str(matches[0])],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0, f"{adr} fails its own acceptance gates"


# ---------------------------------------------------------------------------
# The acronym heuristic is bounded to findings an author can act on (TASK-111)
# ---------------------------------------------------------------------------

def _clarity(tmp_path, insert: str) -> int:
    source = sorted((REPO_ROOT / "docs" / "adr").glob("ADR-020-*.md"))[0]
    body = source.read_text(encoding="utf-8").replace(
        "## Decision Drivers", "## Decision Drivers\n\n" + insert
    )
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "ADR-020-x.md").write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(ADR_LINT), "--gates", "clarity", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).returncode


def test_three_unexpanded_acronyms_in_prose_still_fail(tmp_path):
    """The negative control. Bounding a heuristic must not disable it."""
    assert _clarity(
        tmp_path, "* The OTGW firmware talks to the HVAC unit over the MQTT bridge.\n"
    ) != 0


def test_an_acronym_in_an_inline_code_span_is_not_prose(tmp_path):
    assert _clarity(
        tmp_path, "* Config keys `OTGW`, `HVAC` and `MQTT` are read verbatim.\n"
    ) == 0


def test_an_acronym_in_a_fenced_block_is_not_prose(tmp_path):
    """A fenced block quotes code, output or configuration.

    An acronym there cannot carry an inline expansion without changing what the
    record is quoting -- the gate would be asking the author to falsify an
    example.
    """
    assert _clarity(tmp_path, "```\nOTGW HVAC MQTT\n```\n") == 0


def test_an_expanded_acronym_passes(tmp_path):
    assert _clarity(
        tmp_path,
        "* The OTGW (OpenTherm Gateway) drives the HVAC (heating) unit over "
        "MQTT (a message broker).\n",
    ) == 0


def test_two_acronyms_stay_below_the_threshold(tmp_path):
    """Deliberately conservative: a false positive costs a blocked decision."""
    assert _clarity(tmp_path, "* The OTGW firmware talks to the HVAC unit.\n") == 0


@pytest.mark.parametrize("term", ["LLM", "FAIL", "DUE", "TODO", "PASS"])
def test_this_projects_own_vocabulary_is_not_an_unexplained_acronym(term):
    """`LLM` is the product's subject; `FAIL` and `DUE` are literal output tokens.

    Asking an author to write "FAIL (failure)" makes the record worse in order
    to satisfy a check, which is the contortion spec R15 exists to prevent.
    """
    import importlib.machinery
    import importlib.util

    name = "adr_lint_allowlist_probe"
    cached = sys.modules.get(name)
    if cached is None:
        loader = importlib.machinery.SourceFileLoader(name, str(ADR_LINT))
        spec = importlib.util.spec_from_loader(name, loader)
        cached = importlib.util.module_from_spec(spec)
        sys.modules[name] = cached
        loader.exec_module(cached)

    assert term in cached.CLARITY_ACRONYM_ALLOWLIST
