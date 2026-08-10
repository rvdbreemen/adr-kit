"""A timeout that actually bounds, even behind a shim.

`subprocess.run(..., timeout=N)` does not bound anything once a descendant
outlives the direct child. CPython's own handler is:

    except TimeoutExpired as exc:
        process.kill()
        if _mswindows:
            exc.stdout, exc.stderr = process.communicate()   # no timeout

and `Popen.kill` on Windows is `TerminateProcess` on one handle - no job
object, no tree kill. So the timeout kills the shim and then waits, without a
bound, for a grandchild that still holds the output pipe. Measured with an
8-second grandchild and `timeout=2`: 2.03s direct, 8.18s behind `cmd /c`.

That matters because a client CLI resolving to a `.CMD` shim is normal rather
than exotic: `copilot` does on a machine where it came from npm, and so do
`claude` and `codex` for anyone who installed them that way. ADR-010 describes
these calls as bounded, so the claim has to be made true rather than quietly
dropped (TASK-171).

The fix is to kill the whole tree and then bound the drain as well.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys

# How long to wait for the pipes to drain after the tree has been killed. This
# is a bound on cleanup, not on the command: reaching it means the descendants
# survived the kill, which is a broken machine rather than a slow one.
DRAIN_SECONDS = 5.0


def _kill_tree(process: subprocess.Popen) -> None:
    """Kill the process and everything it started."""
    if sys.platform == "win32":
        try:
            # taskkill /T reaches the grandchildren that Popen.kill cannot.
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=DRAIN_SECONDS,
            )
        except (OSError, subprocess.SubprocessError):
            # Never leave through an unexpected exception: the caller asked for
            # a bounded run and handles TimeoutExpired, not "taskkill missing".
            process.kill()
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, PermissionError):
        process.kill()


def run_bounded(
    command, *, timeout: float, stdin=subprocess.DEVNULL, **kwargs
) -> subprocess.CompletedProcess:
    """`subprocess.run`, but the timeout is a real upper bound.

    Raises `subprocess.TimeoutExpired` like `run` does, so callers that already
    handle it need no change. `stdin` defaults to DEVNULL rather than to the
    console: every caller here starts a third-party CLI, and an inherited
    console stdin is what turns a slow wait into a permanent one (TASK-165).
    """
    if kwargs.pop("capture_output", False):
        kwargs.setdefault("stdout", subprocess.PIPE)
        kwargs.setdefault("stderr", subprocess.PIPE)
    if sys.platform != "win32":
        # Give the child its own process group so the whole tree is killable.
        kwargs.setdefault("start_new_session", True)
    with subprocess.Popen(list(command), stdin=stdin, **kwargs) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(process)
            try:
                stdout, stderr = process.communicate(timeout=DRAIN_SECONDS)
            except subprocess.TimeoutExpired:
                stdout, stderr = None, None
            raise subprocess.TimeoutExpired(
                process.args, timeout, output=stdout, stderr=stderr
            ) from None
    return subprocess.CompletedProcess(
        process.args, process.returncode, stdout, stderr
    )
