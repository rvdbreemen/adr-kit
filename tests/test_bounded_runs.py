"""The declared timeout on a client call must be a real upper bound (TASK-171).

`subprocess.run(timeout=N)` is not one: its own TimeoutExpired handler kills
the direct child and then drains the pipes with no bound, while on Windows the
kill is TerminateProcess on a single handle. Behind a `.CMD` shim - which is
what an npm-installed client CLI is - the grandchild survives and holds the
pipe, so the call returns when the grandchild feels like it.

The shape under test is the recorded one, not an approximation of it: a `.cmd`
that starts a Python grandchild, run through `cmd.exe /d /c`, exactly like
`copilot.CMD` starting node. Measured on Windows with a 6-second grandchild
and `timeout=1`: `subprocess.run` returned after 6.23s, `run_bounded` after
1.71s.

The grandchild sleeps 3 seconds, which is the smallest gap that separates a
bounded run from an unbounded one without weighing on the suite.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clients.installer.bounded import run_bounded  # noqa: E402

GRANDCHILD_SECONDS = 3
TIMEOUT = 1


def _shim_with_grandchild(tmp_path: Path) -> list[str]:
    """A parent that dies on kill while its child keeps the pipe open.

    On Windows this is a real `.cmd` through `cmd.exe`, the shape a client CLI
    installed through npm actually has. Elsewhere a Python parent stands in:
    the point is a surviving descendant, and POSIX has no `.cmd`.
    """
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(
        f"import time, sys\ntime.sleep({GRANDCHILD_SECONDS})\n"
        "sys.stdout.write('grandchild done')\n",
        encoding="utf-8",
    )
    if sys.platform == "win32":
        shim = tmp_path / "shim.cmd"
        shim.write_text(
            f'@echo off\r\n"{sys.executable}" "{sleeper}"\r\n', encoding="utf-8"
        )
        return ["cmd.exe", "/d", "/c", str(shim)]
    parent = tmp_path / "parent.py"
    parent.write_text(
        f"import subprocess, sys\nsubprocess.run([sys.executable, {str(sleeper)!r}])\n",
        encoding="utf-8",
    )
    return [sys.executable, str(parent)]


def test_run_bounded_returns_within_its_timeout_despite_a_surviving_grandchild(tmp_path):
    started = time.perf_counter()
    with pytest.raises(subprocess.TimeoutExpired):
        run_bounded(
            _shim_with_grandchild(tmp_path), timeout=TIMEOUT,
            capture_output=True, text=True,
        )
    elapsed = time.perf_counter() - started

    assert elapsed < GRANDCHILD_SECONDS, (
        f"run_bounded took {elapsed:.2f}s; the grandchild lives "
        f"{GRANDCHILD_SECONDS}s, so the timeout bounded nothing"
    )


def test_plain_subprocess_run_is_the_behaviour_this_replaces(tmp_path):
    """Pin the defect, so the fix cannot be quietly reverted.

    Windows only: the unbounded recovery drain lives in the `_mswindows`
    branch of CPython's `run`, and POSIX bounds that second wait.
    """
    if sys.platform != "win32":
        pytest.skip("the unbounded recovery drain is Windows-specific")
    started = time.perf_counter()
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            _shim_with_grandchild(tmp_path), timeout=TIMEOUT,
            capture_output=True, text=True,
        )
    elapsed = time.perf_counter() - started
    assert elapsed >= GRANDCHILD_SECONDS - 0.5, (
        f"plain run returned in {elapsed:.2f}s against a {GRANDCHILD_SECONDS}s "
        f"grandchild; if this now bounds, CPython changed and "
        f"clients/installer/bounded.py should be re-evaluated"
    )


def test_run_bounded_passes_through_a_normal_result(tmp_path):
    result = run_bounded(
        [sys.executable, "-c", "print('ok')"],
        timeout=30, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"


def test_run_bounded_closes_stdin_unless_the_caller_says_otherwise():
    """Default DEVNULL: every caller starts a CLI we do not control."""
    reads_stdin = [sys.executable, "-c", "import sys; print(len(sys.stdin.read()))"]
    assert run_bounded(reads_stdin, timeout=30, capture_output=True, text=True).stdout.strip() == "0"
    piped = run_bounded(
        reads_stdin, timeout=30, capture_output=True, text=True,
        stdin=subprocess.PIPE,
    )
    assert piped.returncode == 0
