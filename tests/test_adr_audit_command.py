"""bin/adr-audit: lint the decisions and judge the code in one run (TASK-84, R15).

Either answer alone is misleading. A clean judge over vague ADRs proves nothing
because a vague rule cannot be violated; a sharp ADR set nobody checks the code
against is documentation rather than governance. The combination already
existed inside the guardian's cheap tier, on a cadence nobody asked for and
against a fixed `HEAD~5..HEAD` window. This is the on-demand form.

The two properties worth pinning:

* **whole-codebase mode really does reach untouched code.** A rule added after a
  file was written has never been applied to that file, and never will be by a
  gate that only sees diffs. Mechanically it is a diff against the empty tree,
  so every line reads as added -- and this file proves a forbid rule fires on a
  file no recent commit touched, which is the only evidence that matters;
* **the exit codes stay separable.** "Your ADRs are not good enough" and "your
  code violates an ADR" have different owners. One conflated non-zero tells the
  caller nothing about what to go and fix.
"""

# Gate anchor for ADR-026: adr-audit-exit-contract-v1
# Verified here: the combined audit command and its five-way exit contract.
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# Imported as a top-level module, not as `tests.adr_fixtures`. pytest's
# prepend import mode puts this file's own directory on sys.path, so the bare
# name always resolves. The dotted form does not: `tests/` has no
# `__init__.py`, so it is a namespace package, and any installed distribution
# shipping a real top-level `tests` package shadows it -- a regular package
# always beats a namespace portion. That makes the dotted form resolve or fail
# depending on what else is installed on the machine, which is why it is
# banned outright. tests/test_import_convention.py enforces this.
from adr_fixtures import isolated_copy

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_AUDIT = REPO_ROOT / "bin" / "adr-audit"

EXIT_OK = 0
EXIT_CODE_VIOLATION = 1
EXIT_TOOLING = 2
EXIT_ADR_QUALITY = 3
EXIT_BOTH = 4


def _adr(num: int, *, thin: bool = False, enforcement: str = "",
         related: str = "") -> str:
    """A complete ADR by default; `thin` fails its own gates on purpose."""
    body_tail = "" if thin else textwrap.dedent("""\

        **Negative:**
        - Some cost, stated plainly.
        """)
    block = f"\n\n## Enforcement\n\n```json\n{enforcement}\n```\n" if enforcement else ""
    text = textwrap.dedent(f"""\
        ---
        id: "ADR-{num:03d}"
        title: "Decision {num}"
        status: "Accepted"
        date: "2026-05-01"
        binding: false
        gate: null
        documents_shipped: false
        verified_in: []
        supersedes: []
        superseded_by: null
        ---

        # ADR-{num:03d} Decision {num}

        ## Status

        Accepted, 2026-05-01.

        ## Context

        Concrete context that points at src/app.py as the affected code path.

        ## Decision

        Do thing {num} in src/app.py.

        ## Alternatives Considered

        - Do nothing: rejected, it leaves the problem in place.
        - Do it elsewhere: rejected, the module boundary is wrong.

        ## Consequences

        **Positive:**
        - A concrete benefit.
        """) + body_tail + textwrap.dedent("""
        ## Related Decisions

        - None.

        ## References

        - src/app.py
        """) + block
    # Inserted AFTER dedent, never interpolated into it: a multi-line value
    # whose own lines carry no common indent collapses dedent's prefix to
    # nothing and leaves the entire ADR indented, which every tool then reads
    # as an unknown format with an unknown status.
    if related:
        text = text.replace(
            "superseded_by: null\n",
            'superseded_by: null\nrelated:\n  - "%s"\n' % related,
            1,
        )
    return text


def _repo(tmp_path: Path, *, source: str = "print('hello')\n") -> Path:
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text(source, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True,
                   capture_output=True)
    return root


def _commit(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t",
         "commit", "-qm", "seed"],
        cwd=root, check=True, capture_output=True,
    )


def _audit(root: Path, *args: str, stdin_text: str | None = None):
    result = subprocess.run(
        [sys.executable, str(ADR_AUDIT), "--repo-root", str(root),
         "--adr-dir", "docs/adr", "--format", "json", *args],
        cwd=str(root), input=stdin_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    payload = None
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, ValueError):
            payload = None
    return result.returncode, payload, result


FORBID_PRINT = json.dumps(
    {
        "forbid_pattern": [
            {
                "pattern": r"\bprint\(",
                "path_glob": "src/**/*.py",
                "message": "ADR-001: no print in src.",
            }
        ]
    },
    indent=2,
)


# ---------------------------------------------------------------------------
# The clean case
# ---------------------------------------------------------------------------

def test_a_healthy_project_is_on_course(tmp_path):
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)

    code, payload, result = _audit(root, "--whole-codebase")

    assert code == EXIT_OK, result.stdout + result.stderr
    assert payload["decisions"]["clean"] is True
    assert payload["code"]["clean"] is True
    assert payload["verdict"] == "on course"


