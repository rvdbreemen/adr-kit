"""Release packaging contracts for manual and prepared installations."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent


def _direct_entrypoints() -> list[str]:
    paths = [
        "hooks/run-hook.cmd",
        "codex/hooks/run-hook.cmd",
        ".githooks/pre-commit",
        "templates/githooks/pre-commit",
    ]
    for prefix in ("bin", "codex/bin", "copilot/bin"):
        paths.extend(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / prefix).iterdir()
            if path.is_file() and path.suffix != ".py"
        )
    return sorted(set(paths))


def _require_commit_bound_entrypoints() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--", *_direct_entrypoints()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.splitlines()
    if set(tracked) != set(_direct_entrypoints()):
        pytest.skip("direct-entrypoint index contract requires a committed candidate")


def test_git_index_records_every_direct_entrypoint_as_executable():
    _require_commit_bound_entrypoints()
    result = subprocess.run(
        ["git", "ls-files", "--stage", "--", *_direct_entrypoints()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    modes = {
        line.split(maxsplit=3)[3]: line.split(maxsplit=1)[0]
        for line in result.stdout.splitlines()
    }
    assert set(modes) == set(_direct_entrypoints())
    assert {path: mode for path, mode in modes.items() if mode != "100755"} == {}


def test_git_archive_preserves_manual_install_modes(tmp_path):
    _require_commit_bound_entrypoints()
    tree = subprocess.run(
        ["git", "write-tree"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    archive = tmp_path / "adr-kit.tar"
    subprocess.run(
        ["git", "archive", "--format=tar", f"--output={archive}", tree],
        cwd=ROOT,
        check=True,
    )
    with tarfile.open(archive) as payload:
        for path in _direct_entrypoints():
            assert payload.getmember(path).mode & 0o111, path


@pytest.mark.skipif(os.name == "nt", reason="Unix direct-execution contract")
def test_manual_checkout_entrypoints_execute_on_unix(tmp_path):
    profiles = subprocess.run(
        [str(ROOT / "bin" / "adr"), "profiles", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert profiles.returncode == 0, profiles.stderr
    hook = subprocess.run(
        [
            "sh",
            str(ROOT / "hooks" / "run-hook.cmd"),
            "SessionStart",
            "claude-code-cli",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert hook.returncode == 0, hook.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows polyglot-wrapper contract")
def test_manual_checkout_hook_wrapper_is_quiet_on_windows():
    wrapper = ROOT / "hooks" / "run-hook.cmd"
    result = subprocess.run(
        # Invoke by absolute path, matching how plugin.json launches the hook.
        # A bare name is not resolvable when NoDefaultCurrentDirectoryInExePath
        # is set, which is the default in several Windows shells.
        ["cmd.exe", "/d", "/c", str(wrapper), "SessionStart", "claude-code-cli"],
        cwd=wrapper.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert result.stderr == ""
    if result.stdout.strip():
        import json

        json.loads(result.stdout)
