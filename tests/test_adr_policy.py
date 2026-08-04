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

from tests.adr_fixtures import isolated_copy

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

def test_the_alternatives_count_is_no_longer_a_quality_advisory():
    """It moved to the completeness gate as a FAIL (TASK-112).

    As an advisory under `quality` -- a gate that is not in the default set --
    a record listing one option and nothing weighed against it passed every
    blocking gate. R0 is not a suggestion: a record that states only the outcome
    cannot be re-evaluated later, and a decision that cannot be re-evaluated
    cannot be superseded honestly.
    """
    content = textwrap.dedent("""\
        ## Decision

        We will use PostgreSQL.

        ## Consequences

        50% faster queries.

        ## Alternatives Considered

        - **Do nothing.** Rejected because performance is already degraded.
    """)

    findings = check_quality_gate(content, "ADR-001")

    assert not [f for f in findings if f["code"] == "QUALITY_FEW_ALTERNATIVES"], (
        "the count is enforced by the completeness gate now; keeping an "
        "advisory copy would report the same defect twice"
    )


def _one_option(heading: str) -> str:
    source = sorted((REPO_ROOT / "docs" / "adr").glob("ADR-020-*.md"))[0]
    body = isolated_copy(source.read_text(encoding="utf-8")).replace(
        "## Considered Options", heading
    )
    start = body.index(heading) + len(heading)
    end = body.index("\n## ", start)
    return body[:start] + "\n\n* Only one option, nothing weighed against it.\n" + body[end:]


def _lint(tmp_path: Path, body: str):
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "ADR-020-x.md").write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-lint"), str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


@pytest.mark.parametrize(
    "heading", ["## Alternatives Considered", "## Considered Options"]
)
def test_one_alternative_fails_completeness_on_either_profile(tmp_path, heading):
    """Nygard and MADR spell the heading differently; both must be counted.

    A check written against one spelling silently skips the other, and MADR is
    the default profile for new records.
    """
    result = _lint(tmp_path, _one_option(heading))

    assert result.returncode != 0, result.stdout
    assert "alternative(s) considered" in result.stdout


def test_two_alternatives_pass(tmp_path):
    """Satisfiable by editing the record, per spec R15: name the option that
    lost, and 'do nothing' is always one."""
    body = _one_option("## Considered Options").replace(
        "* Only one option, nothing weighed against it.\n",
        "* Option A.\n* Do nothing.\n",
    )

    assert _lint(tmp_path, body).returncode == 0


def test_this_repositorys_records_all_weigh_at_least_two_options():
    """Promoting a gate while the project's own set would fail it is how a gate
    gets reverted. Measured before promotion: 28 of 28 pass."""
    import importlib.machinery
    import importlib.util

    name = "adr_lint_alternatives_probe"
    cached = sys.modules.get(name)
    if cached is None:
        loader = importlib.machinery.SourceFileLoader(
            name, str(REPO_ROOT / "bin" / "adr-lint")
        )
        spec = importlib.util.spec_from_loader(name, loader)
        cached = importlib.util.module_from_spec(spec)
        sys.modules[name] = cached
        loader.exec_module(cached)

    short = [
        (path.name, count)
        for path in sorted((REPO_ROOT / "docs" / "adr").glob("ADR-[0-9]*.md"))
        for count in [cached.count_alternatives(path.read_text(encoding="utf-8"))]
        if count is not None and count < 2
    ]

    assert not short, short


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


def test_a_migration_placeholder_is_not_counted_as_zero(tmp_path):
    """`/adr-kit:migrate` writes a TODO comment when the source had none.

    It deliberately never fabricates alternatives. Counting an HTML-comment
    placeholder as zero would turn every honest import into a blocking failure
    and push a migrating team to disable the gate -- the outcome spec R15 exists
    to prevent. The placeholder already tells the author what to do.
    """
    body = _one_option("## Considered Options").replace(
        "* Only one option, nothing weighed against it.\n",
        "<!-- TODO: document at least 2 alternatives that were considered and "
        "rejected, with reasoning. -->\n",
    )

    result = _lint(tmp_path, body)

    assert result.returncode == 0, result.stdout
    assert "alternative(s) considered" not in result.stdout


