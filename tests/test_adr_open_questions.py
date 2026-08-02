from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from test_adr_readiness import _write_adr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from adr_format import PROFILE_HEADINGS, unresolved_open_questions  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
ADR = REPO_ROOT / "bin" / "adr"
LINT = REPO_ROOT / "bin" / "adr-lint"


def test_proposed_open_questions_are_advisory_even_in_strict_mode(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, open_questions="- [ ] Who owns the migration?")

    result = subprocess.run(
        [sys.executable, str(LINT), "--strict", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "ADVISORY only (1)" in result.stdout
    assert "OPEN_QUESTIONS_UNRESOLVED" not in result.stderr


def test_accept_rejects_unresolved_open_questions_without_mutation(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(
        adr_dir, 1, open_questions="- [ ] Who accepts the operational risk?"
    )
    before = path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(ADR),
            "accept",
            "ADR-001",
            "--adr-dir",
            str(adr_dir),
            "--changed-by",
            "User: Test Signer",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 2
    assert "unresolved Open Questions" in result.stderr
    assert path.read_bytes() == before


def test_accepted_open_questions_fail_strict_lint(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(
        adr_dir,
        1,
        status="Accepted",
        open_questions="- [ ] Who accepts the operational risk?",
    )

    result = subprocess.run(
        [sys.executable, str(LINT), "--strict", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 1
    assert "Accepted ADRs cannot contain unresolved questions" in result.stdout


@pytest.mark.parametrize(
    "open_questions",
    [
        "None.",
        "",
        "- [x] The platform owner accepted the risk.",
        "- Answered: the platform owner accepts the risk.",
    ],
)
def test_resolved_or_absent_questions_do_not_block_acceptance(
    tmp_path, open_questions
):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, open_questions=open_questions)

    result = subprocess.run(
        [
            sys.executable,
            str(ADR),
            "accept",
            "ADR-001",
            "--adr-dir",
            str(adr_dir),
            "--changed-by",
            "User: Test Signer",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "status: Accepted" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("profile", ["madr", "nygard", "canonical"])
@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", []),
        ("None.", []),
        ("- [ ] Who owns rollout?", ["Who owns rollout?"]),
        ("- [x] The platform team owns rollout.", []),
        ("- Answered: the platform team owns rollout.", []),
    ],
)
def test_open_questions_profile_matrix(profile, content, expected):
    heading = PROFILE_HEADINGS[profile]["open_questions"]
    text = f"# Decision\n\n## {heading}\n\n{content}\n"
    assert unresolved_open_questions(text) == expected