# ---------------------------------------------------------------------------
# The property that justifies whole-codebase mode
# ---------------------------------------------------------------------------

def test_whole_codebase_mode_reaches_a_file_no_recent_diff_touched(tmp_path):
    """The rule arrives after the code. A diff-only gate would never see this."""
    root = _repo(tmp_path, source="print('written long before the rule')\n")
    _commit(root)  # the offending file is now history, not a change

    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)

    # A diff of the most recent commit touches only the ADR, so it is clean...
    recent = subprocess.run(
        ["git", "diff", "--unified=0", "HEAD~1", "HEAD"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
    ).stdout
    diff_code, _diff_payload, _ = _audit(root, "--diff", "-", stdin_text=recent)
    assert diff_code == EXIT_OK

    # ... and the whole codebase is not.
    code, payload, result = _audit(root, "--whole-codebase")

    assert code == EXIT_CODE_VIOLATION, result.stdout + result.stderr
    violations = payload["code"]["violations"]
    assert any("src/app.py" in (v.get("path") or "") for v in violations)


def test_whole_codebase_mode_sees_the_working_tree_not_only_head(tmp_path):
    """A local run answers about the code in front of the person asking."""
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)
    (root / "src" / "app.py").write_text("print('uncommitted')\n", encoding="utf-8")

    code, _payload, result = _audit(root, "--whole-codebase")

    assert code == EXIT_CODE_VIOLATION, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# The exit codes stay separable
# ---------------------------------------------------------------------------

def test_a_failing_adr_set_exits_three_not_one(tmp_path):
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, related="ADR-042"), encoding="utf-8"
    )
    _commit(root)

    code, payload, result = _audit(root, "--whole-codebase")

    assert code == EXIT_ADR_QUALITY, result.stdout + result.stderr
    assert payload["decisions"]["clean"] is False
    assert payload["code"]["clean"] is True
    assert "ADR-042" in json.dumps(payload["decisions"]["failures"])


def test_both_failures_exit_four_and_are_reported_separately(tmp_path):
    root = _repo(tmp_path, source="print('bad')\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT, related="ADR-042"), encoding="utf-8"
    )
    _commit(root)

    code, payload, result = _audit(root, "--whole-codebase")

    assert code == EXIT_BOTH, result.stdout + result.stderr
    assert payload["decisions"]["clean"] is False
    assert payload["code"]["clean"] is False


def test_a_tooling_failure_exits_two_rather_than_reporting_clean(tmp_path):
    """Could not answer is never the same as answering no."""
    root = tmp_path / "not-a-repo"
    root.mkdir()

    result = subprocess.run(
        [sys.executable, str(ADR_AUDIT), "--repo-root", str(root),
         "--adr-dir", "docs/adr", "--whole-codebase"],
        cwd=str(root), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )

    assert result.returncode == EXIT_TOOLING
    assert "adr-audit:" in result.stderr
    assert "on course" not in result.stdout


# ---------------------------------------------------------------------------
# Usable from a hook and from CI without a second wrapper
# ---------------------------------------------------------------------------

def test_diff_mode_reads_a_piped_diff(tmp_path):
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)
    (root / "src" / "app.py").write_text("print('staged')\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--unified=0"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
    ).stdout

    code, payload, result = _audit(
        root, "--diff", "-", "--snapshot", "staged", stdin_text=staged
    )

    assert code == EXIT_CODE_VIOLATION, result.stdout + result.stderr
    assert payload["mode"] == "diff"


def test_an_empty_diff_is_clean_rather_than_an_error(tmp_path):
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)

    code, payload, _result = _audit(root, "--diff", "-", stdin_text="")

    assert code == EXIT_OK
    assert payload["code"]["empty"] is True


def test_whole_codebase_mode_passes_the_ci_sized_budget(tmp_path):
    """A repository-wide diff is large by construction; failing closed on size
    would make the mode useless exactly where it is most needed."""
    source = ADR_AUDIT.read_text(encoding="utf-8")

    assert "WHOLE_CODEBASE_DIFF_BUDGET = 33_554_432" in source
    assert "--max-diff-bytes" in source


# ---------------------------------------------------------------------------
# The naming collision is resolved, not documented around
# ---------------------------------------------------------------------------

def test_the_init_scanner_is_named_for_what_it_does():
    discover = REPO_ROOT / "bin" / "adr-discover"
    audit = REPO_ROOT / "bin" / "adr-audit"

    assert discover.is_file(), "the init scanner moved to bin/adr-discover"
    assert audit.is_file(), "bin/adr-audit is now the lint-plus-judge command"
    assert "candidate scanner" in discover.read_text(encoding="utf-8")[:600]
    assert "adr-lint" in audit.read_text(encoding="utf-8")