@pytest.mark.parametrize(
    "placeholder",
    [
        pytest.param(
            "<!-- TODO: document at least 2 alternatives that were considered "
            "and rejected, with reasoning. -->\n",
            id="skill-html-comment",
        ),
        pytest.param("- TODO: record the considered options.\n", id="cli-list-item"),
    ],
)
def test_neither_migration_placeholder_spelling_counts_as_an_option(
    tmp_path, placeholder
):
    """Two writers, two spellings, one meaning: unknown, fill this in.

    `/adr-kit:migrate`'s skill emits an HTML comment; `bin/adr-migrate` emits a
    `- TODO:` list item. Missing either means an honest import fails a blocking
    gate on arrival, which is how a migrating team learns to disable the gate.
    """
    body = _one_option("## Considered Options").replace(
        "* Only one option, nothing weighed against it.\n", placeholder
    )

    result = _lint(tmp_path, body)

    assert result.returncode == 0, result.stdout
    assert "alternative(s) considered" not in result.stdout


def test_a_real_option_beside_a_placeholder_still_counts_as_one(tmp_path):
    """Half-filled is still incomplete, and must not pass by accident."""
    body = _one_option("## Considered Options").replace(
        "* Only one option, nothing weighed against it.\n",
        "* A real option that was weighed.\n- TODO: record the rest.\n",
    )

    result = _lint(tmp_path, body)

    assert result.returncode != 0
    assert "1 alternative(s) considered" in result.stdout


# ---------------------------------------------------------------------------
# Retrieval metadata: an Accepted ADR nobody can find (TASK-118)
# ---------------------------------------------------------------------------

def _strip_retrieval_metadata(text: str) -> str:
    import re

    for key in ("topics", "aliases", "components", "symbols"):
        text = re.sub(rf"^{key}:\n(?:  - .*\n)+", f"{key}: []\n", text, flags=re.M)
    return text


def test_an_accepted_adr_with_no_retrieval_metadata_is_reported(tmp_path):
    """`binding: true` used to be a precondition, and it made this inert.

    Measured on this repository: all 12 records carrying no retrieval metadata
    escaped through that single condition, every one of them `binding: false` --
    ADR-004 among them, so a query about context injection did not return the
    decision that defines context injection. Being non-binding means a decision
    does not gate code; it does not mean it should be invisible.
    """
    import json

    source = sorted((REPO_ROOT / "docs" / "adr").glob("ADR-004-*.md"))[0]
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / source.name).write_text(
        _strip_retrieval_metadata(source.read_text(encoding="utf-8")), encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    codes = [
        f["code"]
        for entry in json.loads(result.stdout)["files"]
        for f in entry["findings"]
        if f.get("code")
    ]

    assert "SELECTIVE_CONTEXT_METADATA" in codes, result.stdout


def test_the_finding_runs_in_the_default_gate_set():
    """It was emitted under `policy`, which is not in DEFAULT_GATES.

    An advisory in a gate nobody runs is not an advisory; it is silence.
    """
    source = (REPO_ROOT / "bin" / "adr-lint").read_text(encoding="utf-8")

    assert "completeness" in DEFAULT_GATES
    assert '"gate": "completeness",\n        "level": "FAIL" if mode == "strict"' in source


def test_populated_metadata_produces_no_finding(tmp_path):
    """The shipped ADR-004, as annotated, must be quiet."""
    import json

    source = sorted((REPO_ROOT / "docs" / "adr").glob("ADR-004-*.md"))[0]
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / source.name).write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    codes = [
        f["code"]
        for entry in json.loads(result.stdout)["files"]
        for f in entry["findings"]
        if f.get("code")
    ]

    assert "SELECTIVE_CONTEXT_METADATA" not in codes


def test_a_global_scope_record_is_exempt(tmp_path):
    """`context_scope: global` is injected regardless of the query, so a
    retrieval miss cannot happen to it."""
    import json

    source = sorted((REPO_ROOT / "docs" / "adr").glob("ADR-004-*.md"))[0]
    text = _strip_retrieval_metadata(source.read_text(encoding="utf-8"))
    text = text.replace("context_scope: null", 'context_scope: "global"')
    if 'context_scope: "global"' not in text:
        text = text.replace("superseded_by: null", 'superseded_by: null\ncontext_scope: "global"')
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / source.name).write_text(text, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ADR_LINT), "--format", "json", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    codes = [
        f["code"]
        for entry in json.loads(result.stdout)["files"]
        for f in entry["findings"]
        if f.get("code")
    ]

    assert "SELECTIVE_CONTEXT_METADATA" not in codes


def test_adr_new_names_the_metadata_it_cannot_fill_in(tmp_path):
    """The tool cannot invent topics, so it says so while the author is there.

    Same shape as the signer proposal: propose, never assume.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr"), "new", "A Decision",
         "--adr-dir", str(adr_dir), "--changed-by", "User: Test Signer"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    assert result.returncode == 0, result.stderr
    assert "retrieval metadata" in result.stderr
    assert "topics" in result.stderr and "components" in result.stderr
    assert "defines" in result.stderr, (
        "the components rule is the part authors get wrong"
    )
