#!/usr/bin/env python3
"""How the release driver talks to the outside world.

Split from release_phases.py along the seam ADR-010 asks for: this module is
process invocation and repository interrogation, that one is the sequence of
steps. Keeping them apart means a phase reads as the runbook step it mirrors,
with the Windows and PATH details out of the way.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, NamedTuple, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "@rvdbreemen/adr-kit-opencode"
CLIENTS = ("claude", "codex", "copilot")


class ReleaseError(RuntimeError):
    """A phase refused to continue. The message says what to do next."""


class Context(NamedTuple):
    version: str
    skip_tests: bool
    timeout_min: int

    @property
    def tag(self) -> str:
        return f"v{self.version}"

    @property
    def branch(self) -> str:
        return f"release/v{self.version}"


def run(
    cmd: Sequence[str],
    *,
    check: bool = False,
    cwd: Optional[Path] = None,
) -> Tuple[int, str, str]:
    """Run a command and return (code, stdout, stderr), never raising on exit code.

    Returning the code rather than raising is deliberate: most callers here are
    asking a question ("is this already done?") where a non-zero answer is
    information, not a failure.
    """
    argv = list(cmd)
    # shutil.which applies PATHEXT, so `npm` finds npm.cmd on Windows. Without
    # it subprocess raises FileNotFoundError for every shim on PATH.
    resolved = shutil.which(argv[0])
    if resolved is None:
        return 127, "", f"{argv[0]}: not found on PATH"
    proc = subprocess.run(
        [resolved, *argv[1:]],
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise ReleaseError(
            f"{' '.join(cmd)} failed ({proc.returncode})\n{proc.stdout}{proc.stderr}"
        )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def git(*args: str, check: bool = False) -> Tuple[int, str, str]:
    return run(["git", *args], check=check)


def script(name: str, *args: str, check: bool = False) -> Tuple[int, str, str]:
    return run([sys.executable, str(ROOT / "scripts" / name), *args], check=check)


def _clean_tree() -> bool:
    return not git("status", "--porcelain")[1].strip()


def _version_everywhere(ctx: Context) -> bool:
    return script("check-release-version.py", "--expect", ctx.tag)[0] == 0


def _main_sha() -> str:
    git("fetch", "origin", "--tags")
    return git("rev-parse", "origin/main")[1].strip()

def _wait_until(predicate: Callable[[], bool], ctx: Context, what: str) -> None:
    deadline = time.monotonic() + ctx.timeout_min * 60
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(30)
    raise ReleaseError(
        f"gave up waiting for {what} after {ctx.timeout_min} minutes. Nothing is "
        "broken: re-run this command once it has happened and the finished "
        "phases will be skipped."
    )


def _client_version(client: str) -> Optional[str]:
    """Read the version a client reports, rather than trusting an exit code."""
    listings = {
        "claude": ["claude", "plugin", "list"],
        "copilot": ["copilot", "plugin", "list"],
        "codex": ["codex", "plugin", "list"],
    }
    code, out, _ = run(listings[client])
    if code != 0:
        return None
    for line in out.splitlines():
        if "adr-kit" in line.lower() or "version" in line.lower():
            found = re.search(r"(\d+\.\d+\.\d+)", line)
            if found:
                return found.group(1)
    return None