@pytest.mark.parametrize("client", ["codex", "copilot"])
def test_the_audit_workflow_reaches_every_client(client):
    """AC#5: usable from CI and a hook without a second wrapper, on any client."""
    assert (REPO_ROOT / client / "skills" / "audit" / "SKILL.md").is_file()
    assert (REPO_ROOT / client / "bin" / "adr-audit").is_file()


def test_a_bare_invocation_refuses_instead_of_reporting_on_course(tmp_path):
    """The rename hazard, made loud.

    Defaulting to stdin is the one shape that can answer wrongly in silence.
    With stdin closed -- a CI step, a cron job, or a script that still calls
    `bin/adr-audit` meaning the old discovery scanner -- the diff reads empty,
    nothing is judged, and the command would print "on course" and exit 0. A
    tool that cannot check must not pretend it did.
    """
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)

    result = subprocess.run(
        [sys.executable, str(ADR_AUDIT), "--repo-root", str(root),
         "--adr-dir", "docs/adr"],
        cwd=str(root), input="", capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )

    assert result.returncode == EXIT_TOOLING
    assert "on course" not in result.stdout
    assert "name a scope" in result.stderr
    # And it points a stranded caller at the command they actually wanted.
    assert "bin/adr-discover" in result.stderr


def test_an_explicit_empty_diff_is_still_clean(tmp_path):
    """`--diff -` with nothing staged is a real answer, not a missing scope."""
    root = _repo(tmp_path, source="import sys\n")
    (root / "docs" / "adr" / "ADR-001-decision-1.md").write_text(
        _adr(1, enforcement=FORBID_PRINT), encoding="utf-8"
    )
    _commit(root)

    code, payload, _result = _audit(root, "--diff", "-", stdin_text="")

    assert code == EXIT_OK
    assert payload["code"]["empty"] is True


# ---------------------------------------------------------------------------
# The audit runs the gate set it claims to run (TASK-111)
# ---------------------------------------------------------------------------

def test_the_gate_selector_reaches_adr_lint(tmp_path):
    """`--gates` was unreachable, and that hid four failures.

    `run_lint` built a fixed argv and never passed `--gates`; `parse_gates` had
    exactly one call site, the command line. `--strict` does not close the gap,
    because it adds `schema` only. Measured on this repository before the fix:
    the default set reported 0 failures over a set that `--gates all` reported
    4 failures on, so the command that exists to ask "are these records sharp
    enough to be violated?" could not ask it.
    """
    import re

    source = (REPO_ROOT / "bin" / "adr-audit").read_text(encoding="utf-8")

    assert '"--gates"' in source, "the audit exposes no gate selector"
    assert re.search(r"run_lint\([^)]*args\.gates", source), (
        "the selector is parsed but never reaches run_lint"
    )


def test_a_vague_record_fails_only_when_the_gates_are_asked_for(tmp_path):
    """The two answers must differ, or the selector is decoration.

    Three unexpanded acronyms in prose are a clarity failure. The default gate
    set must not report it -- that is the authoring/merge split ADR-009 draws --
    and `--gates all` must.
    """
    import shutil
    import subprocess
    import sys

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    source = sorted((REPO_ROOT / "docs" / "adr").glob("ADR-036-*.md"))[0]
    body = isolated_copy(source.read_text(encoding="utf-8")).replace(
        "## Decision Drivers",
        "## Decision Drivers\n\n"
        "* The OTGW firmware talks to the HVAC unit over the MQTT bridge.\n",
    )
    (adr_dir / "ADR-036-vague.md").write_text(body, encoding="utf-8")

    def lint(*extra):
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "bin" / "adr-lint"), *extra, str(adr_dir)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).returncode

    assert lint() == 0, "the default set must stay structural"
    assert lint("--gates", "clarity") != 0, "the clarity gate must see it"


def test_this_repositorys_own_records_pass_every_gate():
    """The kit's ADR set has to survive the gates the kit ships.

    Before this task it did not: four records failed `clarity`. The repair was
    not to edit them -- three of the four flagged terms were `LLM`, the product's
    own core vocabulary, and fragments of filenames such as `SKILL.md`. Editing
    an Accepted Decision to satisfy a heuristic is exactly what spec R15 forbids,
    so the heuristic was bounded instead.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-lint"),
         "--gates", "all", str(REPO_ROOT / "docs" / "adr")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    assert result.returncode == 0, result.stdout[-2000:]


def test_health_subcommands_dispatch_to_the_family(tmp_path):
    """`adr-audit status|quality|readiness|doctor` reach the siblings.

    One entry point for everything on demand (TASK-147): the sibling keeps
    its own argument surface and exit-code contract, so this asserts the
    dispatch and the passthrough, not the sibling's behaviour.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-audit"), "status",
         "--adr-dir", str(REPO_ROOT / "docs" / "adr"), "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr[:400]
    payload = json.loads(result.stdout)
    assert payload["summary"]["total"] > 0

    unknown = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-audit"), "status",
         "--no-such-flag"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert unknown.returncode == 2, "the sibling's own parser answers"
