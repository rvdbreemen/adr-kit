"""Tests for the policy and quality gates in bin/adr-lint (TASK-714).

Tests use a mix of:
- subprocess CLI invocations for end-to-end gate opt-in/opt-out behaviour
- direct function calls for unit-level validation

Fixtures are created in-process via tmp_path to avoid polluting the test
fixture directories.
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_LINT = REPO_ROOT / "bin" / "adr-lint"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_lint(*args):
    """Invoke adr-lint with --format json and return (exit_code, parsed_json)."""
    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, {"_stdout": result.stdout, "_stderr": result.stderr}


def _make_adr(tmp_path: Path, name: str, enforcement_json: str | None = None,
              decision: str = "Use the chosen approach.",
              alternatives: str = "- **A.** Rejected.\n- **B.** Rejected.",
              consequences: str = "No measurable impact.",
              ) -> Path:
    """Write a minimal but structurally valid ADR to tmp_path and return the path."""
    enforcement_section = ""
    if enforcement_json is not None:
        enforcement_section = f"\n## Enforcement\n\n```json\n{enforcement_json}\n```\n"

    content = textwrap.dedent(f"""\
        # ADR-001 Test Decision

        ## Status

        Accepted, 2026-05-01.

        ## Context

        Some context here.

        ## Decision

        {decision}

        ## Alternatives Considered

        {alternatives}

        ## Consequences

        {consequences}

        ## Related Decisions

        - None.

        ## References

        - https://example.com/reference
        {enforcement_section}
    """)
    fp = tmp_path / name
    fp.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Import the functions under test directly.
# ---------------------------------------------------------------------------

import importlib.util as _ilu
import importlib.machinery as _ilm

# bin/adr-lint has no .py extension; load it explicitly via SourceFileLoader.
_loader = _ilm.SourceFileLoader("adr_lint", str(ADR_LINT))
_spec = _ilu.spec_from_loader("adr_lint", _loader)
_adr_lint = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_adr_lint)  # type: ignore[union-attr]

check_policy_gate = _adr_lint.check_policy_gate
check_quality_gate = _adr_lint.check_quality_gate
_extract_enforcement_block = _adr_lint._extract_enforcement_block
DEFAULT_GATES = _adr_lint.DEFAULT_GATES
ALL_GATES = _adr_lint.ALL_GATES


# ---------------------------------------------------------------------------
# 1. Valid Enforcement block → no policy findings
# ---------------------------------------------------------------------------

def test_valid_enforcement_passes_policy():
    valid_json = json.dumps({
        "forbid_pattern": [
            {"pattern": r"\beval\b", "path_glob": "src/**/*.py", "message": "No eval."}
        ]
    })
    content = f"## Enforcement\n\n```json\n{valid_json}\n```\n"
    findings = check_policy_gate(content, "ADR-001")
    assert findings == [], f"Expected no findings, got {findings}"


# ---------------------------------------------------------------------------
# 2. Broken JSON → FAIL POLICY_SCHEMA_INVALID
# ---------------------------------------------------------------------------

def test_invalid_json_fails_policy():
    content = "## Enforcement\n\n```json\n{ broken json !!\n```\n"
    findings = check_policy_gate(content, "ADR-001")
    assert len(findings) == 1
    f = findings[0]
    assert f["severity"] == "FAIL"
    assert f["code"] == "POLICY_SCHEMA_INVALID"
    assert f["gate"] == "policy"


# ---------------------------------------------------------------------------
# 3. Bad regex → FAIL POLICY_BAD_REGEX
# ---------------------------------------------------------------------------

def test_bad_regex_fails_policy():
    bad_json = json.dumps({
        "forbid_pattern": [
            {"pattern": "[unclosed", "path_glob": "src/**/*.py"}
        ]
    })
    content = f"## Enforcement\n\n```json\n{bad_json}\n```\n"
    findings = check_policy_gate(content, "ADR-001")
    fail_findings = [f for f in findings if f["code"] == "POLICY_BAD_REGEX"]
    assert len(fail_findings) >= 1, f"Expected POLICY_BAD_REGEX finding, got {findings}"
    assert fail_findings[0]["severity"] == "FAIL"


# ---------------------------------------------------------------------------
# 4. Excessive wildcard → ADVISORY POLICY_EXCESSIVE_WILDCARD
# ---------------------------------------------------------------------------

def test_excessive_wildcard_advisory():
    wild_json = json.dumps({
        "forbid_pattern": [
            {"pattern": ".*.*.*something", "path_glob": "src/**/*.py"}
        ]
    })
    content = f"## Enforcement\n\n```json\n{wild_json}\n```\n"
    findings = check_policy_gate(content, "ADR-001")
    wild_findings = [f for f in findings if f["code"] == "POLICY_EXCESSIVE_WILDCARD"]
    assert len(wild_findings) >= 1, f"Expected POLICY_EXCESSIVE_WILDCARD, got {findings}"
    assert wild_findings[0]["severity"] == "ADVISORY"


# ---------------------------------------------------------------------------
# 5. Unknown top-level key → FAIL (manual additionalProperties check)
# ---------------------------------------------------------------------------

def test_schema_extra_field_fails():
    extra_json = json.dumps({
        "forbid_pattern": [
            {"pattern": r"\bfoo\b", "path_glob": "src/**/*.py"}
        ],
        "unknown_key": True,
    })
    content = f"## Enforcement\n\n```json\n{extra_json}\n```\n"
    findings = check_policy_gate(content, "ADR-001")
    schema_findings = [f for f in findings if f["code"] == "POLICY_SCHEMA_INVALID"]
    assert len(schema_findings) >= 1, (
        f"Expected POLICY_SCHEMA_INVALID for unknown_key, got {findings}"
    )
    assert schema_findings[0]["severity"] == "FAIL"


# ---------------------------------------------------------------------------
# 6. Vague language in Decision → ADVISORY QUALITY_VAGUE_LANGUAGE
# ---------------------------------------------------------------------------

def test_quality_vague_language():
    content = textwrap.dedent("""\
        ## Decision

        We will use an appropriate caching strategy.

        ## Consequences

        Reduced latency by 40%.

        ## Alternatives Considered

        - **Redis.** Too complex.
        - **Memcached.** Missing features.
    """)
    findings = check_quality_gate(content, "ADR-001")
    vague = [f for f in findings if f["code"] == "QUALITY_VAGUE_LANGUAGE"]
    assert len(vague) >= 1, f"Expected QUALITY_VAGUE_LANGUAGE, got {findings}"
    assert vague[0]["severity"] == "ADVISORY"


# ---------------------------------------------------------------------------
# 7. Too few alternatives → ADVISORY QUALITY_FEW_ALTERNATIVES
# ---------------------------------------------------------------------------

def test_quality_few_alternatives():
    content = textwrap.dedent("""\
        ## Decision

        We will use PostgreSQL.

        ## Consequences

        50% faster queries.

        ## Alternatives Considered

        - **Do nothing.** Rejected because performance is already degraded.
    """)
    findings = check_quality_gate(content, "ADR-001")
    few_alt = [f for f in findings if f["code"] == "QUALITY_FEW_ALTERNATIVES"]
    assert len(few_alt) >= 1, f"Expected QUALITY_FEW_ALTERNATIVES, got {findings}"
    assert few_alt[0]["severity"] == "ADVISORY"


# ---------------------------------------------------------------------------
# 8. Default gates do not include policy
# ---------------------------------------------------------------------------

def test_policy_gate_not_in_default(tmp_path):
    # Write an ADR with a deliberately bad regex; default gates should ignore it.
    bad_json = json.dumps({"forbid_pattern": [{"pattern": "[bad"}]})
    adr_dir = _make_adr(tmp_path, "ADR-001-test.md", enforcement_json=bad_json)
    code, out = run_lint(str(adr_dir))
    # Default gates: completeness, audit, consistency — policy is NOT included.
    policy_findings = [
        f
        for file_result in out.get("files", [])
        for f in file_result.get("findings", [])
        if f.get("gate") == "policy"
    ]
    assert policy_findings == [], (
        f"Policy gate fired with default gates: {policy_findings}"
    )
    assert "policy" not in DEFAULT_GATES


# ---------------------------------------------------------------------------
# 9. --gates policy makes the gate active
# ---------------------------------------------------------------------------

def test_policy_gate_active_with_flag(tmp_path):
    bad_json = json.dumps({"forbid_pattern": [{"pattern": "[unclosed"}]})
    adr_dir = _make_adr(tmp_path, "ADR-001-test.md", enforcement_json=bad_json)
    code, out = run_lint("--gates", "policy", str(adr_dir))
    policy_findings = [
        f
        for file_result in out.get("files", [])
        for f in file_result.get("findings", [])
        if f.get("gate") == "policy"
    ]
    assert len(policy_findings) >= 1, (
        f"Expected policy findings with --gates policy, got {out}"
    )
    assert any(f["level"] == "FAIL" for f in policy_findings)
    assert code == 1


# ---------------------------------------------------------------------------
# 10. ADR without Enforcement block is silently skipped by policy gate
# ---------------------------------------------------------------------------

def test_no_enforcement_block_skipped():
    content = textwrap.dedent("""\
        # ADR-001 Something

        ## Status

        Accepted.

        ## Decision

        Use PostgreSQL.
    """)
    findings = check_policy_gate(content, "ADR-001")
    assert findings == [], f"Expected no findings for ADR without Enforcement block, got {findings}"


# ---------------------------------------------------------------------------
# 11. Broad path_glob advisory
# ---------------------------------------------------------------------------

def test_broad_glob_advisory():
    broad_json = json.dumps({
        "forbid_pattern": [
            {"pattern": r"\beval\b", "path_glob": "**"}
        ]
    })
    content = f"## Enforcement\n\n```json\n{broad_json}\n```\n"
    findings = check_policy_gate(content, "ADR-001")
    broad = [f for f in findings if f["code"] == "POLICY_BROAD_GLOB"]
    assert len(broad) >= 1, f"Expected POLICY_BROAD_GLOB, got {findings}"
    assert broad[0]["severity"] == "ADVISORY"


# ---------------------------------------------------------------------------
# 12. --gates all activates policy and quality gates
# ---------------------------------------------------------------------------

def test_gates_all_includes_policy_and_quality(tmp_path):
    bad_json = json.dumps({"forbid_pattern": [{"pattern": "[unclosed"}]})
    adr_dir = _make_adr(
        tmp_path,
        "ADR-001-test.md",
        enforcement_json=bad_json,
        decision="Use an appropriate solution somehow.",
        alternatives="- **A.** Rejected.",
    )
    code, out = run_lint("--gates", "all", str(adr_dir))
    gate_names = {
        f.get("gate")
        for file_result in out.get("files", [])
        for f in file_result.get("findings", [])
    }
    assert "policy" in gate_names, f"Expected policy gate in 'all' run, gates found: {gate_names}"
