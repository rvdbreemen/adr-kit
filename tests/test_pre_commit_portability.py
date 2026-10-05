"""Portability of the pre-commit hook template (GitHub issue #155, TASK-216).

These tests run blocks cut from the real template rather than a copy of them,
so a later edit to the hook cannot drift away from what is tested.

1. The interpreter probe must skip a Python older than 3.10 and keep looking.
2. The plugin-version comparison must not depend on GNU ``sort -V``.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "templates" / "githooks" / "pre-commit"


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


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _probe_block() -> str:
    """The interpreter probe: from `_PYTHON3=""` through its closing `done`."""
    match = re.search(r'^_PYTHON3=""\n.*?^done\n', _template(), re.S | re.M)
    assert match, "interpreter probe block not found in the template"
    return match.group(0)


def _version_ge_function() -> str:
    match = re.search(r"^_version_ge\(\) \{\n.*?^\}\n", _template(), re.S | re.M)
    assert match, "_version_ge() not found in the template"
    return match.group(0)


def _stub(directory: pathlib.Path, name: str, version: str) -> None:
    """A fake interpreter that reports `version` however it is asked.

    `--version` answers like CPython does; any `-c` program gets "major minor",
    which is what the probe's one-liner prints on a real interpreter.
    """
    major, minor = version.split(".")[:2]
    path = directory / name
    path.write_text(
        "#!/usr/bin/env bash\n"
        f'if [ "$1" = "--version" ]; then echo "Python {version}"; exit 0; fi\n'
        f'echo "{major} {minor}"\n',
        encoding="utf-8",
        newline="\n",
    )
    path.chmod(0o755)


def _run_probe(stub_dir: pathlib.Path) -> str:
    script = _probe_block() + 'printf "%s" "$_PYTHON3"\n'
    # Stubs first; then only the shell's own tool directories, so grep, cut and
    # env resolve while every python name the probe tries is shadowed by a stub.
    for name in ("python3", "python", "py"):
        if not (stub_dir / name).exists():
            _stub(stub_dir, name, "2.7.18")
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(
        [str(stub_dir), str(pathlib.Path(BASH).parent), "/usr/bin", "/bin"]
    )
    result = subprocess.run(
        [BASH, "-c", script], capture_output=True, text=True, env=env, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@needs_bash
def test_probe_skips_python_below_310_and_keeps_searching(tmp_path):
    _stub(tmp_path, "python3", "3.9.18")
    _stub(tmp_path, "python", "3.12.1")
    assert _run_probe(tmp_path) == "python"


@needs_bash
def test_probe_takes_the_first_python_at_or_above_310(tmp_path):
    _stub(tmp_path, "python3", "3.10.0")
    _stub(tmp_path, "python", "3.12.1")
    assert _run_probe(tmp_path) == "python3"


@needs_bash
def test_probe_finds_nothing_when_every_python_is_too_old(tmp_path):
    _stub(tmp_path, "python3", "3.8.10")
    _stub(tmp_path, "python", "2.7.18")
    assert _run_probe(tmp_path) == ""


@needs_bash
def test_probe_accepts_the_real_interpreter_running_this_suite(tmp_path):
    # The suite itself needs 3.10+, so the probe must accept it, including on
    # Windows where its output ends in CRLF.
    link = tmp_path / "python3"
    link.write_text(
        f'#!/usr/bin/env bash\nexec "{pathlib.Path(sys.executable).as_posix()}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    link.chmod(0o755)
    assert _run_probe(tmp_path) == "python3"


def test_template_does_not_use_gnu_sort_version():
    assert "sort -V" not in _template()


@needs_bash
@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("0.10.0", "0.9.0", True),  # numeric, not lexical
        ("0.59.0", "0.59.0", True),  # a tie takes the candidate, as sort -V did
        ("0.58.0", "0.59.0", False),
        ("1.0.0", "0.99.9", True),
    ],
)
def test_version_ge_compares_numerically(left, right, expected):
    script = (
        f'_PYTHON3="{pathlib.Path(sys.executable).as_posix()}"\n'
        + _version_ge_function()
        + f'if _version_ge "{left}" "{right}"; then echo yes; else echo no; fi\n'
    )
    result = subprocess.run(
        [BASH, "-c", script], capture_output=True, text=True, timeout=10
    )
    assert result.stdout.strip() == ("yes" if expected else "no"), result.stderr
