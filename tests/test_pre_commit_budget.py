"""The pre-commit template must apply the budget the config declares.

`judge.pre_commit_timeout_ms` existed in the schema and the installed hook
ignored it: the threshold was a literal 5000 in the template, so setting the key
changed nothing (TASK-121). Same shape as the JUDGE_TIMEOUT_S = 120 defect fixed
in v0.44.1 -- a bound declared in config and contradicted by a constant in code,
with nothing forcing agreement -- except this one ships to every project that
installs the hook.

These drive the actual shell block rather than asserting on its source, because
a regex over a template proves the text and not the behaviour.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "githooks" / "pre-commit"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="POSIX shell not available"
)

# The budget-resolution block, lifted out of the template and driven directly.
# It reads $ROOT/docs/adr/.adr-kit.json and prints the state, the budget it
# resolved, and whether the warning is enabled.
_HARNESS = """
set -e
_PYTHON3=$(command -v python3 || command -v python)
ROOT="."
{block}
printf '%s %s %s\n' "$_BUDGET_STATE" "$_BUDGET_MS" "$_WARN_ON_EXCEED"
"""


def _budget_block() -> str:
    # Newlines normalised: .gitattributes declares this file LF, but a Windows
    # working copy holds CRLF and bash reports `$'\r': command not found` on
    # every line. The installed hook is written LF by the installer.
    text = TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")
    start = text.index("_ADR_KIT_MAX_BUDGET_MS=")
    end = text.index("# Run the judge.", start)
    return text[start:end]


def _run_block(tmp_path: Path) -> tuple[str, str, str]:
    """Run the template's budget block with tmp_path as the working directory.

    Everything is relative on purpose. Handing bash a native Windows path gets
    the backslashes eaten; handing it a /c/... path assumes a drive mount that
    the Git `usr/bin/bash` does not have. Interpreter comes from PATH inside the
    shell for the same reason.
    """
    script = tmp_path / "probe.sh"
    # Bytes with explicit LF: text mode would write CRLF on Windows, and bash
    # rejects every line of a script whose endings it did not expect.
    script.write_bytes(_HARNESS.format(block=_budget_block()).encode("utf-8"))
    result = subprocess.run(
        ["bash", "probe.sh"],
        cwd=str(tmp_path),
        capture_output=True,
        timeout=60,
    )
    stderr = result.stderr.decode("utf-8", "replace")
    assert result.returncode == 0, stderr
    state, budget, warn = result.stdout.decode("utf-8").strip().split()
    return state, budget, warn


def _resolve(tmp_path: Path, judge_config: object | None) -> tuple[str, str, str]:
    """Run the template's budget block against one .adr-kit.json and read it back."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    if judge_config is not None:
        (adr_dir / ".adr-kit.json").write_text(
            json.dumps({"judge": judge_config}), encoding="utf-8"
        )
    return _run_block(tmp_path)


def test_a_configured_budget_is_the_one_applied(tmp_path):
    """AC#1's real assertion: the observed threshold is the configured number."""
    assert _resolve(tmp_path, {"pre_commit_timeout_ms": 12345}) == ("ok", "12345", "1")


def test_an_absent_key_falls_back_to_the_documented_default(tmp_path):
    state, budget, _ = _resolve(tmp_path, None)
    assert (state, budget) == ("absent", "5000")


def test_zero_disables_the_warning_the_way_the_judge_reads_it(tmp_path):
    """bin/adr-judge treats 0 as off; the shell must not invent a second meaning."""
    state, budget, _ = _resolve(tmp_path, {"pre_commit_timeout_ms": 0})
    assert (state, budget) == ("ok", "0")


@pytest.mark.parametrize("value", [-1, 3600001, "5000", True, 1.5], ids=str)
def test_a_value_outside_the_sane_range_is_refused_not_adopted(tmp_path, value):
    """AC#2. A hand-edited repo-tracked file gets validated, not trusted.

    `True` is in the list on purpose: bool is a subclass of int in Python, so a
    naive isinstance check would silently accept `true` as 1 ms.
    """
    state, budget, _ = _resolve(tmp_path, {"pre_commit_timeout_ms": value})
    assert state == "invalid"
    assert budget == "5000"


def test_warn_on_exceed_false_turns_the_warning_off(tmp_path):
    """Shipping the budget read without this reproduces the same defect one key over."""
    _, _, warn = _resolve(
        tmp_path, {"pre_commit_timeout_ms": 9000, "warn_on_exceed": False}
    )
    assert warn == "0"


def test_a_broken_config_falls_back_rather_than_aborting_the_commit(tmp_path):
    """set -e is live at this point; an unguarded read would abort mid-commit."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text("{ not json", encoding="utf-8")
    state, budget, _ = _run_block(tmp_path)
    assert (state, budget) == ("absent", "5000")


def test_the_template_no_longer_hardcodes_the_threshold():
    """The literal is what made the config key inert."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "-gt 5000" not in text, "the hardcoded 5000 ms threshold is back"
    assert "threshold: 5000ms" not in text


def test_the_suggest_pass_is_bounded_by_the_same_budget():
    """TASK-122: the advisory pass must not outlast what the hook declares.

    bin/adr-suggest defaulted to 120 s on a path documented as never blocking,
    and no caller ever passed --llm-timeout, so 120 s is what every commit got.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "--llm-timeout" in text, "the suggest pass runs unbounded again"
    assert "_SUGGEST_TIMEOUT_S" in text

    suggest = (ROOT / "bin" / "adr-suggest").read_text(encoding="utf-8")
    assert "DEFAULT_LLM_TIMEOUT_S = 30" in suggest, (
        "the suggest default is no longer a wait a person will sit through"
    )
