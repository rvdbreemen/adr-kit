"""End-to-end tests for bin/adr-generate-scripts.

Runs the CLI as a subprocess and asserts on generated file contents and
exit codes. Mirrors the patterns established by test_adr_lint.py and
test_adr_judge.py.
"""
from __future__ import annotations

import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE_SCRIPTS = REPO_ROOT / "bin" / "adr-generate-scripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_adr(adr_dir: Path, filename: str, body: str) -> Path:
    """Write an ADR file into adr_dir."""
    adr_dir.mkdir(parents=True, exist_ok=True)
    p = adr_dir / filename
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def _run_generator(*extra_args, adr_dir: Path, output_dir: Path) -> subprocess.CompletedProcess:
    """Invoke adr-generate-scripts and return the CompletedProcess."""
    cmd = [
        sys.executable,
        str(GENERATE_SCRIPTS),
        "--adr-dir", str(adr_dir),
        "--output", str(output_dir),
        *extra_args,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Shared fixture ADR content
# ---------------------------------------------------------------------------

SIMPLE_ADR = """\
    # ADR-001 No Foo

    ## Status

    Accepted, 2026-04-25.

    ## Context

    Foo fragments the heap.

    ## Decision

    Do not use Foo.

    ## Alternatives Considered

    - Use Foo: rejected.

    ## Consequences

    Cleaner heap.

    ## Related Decisions

    - None.

    ## References

    - None.

    ## Enforcement

    ```json
    {
      "forbid_pattern": [
        {"pattern": "\\\\bFoo\\\\b", "message": "Do not use Foo."}
      ]
    }
    ```
"""

ADR_WITH_IMPORT = """\
    # ADR-002 No Bar Import

    ## Status

    Accepted, 2026-04-25.

    ## Context

    Bar is deprecated.

    ## Decision

    Do not import Bar.

    ## Alternatives Considered

    - Import Bar: rejected.

    ## Consequences

    Less coupling.

    ## Related Decisions

    - None.

    ## References

    - None.

    ## Enforcement

    ```json
    {
      "forbid_import": [
        {"pattern": "import bar", "message": "Do not import bar."}
      ]
    }
    ```
"""

ADR_NO_ENFORCEMENT = """\
    # ADR-003 No Enforcement

    ## Status

    Accepted, 2026-04-25.

    ## Context

    A design choice with no code surface.

    ## Decision

    Use a whiteboard.

    ## Alternatives Considered

    - None.

    ## Consequences

    Better diagrams.

    ## Related Decisions

    - None.

    ## References

    - None.
"""

ADR_WITH_LLM_JUDGE_ONLY = """\
    # ADR-004 LLM Judge Only

    ## Status

    Accepted, 2026-04-25.

    ## Context

    Requires human-like judgement.

    ## Decision

    Use domain models consistently.

    ## Alternatives Considered

    - None.

    ## Consequences

    Consistent design.

    ## Related Decisions

    - None.

    ## References

    - None.

    ## Enforcement

    ```json
    {
      "llm_judge": true
    }
    ```
"""


# ---------------------------------------------------------------------------
# Tests: file existence
# ---------------------------------------------------------------------------

def test_python_script_generated(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    result = _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert (output_dir / "ADR-001" / "validate.py").exists()


def test_shell_script_generated(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    result = _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert (output_dir / "ADR-001" / "validate.sh").exists()


def test_all_generates_python_and_shell(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    result = _run_generator("--lang", "all", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert (output_dir / "ADR-001" / "validate.py").exists()
    assert (output_dir / "ADR-001" / "validate.sh").exists()


# ---------------------------------------------------------------------------
# Tests: injected pattern content
# ---------------------------------------------------------------------------

def test_python_script_contains_pattern(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    content = (output_dir / "ADR-001" / "validate.py").read_text(encoding="utf-8")
    # Pattern is written via repr(), so \bFoo\b appears as \\bFoo\\b in the file.
    assert "bFoo" in content
    assert "re.compile(" in content
    assert "Do not use Foo." in content


def test_shell_script_contains_pattern(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    content = (output_dir / "ADR-001" / "validate.sh").read_text(encoding="utf-8")
    assert r"\bFoo\b" in content
    assert "Do not use Foo." in content


# ---------------------------------------------------------------------------
# Tests: standalone (no adr-kit dependency)
# ---------------------------------------------------------------------------

def test_python_script_no_adr_kit_imports(tmp_path):
    """Generated Python script must not import any adr-kit module."""
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    content = (output_dir / "ADR-001" / "validate.py").read_text(encoding="utf-8")
    import re as _re
    assert not _re.search(r"^import adr|^from adr", content, _re.MULTILINE), (
        "Python script should not import adr-kit modules"
    )
    # Only stdlib imports: re and sys.
    assert "import re" in content
    assert "import sys" in content


def test_python_script_uses_re_compile(tmp_path):
    """Generated Python script compiles patterns with re.compile."""
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    content = (output_dir / "ADR-001" / "validate.py").read_text(encoding="utf-8")
    assert "re.compile(" in content


# ---------------------------------------------------------------------------
# Tests: --lang flag filtering
# ---------------------------------------------------------------------------

def test_lang_flag_shell_only(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    result = _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr

    adr_out = output_dir / "ADR-001"
    assert (adr_out / "validate.sh").exists()
    assert not (adr_out / "validate.py").exists()


def test_lang_flag_python_only(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    result = _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr

    adr_out = output_dir / "ADR-001"
    assert (adr_out / "validate.py").exists()
    assert not (adr_out / "validate.sh").exists()


# ---------------------------------------------------------------------------
# Tests: output directory creation
# ---------------------------------------------------------------------------

def test_output_dir_created(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / "deeply" / "nested" / "output"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    assert not output_dir.exists()
    result = _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert output_dir.is_dir()
    assert (output_dir / "ADR-001" / "validate.sh").exists()


# ---------------------------------------------------------------------------
# Tests: ADR without Enforcement → no script generated
# ---------------------------------------------------------------------------

def test_no_enforcement_no_script(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-003-no-enforcement.md", ADR_NO_ENFORCEMENT)

    result = _run_generator(adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert not (output_dir / "ADR-003").exists()


# ---------------------------------------------------------------------------
# Tests: ADR with only llm_judge (no forbid rules) → no script
# ---------------------------------------------------------------------------

def test_llm_judge_only_no_script(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-004-llm-only.md", ADR_WITH_LLM_JUDGE_ONLY)

    result = _run_generator(adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert not (output_dir / "ADR-004").exists()


# ---------------------------------------------------------------------------
# Tests: multiple ADRs → multiple subdirectories
# ---------------------------------------------------------------------------

def test_multiple_adrs_multiple_scripts(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)
    _write_adr(adr_dir, "ADR-002-no-bar.md", ADR_WITH_IMPORT)

    result = _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    assert (output_dir / "ADR-001" / "validate.sh").exists()
    assert (output_dir / "ADR-002" / "validate.sh").exists()


# ---------------------------------------------------------------------------
# Tests: forbid_import treated same as forbid_pattern
# ---------------------------------------------------------------------------

def test_forbid_import_generates_script(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-002-no-bar.md", ADR_WITH_IMPORT)

    result = _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    assert result.returncode == 0, result.stderr
    content = (output_dir / "ADR-002" / "validate.sh").read_text(encoding="utf-8")
    assert "import bar" in content
    assert "Do not import bar." in content


# ---------------------------------------------------------------------------
# Tests: functional — generated Python script actually validates
# ---------------------------------------------------------------------------

def test_python_script_validates_violation(tmp_path):
    """Generated Python script detects a violation and exits 1."""
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    gen = _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    assert gen.returncode == 0, gen.stderr

    py_script = output_dir / "ADR-001" / "validate.py"
    assert py_script.exists()

    result = subprocess.run(
        [sys.executable, str(py_script)],
        input="x = Foo()\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1, (
        f"Expected exit 1 for forbidden content, got {result.returncode}. "
        f"stderr: {result.stderr!r}"
    )
    assert "VIOLATION" in result.stderr


def test_python_script_validates_clean(tmp_path):
    """Generated Python script exits 0 for content with no violations."""
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    gen = _run_generator("--lang", "python", adr_dir=adr_dir, output_dir=output_dir)
    assert gen.returncode == 0, gen.stderr

    py_script = output_dir / "ADR-001" / "validate.py"

    result = subprocess.run(
        [sys.executable, str(py_script)],
        input="x = Bar()\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, (
        f"Expected exit 0 for clean content, got {result.returncode}. "
        f"stderr: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Tests: shell script structure
# ---------------------------------------------------------------------------

def test_shell_script_has_shebang(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    content = (output_dir / "ADR-001" / "validate.sh").read_text(encoding="utf-8")
    assert content.startswith("#!/bin/bash")


@pytest.mark.skipif(sys.platform == "win32", reason="chmod not applicable on Windows")
def test_shell_script_is_executable(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    sh = output_dir / "ADR-001" / "validate.sh"
    assert sh.exists()
    mode = sh.stat().st_mode
    assert mode & stat.S_IXUSR, "validate.sh should have user execute bit set"


@pytest.mark.skipif(
    shutil.which("bash") is None or sys.platform == "win32",
    reason="bash not on PATH or Windows bash filesystem incompatible with Python tempdir",
)
def test_shell_script_validates_violation(tmp_path):
    """Generated shell script detects a violation and exits 1."""
    adr_dir = tmp_path / "docs" / "adr"
    output_dir = tmp_path / ".generated"
    _write_adr(adr_dir, "ADR-001-no-foo.md", SIMPLE_ADR)

    gen = _run_generator("--lang", "shell", adr_dir=adr_dir, output_dir=output_dir)
    assert gen.returncode == 0, gen.stderr

    sh_script = output_dir / "ADR-001" / "validate.sh"
    result = subprocess.run(
        ["bash", str(sh_script)],
        input="x = Foo()\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1
