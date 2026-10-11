"""Portability of the guardian SessionStart entry (TASK-220, the #155 class).

The entry picks the newest cached adr-kit and runs its guardian. It used
`ls ... | sort -V | tail -1`; where `sort` has no version mode that pipeline
yields nothing, and the `[ -n ... ] || true` chain then skips the guardian
silently on every session start. These tests run the real command from the
template, not a copy of it.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRY = REPO_ROOT / "templates" / "cc-settings" / "guardian-hook-entry.json"
CACHE = pathlib.Path(".claude/plugins/cache/rvdbreemen-adr-kit/adr-kit")


def _usable_bash() -> str | None:
    bash = shutil.which("bash")
    if bash is None:
        return None
    try:
        ok = subprocess.run([bash, "--version"], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return bash if ok.returncode == 0 else None


BASH = _usable_bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="bash not available")


def _write_exe(path: pathlib.Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def _fake_home(tmp_path: pathlib.Path, versions: list[str]) -> pathlib.Path:
    """A HOME whose plugin cache holds one guardian per version.

    Each guardian records which version ran, so the test can see the pick.
    """
    home = tmp_path / "home"
    marker = tmp_path / "ran.txt"
    for version in versions:
        bin_dir = home / CACHE / version / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "adr-guardian").write_text(
            "import pathlib, sys\n"
            f"pathlib.Path({str(marker)!r}).write_text({version!r})\n",
            encoding="utf-8",
        )
    return home


def _run_entry(tmp_path: pathlib.Path, home: pathlib.Path, *, gnu_sort: bool) -> str:
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    # The entry looks for python3 first; point it at the interpreter running
    # this suite so the guardian stub runs everywhere, Windows included.
    _write_exe(stubs / "python3", f'exec "{pathlib.Path(sys.executable).as_posix()}" "$@"\n')
    if not gnu_sort:
        _write_exe(
            stubs / "sort",
            'for a in "$@"; do\n'
            '  if [ "$a" = "-V" ]; then echo "sort: invalid option -- V" >&2; exit 2; fi\n'
            "done\n"
            'exec /usr/bin/sort "$@"\n',
        )
    command = json.loads(ENTRY.read_text(encoding="utf-8"))["command"]
    env = dict(os.environ)
    env["HOME"] = home.as_posix()
    env["PATH"] = os.pathsep.join(
        [str(stubs), str(pathlib.Path(BASH).parent), "/usr/bin", "/bin"]
    )
    result = subprocess.run(
        [BASH, "-c", command], capture_output=True, text=True, env=env, timeout=30
    )
    assert result.returncode == 0, result.stderr
    marker = tmp_path / "ran.txt"
    return marker.read_text(encoding="utf-8") if marker.exists() else ""


@needs_bash
def test_entry_runs_the_guardian_where_sort_has_no_version_mode(tmp_path):
    home = _fake_home(tmp_path, ["0.58.0", "0.59.1"])
    assert _run_entry(tmp_path, home, gnu_sort=False) == "0.59.1"


@needs_bash
def test_entry_picks_the_numerically_newest_version(tmp_path):
    # 0.10.0 sorts before 0.9.0 as text; the entry must compare numbers.
    home = _fake_home(tmp_path, ["0.9.0", "0.10.0"])
    assert _run_entry(tmp_path, home, gnu_sort=True) == "0.10.0"


@needs_bash
def test_entry_is_silent_without_a_cached_plugin(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    assert _run_entry(tmp_path, home, gnu_sort=True) == ""


def test_entry_does_not_use_gnu_sort_version_mode():
    assert "sort -V" not in json.loads(ENTRY.read_text(encoding="utf-8"))["command"]
