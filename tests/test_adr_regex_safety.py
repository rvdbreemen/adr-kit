"""Regression tests for killable repository-authored enforcement regexes."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
JUDGE = ROOT / "bin" / "adr-judge"


def _project(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-regex-budget.md").write_text(
        textwrap.dedent(
            """\
            # ADR-001 Regex Budget

            ## Status

            Accepted, 2026-07-18.

            ## Decision

            Reject unsafe content.

            ## Enforcement

            ```json
            {
              "forbid_pattern": [
                {
                  "pattern": "(a+)+$",
                  "message": "Catastrophic policy pattern."
                }
              ]
            }
            ```
            """
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_judge_kills_catastrophic_policy_regex_and_fails_closed(tmp_path):
    project = _project(tmp_path)
    diff = textwrap.dedent(
        f"""\
        diff --git a/src/value.txt b/src/value.txt
        --- a/src/value.txt
        +++ b/src/value.txt
        @@ -0,0 +1 @@
        +{'a' * 30}!
        """
    )

    started = time.perf_counter()
    result = subprocess.run(
        [
            sys.executable,
            str(JUDGE),
            "--diff",
            "-",
            "--adr-dir",
            str(project / "docs" / "adr"),
            "--repo-root",
            str(project),
            "--json",
        ],
        input=diff,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=4,
        check=False,
    )
    elapsed = time.perf_counter() - started

    assert result.returncode == 1
    assert elapsed < 3
    payload = json.loads(result.stdout)
    assert payload["summary"]["violations"] == 1
    finding = payload["findings"][0]
    assert finding["severity"] == "violation"
    assert "failed closed" in finding["message"]


def test_regex_worker_restarts_after_timeout():
    sys.path.insert(0, str(ROOT / "bin"))
    from adr_regex import RegexEvaluator, RegexTimeoutError

    evaluator = RegexEvaluator(timeout_seconds=0.5)
    try:
        try:
            evaluator.search("(a+)+$", ("a" * 30) + "!")
        except RegexTimeoutError:
            pass
        else:
            raise AssertionError("catastrophic regex unexpectedly completed")
        assert evaluator.search("safe", "safe value") is True
    finally:
        evaluator.close()
