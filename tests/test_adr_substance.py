"""adr-substance: the LLM tier reads whether a written section says anything (TASK-203).

No real model is called: a fake host CLI returns a canned answer, which is
what lets these tests pin the parts adr-kit owns -- what is sent, what is
kept, and that nothing becomes a gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"
SUBSTANCE = BIN / "adr-substance"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_adr_readiness import _write_adr  # noqa: E402


def _fake_cli(tmp_path: Path, answer: dict) -> str:
    """A host CLI that records its prompt and prints `answer`."""
    script = tmp_path / "fake_llm.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import sys
            prompt = sys.stdin.buffer.read().decode("utf-8")
            with open({str(tmp_path / 'prompts.txt')!r}, "a", encoding="utf-8") as f:
                f.write(prompt + "\\n=====\\n")
            sys.stdout.write({json.dumps(json.dumps(answer))})
            """
        ),
        encoding="utf-8",
    )
    return f'"{sys.executable}" "{script}"'


def _run(adr_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SUBSTANCE), "--adr-dir", str(adr_dir), *args],
        capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
    )


def _adr_dir(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("## Consequences\n", "## Consequences\n\nTBD, see above.\n\n", 1),
        encoding="utf-8",
    )
    _write_adr(adr_dir, 2, status="Accepted")
    return adr_dir


def test_estimate_counts_one_call_per_proposed_adr_and_calls_nothing(tmp_path):
    adr_dir = _adr_dir(tmp_path)

    result = _run(adr_dir, "--estimate", "--llm-cmd", _fake_cli(tmp_path, {"findings": []}))

    assert result.returncode == 0, result.stderr
    assert "1 model call(s)" in result.stdout
    assert not (tmp_path / "prompts.txt").exists()


def test_a_vacuous_section_is_named_with_the_words_the_author_wrote(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    answer = {"findings": [
        {"heading": "Consequences", "quote": "TBD, see above.", "reason": "Defers."}
    ]}

    result = _run(adr_dir, "--json", "--llm-cmd", _fake_cli(tmp_path, answer))

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["checked"] == ["ADR-001"]
    assert report["findings"] == [
        {"adr": "ADR-001", "heading": "Consequences", "quote": "TBD, see above.",
         "reason": "Defers."}
    ]
    prompt = (tmp_path / "prompts.txt").read_text(encoding="utf-8")
    assert "ADR-KIT-DATA-" in prompt, "ADR text must be fenced as untrusted data"
    assert "ADR-002" not in prompt, "only Proposed ADRs are read"


def test_a_quote_that_is_not_in_the_section_is_dropped(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    answer = {"findings": [
        {"heading": "Consequences", "quote": "words nobody wrote", "reason": "x"},
        {"heading": "No Such Heading", "quote": "TBD", "reason": "x"},
    ]}

    report = json.loads(
        _run(adr_dir, "--json", "--llm-cmd", _fake_cli(tmp_path, answer)).stdout
    )

    assert report["findings"] == []
    assert report["checked"] == ["ADR-001"]


def test_an_unusable_answer_degrades_and_still_exits_zero(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    script = tmp_path / "junk.py"
    script.write_text("import sys; sys.stdin.read(); print('I cannot help')\n", encoding="utf-8")

    result = _run(adr_dir, "--json", "--llm-cmd", f'"{sys.executable}" "{script}"')

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["unanswered"] == ["ADR-001"]
    assert report["degraded"]


def test_findings_never_reach_lint_or_readiness(tmp_path):
    """AC#2 and AC#3: readiness stays deterministic and key-free, lint exits 0."""
    adr_dir = _adr_dir(tmp_path)
    readiness = (BIN / "adr_readiness.py").read_text(encoding="utf-8")
    assert "adr_llm" not in readiness and "adr-substance" not in readiness
    mcp = (BIN / "adr-mcp").read_text(encoding="utf-8")
    assert "adr-substance" not in mcp

    lint = subprocess.run(
        [sys.executable, str(BIN / "adr-lint"), str(adr_dir / "ADR-001-decision-1.md")],
        capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
    )
    assert lint.returncode == 0, lint.stdout


def test_a_bad_config_is_exit_2(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    (adr_dir / ".adr-kit.json").write_text("{not json", encoding="utf-8")

    assert _run(adr_dir, "--estimate").returncode == 2
