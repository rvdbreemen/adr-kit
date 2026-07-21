from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))

from adr_readiness_ci import (  # noqa: E402
    annotations,
    github_escape,
    output_values,
    render_summary,
)
from test_adr_readiness import _write_adr  # noqa: E402


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repo(tmp_path: Path, status: str = "Proposed") -> tuple[Path, str, str]:
    root = tmp_path / "repo"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(
        adr_dir,
        1,
        status=status,
        verified_in=["src/service.py"],
    )
    (root / "src").mkdir()
    source = root / "src" / "service.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "init")
    _git(root, "config", "user.email", "tests@example.com")
    _git(root, "config", "user.name", "ADR Kit Tests")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD")
    source.write_text("VALUE = 2  # implements ADR-001\n", encoding="utf-8")
    _git(root, "add", "src/service.py")
    _git(root, "commit", "-m", "implement ADR-001")
    head = _git(root, "rev-parse", "HEAD")
    return root, base, head


def _run(root: Path, base: str, head: str):
    summary = root / "summary.md"
    outputs = root / "outputs.txt"
    result = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-readiness-ci"),
            "--repo-root",
            str(root),
            "--base",
            base,
            "--head",
            head,
            "--today",
            "2026-07-20",
            "--summary-file",
            str(summary),
            "--output-file",
            str(outputs),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result, summary, outputs


def test_ci_blocks_only_explicitly_linked_implemented_proposed(tmp_path):
    root, base, head = _repo(tmp_path, "Proposed")
    result, summary, outputs = _run(root, base, head)
    assert result.returncode == 1
    assert "::error title=ADR readiness block::" in result.stdout
    assert "/adr-kit:grill ADR-001" in result.stdout
    assert "[BLOCK]" in summary.read_text(encoding="utf-8")
    values = dict(
        line.split("=", 1)
        for line in outputs.read_text(encoding="utf-8").splitlines()
    )
    assert values["blocking-count"] == "1"
    assert json.loads(values["blocking-adrs"]) == ["ADR-001"]
    assert values["conclusion"] == "blocked"


@pytest.mark.parametrize("status", ["Accepted", "Rejected", "Superseded"])
def test_non_proposed_statuses_never_block(tmp_path, status):
    root, base, head = _repo(tmp_path, status)
    result, _summary, outputs = _run(root, base, head)
    assert result.returncode == 0
    assert "blocking-count=0" in outputs.read_text(encoding="utf-8")


def test_suspected_decision_is_advisory_and_fork_style_detached_sha_range_is_safe(
    tmp_path,
):
    root, _base, base = _repo(tmp_path, "Proposed")
    infra = root / "infra"
    infra.mkdir()
    (infra / "main.tf").write_text("resource \"x\" \"y\" {}\n", encoding="utf-8")
    _git(root, "add", "infra/main.tf")
    _git(root, "commit", "-m", "infrastructure change")
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--detach", head)
    result, summary, outputs = _run(root, base, head)
    assert result.returncode == 0
    assert "[ADVISORY]" in summary.read_text(encoding="utf-8")
    assert "`not-an-adr`" in summary.read_text(encoding="utf-8")
    assert "/adr-kit:grill --source" in summary.read_text(encoding="utf-8")
    assert "advisory-count=1" in outputs.read_text(encoding="utf-8")
    assert "classification=not-an-adr" in result.stdout


def test_shallow_clone_succeeds_when_exact_base_and_head_commits_are_present(tmp_path):
    source, base, head = _repo(tmp_path / "source", "Proposed")
    clone = tmp_path / "shallow"
    result = subprocess.run(
        ["git", "clone", "--depth", "2", source.as_uri(), str(clone)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr

    outcome, _summary, outputs = _run(clone, base, head)

    assert outcome.returncode == 1
    assert "blocking-count=1" in outputs.read_text(encoding="utf-8")


def test_nonimplemented_proposed_and_missing_ref_outcomes_are_distinct(tmp_path):
    root, base, head = _repo(tmp_path, "Proposed")
    clean_base = head
    (root / "README.md").write_text("ordinary docs\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "docs")
    clean_head = _git(root, "rev-parse", "HEAD")
    clean, _summary, _outputs = _run(root, clean_base, clean_head)
    assert clean.returncode == 0

    failed, _summary, _outputs = _run(root, "missing-base", clean_head)
    assert failed.returncode == 2
    assert "ADR readiness infrastructure" in failed.stdout


def test_multiple_linked_proposed_adrs_are_reported_stably(tmp_path):
    root, base, _head = _repo(tmp_path, "Proposed")
    _write_adr(
        root / "docs" / "adr",
        2,
        status="Proposed",
        verified_in=["src/service.py"],
    )
    _git(root, "add", "docs/adr")
    _git(root, "commit", "-m", "record ADR-002")
    head = _git(root, "rev-parse", "HEAD")

    result, _summary, outputs = _run(root, base, head)

    assert result.returncode == 1
    values = dict(
        line.split("=", 1)
        for line in outputs.read_text(encoding="utf-8").splitlines()
    )
    assert values["blocking-count"] == "2"
    assert json.loads(values["blocking-adrs"]) == ["ADR-001", "ADR-002"]


def test_github_content_escaping_and_machine_outputs():
    report = {
        "schema_version": 1,
        "evaluated_on": "2026-07-20",
        "summary": {
            "blocking_proposed": ["ADR-001"],
            "blocking_count": 1,
            "advisory_count": 1,
        },
        "adrs": [
            {
                "adr_id": "ADR-001",
                "title": "<script>\n::warning::",
                "status": "Proposed",
                "classification": "needs-human-input",
                "next_command": "/adr-kit:grill ADR-001",
                "implementation_link": {
                    "linked": True,
                    "blocking_proposed": True,
                    "evidence": [{"code": "ADR_ID_EXPLICIT"}],
                },
            }
        ],
        "advisories": [
            {
                "code": "ARCHITECTURE_REVIEW_RECOMMENDED",
                "path": "infra/%0Aevil\n::error::",
                "message": "review\nneeded",
            }
        ],
    }
    summary = render_summary(report)
    assert "<script>" not in summary
    assert "&lt;script&gt;" in summary
    assert all("\n" not in line.split("::", 2)[-1] for line in annotations(report))
    assert "%25" in "\n".join(annotations(report))
    assert output_values(report)["conclusion"] == "blocked"
    assert github_escape("a%\nb") == "a%25%0Ab"


def test_composite_action_is_key_free_comment_free_and_sha_based():
    text = (ROOT / ".github" / "actions" / "adr-readiness" / "action.yml").read_text(
        encoding="utf-8"
    )
    for forbidden in ("ANTHROPIC", "OPENAI", "API_KEY", "gh pr comment", "issue-comment"):
        assert forbidden not in text
    assert "pull_request.base.sha" in text
    assert "pull_request.head.sha" in text
    assert "GITHUB_STEP_SUMMARY" in text
    assert "GITHUB_OUTPUT" in text
    workflow = (ROOT / ".github" / "workflows" / "adr-readiness.yml").read_text(
        encoding="utf-8"
    )
    assert "branches: [dev, main]" in workflow
    assert "uses: ./.github/actions/adr-readiness" in workflow
