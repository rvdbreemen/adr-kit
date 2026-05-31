"""Tests for bin/adr-judge-precommit — the pre-commit framework wrapper.

Strategy: create a real git repository in tmp_path, write an ADR with an
Enforcement block, stage a violating file, and invoke the wrapper as a
subprocess.  Assert exit 1 on violation and exit 0 on a clean staging area.

These tests do NOT require the pre-commit CLI to be installed.  They smoke-
test the wrapper's git-diff-to-adr-judge pipe directly.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WRAPPER = REPO_ROOT / "bin" / "adr-judge-precommit"

# A minimal Accepted ADR that forbids the word "Foo" in src/**/*.py files.
CANONICAL_ADR = """\
# ADR-001 No Foo

## Status

Accepted, 2026-04-25.

## Context

Foo fragments the heap and is banned project-wide.

## Decision

Do not use Foo anywhere in src/.

## Alternatives Considered

- Use Foo: rejected (heap fragmentation).
- Use Bar: accepted.

## Consequences

**Positive:**
- Stable heap.

**Negative:**
- Cannot use Foo.

## Related Decisions

- None.

## References

- Internal benchmark results.

## Enforcement

```json
{
  "forbid_pattern": [
    {"pattern": "\\\\bFoo\\\\b", "path_glob": "src/**/*.py", "message": "No Foo allowed (ADR-001)."}
  ]
}
```
"""


def _init_git_repo(path: Path) -> None:
    """Create a minimal git repository at path."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    # Set identity so git commands don't fail in CI environments.
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True, capture_output=True, cwd=str(path),
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True, capture_output=True, cwd=str(path),
    )


def _make_project(tmp_path: Path) -> Path:
    """Create a git repo with the ADR; return the repo root path."""
    _init_git_repo(tmp_path)
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-no-foo.md").write_text(
        textwrap.dedent(CANONICAL_ADR), encoding="utf-8"
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    return tmp_path


def _run_wrapper(repo_root: Path) -> subprocess.CompletedProcess:
    """Invoke the wrapper script in the context of the git repo."""
    result = subprocess.run(
        [sys.executable, str(WRAPPER)],
        cwd=str(repo_root),
        capture_output=True,
    )
    # Decode with errors="replace" so Windows ANSI / non-UTF-8 bytes don't
    # cause UnicodeDecodeError in test output.
    result.stdout = result.stdout.decode("utf-8", errors="replace")
    result.stderr = result.stderr.decode("utf-8", errors="replace")
    return result


def test_wrapper_exit_1_on_violation(tmp_path):
    """Staging a file that violates an ADR Enforcement rule exits 1."""
    repo = _make_project(tmp_path)

    # Write and stage a violating Python file.
    violating = repo / "src" / "bad.py"
    violating.write_text("def bad():\n    return Foo()\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/bad.py"], check=True, capture_output=True, cwd=str(repo))

    result = _run_wrapper(repo)
    assert result.returncode == 1, (
        f"Expected exit 1 (violation), got {result.returncode}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_wrapper_exit_0_on_clean_staging(tmp_path):
    """Staging a file with no Enforcement violation exits 0."""
    repo = _make_project(tmp_path)

    # Write and stage a clean Python file.
    clean_file = repo / "src" / "clean.py"
    clean_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/clean.py"], check=True, capture_output=True, cwd=str(repo))

    result = _run_wrapper(repo)
    assert result.returncode == 0, (
        f"Expected exit 0 (no violation), got {result.returncode}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_wrapper_exit_0_on_empty_staging_area(tmp_path):
    """With nothing staged the diff is empty — adr-judge exits 0."""
    repo = _make_project(tmp_path)
    # Nothing staged.
    result = _run_wrapper(repo)
    assert result.returncode == 0, (
        f"Expected exit 0 (empty diff), got {result.returncode}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_wrapper_resolves_adr_judge_sibling():
    """The wrapper resolves bin/adr-judge relative to its own __file__ path.

    We verify this statically: the sibling path computed by the wrapper must
    point at an existing file.  This confirms the wrapper does not rely on
    PATH and will work regardless of cwd or the consumer's environment.
    """
    # The wrapper sets: _ADR_JUDGE = Path(__file__).resolve().parent / "adr-judge"
    # Replicate that logic here and assert the target exists.
    adr_judge_sibling = WRAPPER.parent / "adr-judge"
    assert adr_judge_sibling.exists(), (
        f"bin/adr-judge not found at expected sibling path: {adr_judge_sibling}\n"
        "The wrapper's sibling-resolution will fail at runtime."
    )
