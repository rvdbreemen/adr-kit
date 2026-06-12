"""Tests for bin/bump-version (Python rewrite, post-v0.30.0).

Background: bump-version was a bash script that shelled out to python3 per
file edit. On Windows the `python3` Store alias routes through the Python
Install Manager, which scans argv for a script file and dispatches on ITS
shebang; passing the bash-shebanged pre-commit template as an argument made
the launcher exec bash instead of python (observed as cygheap fork crashes
during releases v0.27.0 through v0.29.0). The rewrite is pure stdlib Python:
no child processes at all, so there is nothing for a launcher to misroute.

The script resolves all paths relative to its own location, so the tests
copy it into a temp fixture tree and run the copy: the real repo is never
mutated.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUMP_VERSION = REPO_ROOT / "bin" / "bump-version"

PLUGIN = {"name": "adr-kit", "version": "0.30.0", "description": "x"}
MARKETPLACE = {"plugins": [{"name": "adr-kit", "version": "0.30.0"}]}
CHANGELOG = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- thing.\n\n"
    "## [0.30.0] - 2026-06-12\n"
)
PRECOMMIT = (
    "#!/usr/bin/env bash\n"
    "# adr-kit pre-commit hook\n"
    'ADR_KIT_WRAPPER_VERSION="0.30.0"\n'
    "exit 0\n"
)
GUARDIAN_ENTRY = {
    "_remove_marker": "adr-guardian-session-start",
    "_wrapper_version": "0.30.0",
    "type": "command",
    "command": "adr-guardian check",
}


def _make_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "bin").mkdir(parents=True)
    (root / ".claude-plugin").mkdir()
    (root / "templates" / "githooks").mkdir(parents=True)
    (root / "templates" / "cc-settings").mkdir(parents=True)
    shutil.copy(str(BUMP_VERSION), str(root / "bin" / "bump-version"))
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(PLUGIN, indent=2) + "\n", encoding="utf-8"
    )
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(MARKETPLACE, indent=2) + "\n", encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    (root / "templates" / "githooks" / "pre-commit").write_text(
        PRECOMMIT, encoding="utf-8"
    )
    (root / "templates" / "cc-settings" / "guardian-hook-entry.json").write_text(
        json.dumps(GUARDIAN_ENTRY, indent=2) + "\n", encoding="utf-8"
    )
    return root


def _run(root: Path, *args: str) -> "subprocess.CompletedProcess":
    return subprocess.run(
        [sys.executable, str(root / "bin" / "bump-version")] + list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(root),
    )


def test_bump_updates_all_five_files(tmp_path):
    root = _make_tree(tmp_path)
    proc = _run(root, "0.31.0")
    assert proc.returncode == 0, proc.stderr
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.31.0"
    marketplace = json.loads(
        (root / ".claude-plugin" / "marketplace.json").read_text()
    )
    assert marketplace["plugins"][0]["version"] == "0.31.0"
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]\n\n## [0.31.0] - " in changelog
    assert "## [0.30.0] - 2026-06-12" in changelog
    precommit = (root / "templates" / "githooks" / "pre-commit").read_text()
    assert 'ADR_KIT_WRAPPER_VERSION="0.31.0"' in precommit
    entry = json.loads(
        (root / "templates" / "cc-settings" / "guardian-hook-entry.json").read_text()
    )
    assert entry["_wrapper_version"] == "0.31.0"


def test_invalid_semver_rejected(tmp_path):
    root = _make_tree(tmp_path)
    for bad in ("0.31", "v0.31.0", "0.31.0-rc1", "banana"):
        proc = _run(root, bad)
        assert proc.returncode == 1, bad
        assert "semver" in proc.stderr


def test_usage_error_without_argument(tmp_path):
    root = _make_tree(tmp_path)
    proc = _run(root)
    assert proc.returncode == 1
    assert "Usage" in proc.stderr


def test_missing_marketplace_entry_fails(tmp_path):
    root = _make_tree(tmp_path)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "other", "version": "1.0.0"}]}),
        encoding="utf-8",
    )
    proc = _run(root, "0.31.0")
    assert proc.returncode == 1
    assert "marketplace" in proc.stderr


def test_missing_unreleased_warns_but_succeeds(tmp_path):
    root = _make_tree(tmp_path)
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.30.0] - 2026-06-12\n", encoding="utf-8"
    )
    proc = _run(root, "0.31.0")
    assert proc.returncode == 0
    assert "WARNING" in proc.stderr
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.31.0"


def test_missing_stamps_tolerated(tmp_path):
    root = _make_tree(tmp_path)
    (root / "templates" / "githooks" / "pre-commit").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )
    (root / "templates" / "cc-settings" / "guardian-hook-entry.json").write_text(
        "{not json", encoding="utf-8"
    )
    proc = _run(root, "0.31.0")
    assert proc.returncode == 0, proc.stderr
    assert "wrapper stamp" not in proc.stdout
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.31.0"


def test_no_child_processes_in_source():
    """The launcher-misrouting bug class is structurally excluded: the script
    must not spawn any child process."""
    source = BUMP_VERSION.read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "os.system" not in source


def test_real_script_is_python():
    first_line = BUMP_VERSION.read_text(encoding="utf-8").splitlines()[0]
    assert "python" in first_line
