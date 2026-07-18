"""Fail-closed runtime configuration checks for judge and suggest."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
JUDGE = ROOT / "bin" / "adr-judge"
SUGGEST = ROOT / "bin" / "adr-suggest"


def _project(tmp_path: Path, config) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps(config),
        encoding="utf-8",
    )
    return tmp_path


def _run(script: Path, project: Path, diff: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--diff",
            "-",
            "--adr-dir",
            str(project / "docs" / "adr"),
            "--repo-root",
            str(project),
        ],
        input=diff,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.mark.parametrize(
    ("config", "expected_path"),
    [
        ({"judge": {"advisory_only": "false"}}, "$.judge.advisory_only"),
        ({"judge": {"max_diff_bytes": -1}}, "$.judge.max_diff_bytes"),
        ({"judge": {"llm_enabled": "false"}}, "$.judge.llm_enabled"),
        ({"judge": {"pre_commit_timeout_ms": None}}, "$.judge.pre_commit_timeout_ms"),
        ({"judge": []}, "$.judge"),
        ({"judge": {"unexpected": True}}, "$.judge.unexpected"),
        ({"unexpected": True}, "$.unexpected"),
    ],
)
def test_judge_rejects_invalid_runtime_config(tmp_path, config, expected_path):
    result = _run(JUDGE, _project(tmp_path, config))

    assert result.returncode == 2
    assert "schema validation failed" in result.stderr
    assert expected_path in result.stderr


def test_invalid_false_string_cannot_enable_suggest(tmp_path):
    project = _project(tmp_path, {"suggest": {"enabled": "false"}})

    result = _run(SUGGEST, project, "diff --git a/src/a.py b/src/a.py\n")

    assert result.returncode == 2
    assert "$.suggest.enabled: expected boolean" in result.stderr
    assert "LLM unavailable" not in result.stderr


def test_underscore_annotations_remain_valid(tmp_path):
    project = _project(
        tmp_path,
        {
            "_comment": "annotations are intentionally allowed",
            "judge": {"max_diff_bytes": 0, "advisory_only": False},
        },
    )

    result = _run(JUDGE, project, "not a unified diff")

    assert result.returncode == 0


def test_oversized_diff_fails_closed_instead_of_skipping(tmp_path):
    project = _project(tmp_path, {"judge": {"max_diff_bytes": 16}})
    diff = "diff --git a/a b/a\n--- a/a\n+++ b/a\n+forbidden\n"

    result = _run(JUDGE, project, diff)

    assert result.returncode == 2
    assert "exceeds judge.max_diff_bytes=16" in result.stderr
    assert "enforcement was not performed" in result.stderr
    assert "skipping" not in result.stderr


def test_diff_limit_counts_utf8_bytes(tmp_path):
    project = _project(tmp_path, {"judge": {"max_diff_bytes": 1}})

    result = _run(JUDGE, project, "é")

    assert result.returncode == 2
    assert "diff is 2 bytes" in result.stderr
