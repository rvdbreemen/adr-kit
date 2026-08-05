"""Session-start snapshot of the working tree, for tests that assert on it.

This is the suite's only shared fixture module, and it exists for one reason.
`scripts/build-client-adapters.py --check` asserts that the generated `codex/`
and `copilot/` trees are a pure function of the source trees. Pointed at the
live checkout, that assertion is sensitive to every other test in the run: a
neighbouring test that writes a file anywhere under `bin/`, `schemas/`,
`templates/`, `instructions/` or inside a generated root fails the drift check
and names the wrong thing (TASK-128).

Taking one copy at session start gives the check a tree nothing else writes to.

Keep this file single-purpose. A conftest that grows into a fixture dumping
ground would cost more than the flake it fixes.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Excluded at the top level only, each for a stated reason. The generator reads
# none of them, and several are large enough or deep enough to matter on
# Windows, where the snapshot lives under %TEMP% and MAX_PATH is 260.
_DENY_TOP = {
    ".git": "large, and its files are locked while git runs",
    "backlog": "never read by the generator; carries the longest paths in the repo",
    "docs": "never read by the generator",
    "tests": "never read by the generator",
    "C4-Documentation": "never read by the generator",
    "graphify-out": "untracked local artefact cache; deepest paths in the tree",
    ".pytest_cache": "test runner scratch",
    ".mypy_cache": "type checker scratch",
    ".venv": "virtualenv, large and machine-local",
    "node_modules": "large and machine-local",
}

# Excluded at every depth.
_DENY_ANY = {"__pycache__"}

_SNAPSHOT: Path | None = None
_SNAPSHOT_ERROR: BaseException | None = None


def _ignore(directory: str, names: list[str]) -> set[str]:
    """copytree ignore callback.

    Deliberately not shutil.ignore_patterns: that matches basenames at every
    depth, so a pattern like "docs" would also drop a nested docs/ directory
    inside a generated root. A partially-copied tree would make the drift check
    report differences that are artefacts of the copy -- the one failure mode
    most worth designing out here.
    """
    if Path(directory) == ROOT:
        return {name for name in names if name in _DENY_TOP}
    return {name for name in names if name in _DENY_ANY}


def _take_snapshot() -> Path:
    base = Path(tempfile.mkdtemp(prefix="adr-kit-tree-"))
    # copytree needs a destination that does not exist yet, hence the child.
    destination = base / "tree"
    shutil.copytree(ROOT, destination, ignore=_ignore)
    return destination


def pytest_collection_modifyitems(session, config, items) -> None:
    """Take the snapshot once, and only when something selected needs it."""
    global _SNAPSHOT, _SNAPSHOT_ERROR
    if getattr(config.option, "collectonly", False):
        return
    if _SNAPSHOT is not None or _SNAPSHOT_ERROR is not None:
        return
    if not any(item.get_closest_marker("tree_snapshot") for item in items):
        return
    try:
        _SNAPSHOT = _take_snapshot()
    except BaseException as exc:  # noqa: BLE001 -- see below
        # Stashed rather than raised: an exception here aborts collection for
        # the whole session, which would be a worse defect than the flake this
        # fixture exists to fix. The tests that need it fail with this reason.
        _SNAPSHOT_ERROR = exc


def pytest_sessionfinish(session, exitstatus) -> None:
    if _SNAPSHOT is not None:
        # ignore_errors is required on Windows, where a read-only file makes
        # rmtree raise and would fail a session in which every test passed.
        shutil.rmtree(_SNAPSHOT.parent, ignore_errors=True)


@pytest.fixture(scope="session")
def tree_snapshot() -> Path:
    """A copy of the working tree taken before any test ran.

    Never write into it. Tests that need to mutate a tree copy it again into
    their own tmp_path -- mutating the shared snapshot would reintroduce the
    shared-mutable-state problem this fixture removes.
    """
    if _SNAPSHOT_ERROR is not None:
        raise _SNAPSHOT_ERROR
    if _SNAPSHOT is None:
        pytest.fail(
            "tree snapshot was not taken; mark the test with "
            "@pytest.mark.tree_snapshot"
        )
    return _SNAPSHOT
