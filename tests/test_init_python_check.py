"""Documentation tests for the Python-availability requirement in adr-kit init and pre-commit hook."""

import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
INIT_SKILL = REPO_ROOT / "skills" / "init" / "SKILL.md"
PRE_COMMIT = REPO_ROOT / "templates" / "githooks" / "pre-commit"


def _init_text() -> str:
    return INIT_SKILL.read_text(encoding="utf-8")


def _hook_text() -> str:
    return PRE_COMMIT.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Init skill tests
# ---------------------------------------------------------------------------


def test_init_skill_has_step0():
    """skills/init/SKILL.md must contain a Step 0 section."""
    assert "Step 0" in _init_text(), "Expected 'Step 0' in skills/init/SKILL.md"


def test_init_skill_mentions_python39():
    """Init skill must reference Python 3.9 as the minimum required version."""
    assert "3.9" in _init_text(), "Expected '3.9' in skills/init/SKILL.md"


def test_init_skill_has_windows_install():
    """Init skill must contain Windows-specific installation instructions."""
    text = _init_text()
    assert "winget" in text or "Windows" in text, (
        "Expected 'winget' or 'Windows' in skills/init/SKILL.md"
    )


def test_init_skill_has_macos_install():
    """Init skill must contain macOS Homebrew installation instructions."""
    assert "brew" in _init_text(), "Expected 'brew' in skills/init/SKILL.md"


def test_init_skill_has_linux_install():
    """Init skill must contain Linux package manager installation instructions."""
    text = _init_text()
    assert "apt-get" in text or "dnf" in text, (
        "Expected 'apt-get' or 'dnf' in skills/init/SKILL.md"
    )


def test_init_skill_has_python_org_fallback():
    """Init skill must reference python.org as a universal fallback."""
    assert "python.org" in _init_text(), "Expected 'python.org' in skills/init/SKILL.md"


# ---------------------------------------------------------------------------
# Pre-commit hook tests
# ---------------------------------------------------------------------------


def test_pre_commit_has_python_check():
    """templates/githooks/pre-commit must contain the Python-not-found error message."""
    assert "Python 3 not found" in _hook_text(), (
        "Expected 'Python 3 not found' in templates/githooks/pre-commit"
    )


def test_pre_commit_python_check_is_nonblocking():
    """The Python check in the hook must exit 0 (non-blocking), not exit 1."""
    text = _hook_text()
    # Locate the block around the "Python 3 not found" sentinel.
    marker = "Python 3 not found"
    assert marker in text, f"Sentinel '{marker}' not found in pre-commit hook"

    marker_pos = text.index(marker)
    # Look at a reasonable window of chars after the marker to find the exit statement.
    window = text[marker_pos: marker_pos + 400]

    # The block must exit 0 (non-blocking).
    assert "exit 0" in window, (
        "Expected 'exit 0' within 400 chars after 'Python 3 not found' — hook must be non-blocking"
    )
    # The block must NOT exit 1 (that would block commits).
    assert "exit 1" not in window, (
        "Found 'exit 1' near 'Python 3 not found' — Python check must not block commits"
    )
