"""Tests for the Python-availability check in templates/githooks/pre-commit.

Strategy
--------
Rather than executing the full hook (which requires git, a clone of the plugin cache,
and staged diffs), we extract the Python-detection logic into a small inline bash
script and drive it via a subprocess.  Tests that require bash are automatically
skipped when bash is not available on the system (e.g. pure Windows without Git Bash).
"""

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_usable_bash() -> str | None:
    """Return a bash executable that can actually run scripts.

    On Windows, C:\\Windows\\system32\\bash.exe can exist even when WSL is not
    usable. `shutil.which("bash")` alone then makes these tests fail with WSL
    launcher errors instead of skipping as intended.
    """
    bash = shutil.which("bash")
    if bash is None:
        return None
    try:
        result = subprocess.run(
            [bash, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return bash if result.returncode == 0 else None


BASH = _find_usable_bash()
REQUIRES_BASH = pytest.mark.skipif(BASH is None, reason="bash not available on this system")


def _bash_can_see_python3() -> bool:
    if BASH is None:
        return False
    result = subprocess.run(
        [
            BASH,
            "-lc",
            "for c in python3 python py; do "
            "command -v \"$c\" >/dev/null 2>&1 || continue; "
            "v=$(\"$c\" --version 2>&1 | grep -oE '[0-9]+\\.[0-9]+' | head -1); "
            "m=$(echo \"$v\" | cut -d. -f1); "
            "if [ \"${m:-0}\" -ge 3 ] 2>/dev/null; then exit 0; fi; "
            "done; exit 1",
        ],
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=10,
    )
    return result.returncode == 0


BASH_HAS_PYTHON3 = _bash_can_see_python3()

# Minimal bash script that replicates the Python-detection block from the hook.
# It exits 42 if Python 3 is found (to distinguish from the exit 0 non-blocking path),
# and exits 0 (with error messages) when Python is absent — matching hook behaviour.
_PYTHON_CHECK_SCRIPT = r"""#!/usr/bin/env bash
set -e

_PYTHON3=""
for _cmd in python3 python py; do
  if command -v "$_cmd" >/dev/null 2>&1; then
    _ver=$("$_cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    _major=$(echo "$_ver" | cut -d. -f1)
    if [ "${_major:-0}" -ge 3 ] 2>/dev/null; then
      _PYTHON3="$_cmd"
      break
    fi
  fi
done

if [ -z "$_PYTHON3" ]; then
  echo "[adr-kit] ERROR: Python 3 not found. adr-judge requires Python 3.9+." >&2
  echo "[adr-kit] Install Python: https://www.python.org/downloads/" >&2
  echo "[adr-kit] On macOS: brew install python3" >&2
  echo "[adr-kit] On Windows: winget install Python.Python.3.12" >&2
  echo "[adr-kit] Skipping ADR check for this commit." >&2
  exit 0
fi

# Signal that Python was found (exit code 42 is our sentinel — hook would continue).
exit 42
"""


def _run_check_script(env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the inline Python-check script via bash and return the CompletedProcess."""
    assert BASH is not None, "bash is required for this helper"
    result = subprocess.run(
        [BASH, "-c", _PYTHON_CHECK_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result


def _empty_path_env() -> dict:
    """Build a minimal environment with a PATH that has no Python commands."""
    env = {k: v for k, v in os.environ.items()}
    # On POSIX-ish systems (including Git Bash on Windows) we can point PATH at an
    # empty/nonexistent directory so that `command -v python3` etc. fail.
    env["PATH"] = "/nonexistent_path_for_testing"
    # Keep HOME so bash finds its rc files (or doesn't crash looking for them).
    env["HOME"] = os.environ.get("HOME", str(pathlib.Path.home()))
    return env


# ---------------------------------------------------------------------------
# Bash-based integration tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(BASH is None, reason="bash not available on this system")
def test_hook_skips_gracefully_when_python_missing():
    """When no Python command is on PATH the check must exit 0 (non-blocking)."""
    result = _run_check_script(env=_empty_path_env())
    assert result.returncode == 0, (
        f"Expected exit 0 when Python is absent, got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )


@pytest.mark.skipif(BASH is None, reason="bash not available on this system")
@pytest.mark.skipif(
    not BASH_HAS_PYTHON3,
    reason="bash is available but cannot see a Python 3 command",
)
def test_hook_continues_when_python3_found():
    """When Python 3 is available the check must pass through (sentinel exit 42)."""
    # Use the current process's PATH — Python is definitely available here because
    # we're running under it right now.
    result = _run_check_script(env=dict(os.environ))
    assert result.returncode == 42, (
        f"Expected sentinel exit 42 when Python 3 is found, got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )


@pytest.mark.skipif(BASH is None, reason="bash not available on this system")
def test_python_check_message_contains_install_instructions():
    """When Python is missing, stderr must contain the python.org install URL."""
    result = _run_check_script(env=_empty_path_env())
    assert "python.org" in result.stderr, (
        f"Expected 'python.org' in stderr when Python is absent.\nstderr: {result.stderr}"
    )


@pytest.mark.skipif(BASH is None, reason="bash not available on this system")
def test_python_check_message_contains_platform_hints():
    """When Python is missing, stderr must mention both macOS and Windows install commands."""
    result = _run_check_script(env=_empty_path_env())
    assert "brew install python3" in result.stderr, (
        f"Expected macOS hint in stderr.\nstderr: {result.stderr}"
    )
    assert "winget" in result.stderr, (
        f"Expected Windows hint in stderr.\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Pure-Python structural tests (no bash required)
# ---------------------------------------------------------------------------


def test_hook_template_contains_python_check_block():
    """The pre-commit template must contain the full Python-detection loop."""
    hook = (REPO_ROOT / "templates" / "githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "_PYTHON3" in hook, "Expected _PYTHON3 variable in pre-commit hook"
    assert "command -v" in hook, "Expected 'command -v' in pre-commit hook Python check"
    assert "python3 python py" in hook, (
        "Expected 'python3 python py' candidate list in pre-commit hook"
    )


def test_hook_template_python_check_exits_zero_not_one():
    """The Python-absent branch must use exit 0, never exit 1."""
    hook = (REPO_ROOT / "templates" / "githooks" / "pre-commit").read_text(encoding="utf-8")
    marker = "Python 3 not found"
    assert marker in hook
    pos = hook.index(marker)
    window = hook[pos: pos + 400]
    assert "exit 0" in window, "Python-absent branch must exit 0 (non-blocking)"
    assert "exit 1" not in window, "Python-absent branch must not exit 1 (would block commits)"


def test_hook_template_bash_syntax():
    """The pre-commit hook must pass bash -n syntax check (if bash is available)."""
    if BASH is None:
        pytest.skip("bash not available")
    hook_path = REPO_ROOT / "templates" / "githooks" / "pre-commit"
    # Pass bytes so Windows does not translate LF to CRLF on stdin. In
    # particular, WSL bash otherwise receives tokens such as ``do\r`` even
    # though the repository hook itself has canonical LF line endings.
    hook = hook_path.read_bytes().replace(b"\r\n", b"\n")
    result = subprocess.run(
        [BASH, "-n"],
        input=hook,
        capture_output=True,
        timeout=10,
    )
    stderr = result.stderr.decode("utf-8", errors="replace")
    assert result.returncode == 0, (
        f"bash -n syntax check failed:\n{stderr}"
    )


def test_hook_resolves_all_native_plugin_caches():
    """The shared wrapper must not depend on Claude's cache alone."""
    hook = (REPO_ROOT / "templates" / "githooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    assert ".claude/plugins/cache/rvdbreemen-adr-kit/adr-kit" in hook
    assert (
        ".codex}/plugins/cache/rvdbreemen-adr-kit-codex/adr-kit" in hook
    )
    assert (
        ".copilot}/installed-plugins/rvdbreemen-adr-kit-copilot/adr-kit"
        in hook
    )
    assert ".codex-plugin/plugin.json" in hook
    assert '_plugin_root/plugin.json"' in hook
