"""Index freshness where it actually rots (TASK-83, spec R7).

Every `bin/adr` subcommand regenerates README.md, ADR-INDEX.md and
ADR-INDEX.json inside the same rollback-able transaction as the ADR write, so
anything that goes through the lifecycle CLI keeps them true. That guarantee
stops at the CLI. An ADR edited by hand -- or written straight to disk by a
coding agent with a Write tool, which is the common case in a harness -- leaves
all three stale, and the index is what every other tool and every agent reads
first.

Three places now notice, each with the strength it can honestly claim:

* the guardian at SessionStart, in-process because `check` may never spawn, and
  advisory because a nudge is all a session start should be;
* the commit hook, which warns rather than blocks: it reads the worktree while
  the commit is the staged snapshot, so on a partial commit a block there would
  refuse correct work;
* CI, which checks out the commit itself and therefore blocks.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_GUARDIAN = REPO_ROOT / "bin" / "adr-guardian"
ADR_INDEX = REPO_ROOT / "bin" / "adr-index"


def _core():
    name = "adr_index_core"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "bin" / f"{name}.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


core = _core()


def _seeded_dir(tmp_path: Path) -> Path:
    """A small ADR set with its indexes freshly generated."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for num in (1, 2):
        (adr_dir / f"ADR-{num:03d}-decision-{num}.md").write_text(
            f"""---
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

Some context pointing at bin/adr-index.

## Decision

Do thing {num}.

## Alternatives Considered

- Do nothing: rejected.
- This: accepted.

## Consequences

**Positive:**
- Benefit.

**Negative:**
- Cost.

## Related Decisions

- None.

## References

- bin/adr-index
""",
            encoding="utf-8",
        )
    subprocess.run(
        [sys.executable, str(ADR_INDEX), str(adr_dir)],
        capture_output=True, text=True, check=True,
    )
    return adr_dir


def _touch_future(adr_dir: Path, name: str) -> None:
    """Make one file newer than everything else, deterministically."""
    later = time.time() + 60
    os.utime(adr_dir / name, (later, later))


# ---------------------------------------------------------------------------
# The generator's own answer
# ---------------------------------------------------------------------------

def test_a_freshly_generated_index_is_not_stale(tmp_path):
    adr_dir = _seeded_dir(tmp_path)

    assert core.stale_index_artifacts(adr_dir) == []


def test_an_edited_adr_makes_the_index_stale(tmp_path):
    adr_dir = _seeded_dir(tmp_path)
    path = adr_dir / "ADR-001-decision-1.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Do thing 1.", "Do something else."),
        encoding="utf-8",
    )

    stale = core.stale_index_artifacts(adr_dir)

    assert stale, "an edited Decision must change what the generator would write"


def test_a_missing_artifact_counts_as_stale(tmp_path):
    adr_dir = _seeded_dir(tmp_path)
    (adr_dir / "ADR-INDEX.json").unlink()

    assert "ADR-INDEX.json" in core.stale_index_artifacts(adr_dir)


def test_a_directory_with_no_adrs_is_never_reported_stale(tmp_path):
    empty = tmp_path / "docs" / "adr"
    empty.mkdir(parents=True)

    assert core.stale_index_artifacts(empty) == []
    assert core.index_probably_fresh(empty) is True


# ---------------------------------------------------------------------------
# The mtime precondition: a skip, not a proof
# ---------------------------------------------------------------------------

def test_the_mtime_probe_says_fresh_right_after_generation(tmp_path):
    adr_dir = _seeded_dir(tmp_path)

    assert core.index_probably_fresh(adr_dir) is True


def test_the_mtime_probe_says_not_fresh_when_an_adr_is_newer(tmp_path):
    adr_dir = _seeded_dir(tmp_path)
    _touch_future(adr_dir, "ADR-001-decision-1.md")

    assert core.index_probably_fresh(adr_dir) is False


def test_the_mtime_probe_is_not_proof_of_freshness(tmp_path):
    """Documented limitation, pinned so nobody promotes it to a certificate."""
    adr_dir = _seeded_dir(tmp_path)
    index = adr_dir / "ADR-INDEX.md"
    index.write_text(index.read_text(encoding="utf-8") + "\n| bogus | row |\n",
                     encoding="utf-8")
    _touch_future(adr_dir, "ADR-INDEX.md")
    _touch_future(adr_dir, "README.md")
    _touch_future(adr_dir, "ADR-INDEX.json")

    assert core.index_probably_fresh(adr_dir) is True      # the probe is fooled
    assert "ADR-INDEX.md" in core.stale_index_artifacts(adr_dir)  # the real check is not


# ---------------------------------------------------------------------------
# The guardian nudge
# ---------------------------------------------------------------------------

def _guardian_check(cwd: Path):
    return subprocess.run(
        [sys.executable, str(ADR_GUARDIAN), "check"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )


def test_the_guardian_nudges_about_a_stale_index(tmp_path):
    adr_dir = _seeded_dir(tmp_path)
    path = adr_dir / "ADR-001-decision-1.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Do thing 1.", "Do something else."),
        encoding="utf-8",
    )
    _touch_future(adr_dir, "ADR-001-decision-1.md")

    result = _guardian_check(tmp_path)

    assert result.returncode == 0
    assert "index:" in result.stdout
    assert "bin/adr-index" in result.stdout


def test_the_guardian_says_nothing_about_a_fresh_index(tmp_path):
    adr_dir = _seeded_dir(tmp_path)

    result = _guardian_check(tmp_path)

    assert result.returncode == 0
    assert "index:" not in result.stdout
    assert core.stale_index_artifacts(adr_dir) == []


def test_the_guardian_still_exits_zero_when_the_generator_cannot_run(tmp_path):
    """A tool that cannot check must not pretend it did, nor block the session."""
    adr_dir = _seeded_dir(tmp_path)
    (adr_dir / "ADR-001-decision-1.md").write_text(
        "---\nnot: [valid\n---\nbroken", encoding="utf-8"
    )
    _touch_future(adr_dir, "ADR-001-decision-1.md")

    result = _guardian_check(tmp_path)

    assert result.returncode == 0


# ---------------------------------------------------------------------------
# The shipped CI gate
# ---------------------------------------------------------------------------

def test_the_downstream_ci_template_and_its_action_both_ship():
    """AC#4: a downstream project gets this check in its own CI, not just ours."""
    template = REPO_ROOT / "templates" / "github-workflows" / "adr-index-check.yml"
    action = REPO_ROOT / ".github" / "actions" / "adr-index-check" / "action.yml"

    assert template.is_file(), "the copyable workflow is the downstream half"
    assert action.is_file(), "the workflow references an action that must exist"
    assert "adr-index-check@" in template.read_text(encoding="utf-8")
    assert "bin/adr-index" in action.read_text(encoding="utf-8")


def test_the_commit_hook_warns_about_a_stale_index_without_blocking():
    """It reads the worktree, not the staged snapshot; only CI may block."""
    hook = (REPO_ROOT / "templates" / "githooks" / "pre-commit").read_text(
        encoding="utf-8"
    )

    assert "--check" in hook and "adr-index" in hook
    marker = hook.index("_ADR_INDEX=")
    section = hook[marker - 1200: marker + 900]
    assert "WARN" in section
    assert "exit 1" not in section, "the hook must not block on worktree state"
