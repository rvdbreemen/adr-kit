"""Gate adr-no-pinned-model-v1 (ADR-043).

ADR-043 carries the two rules ADR-017 enforced before it was superseded: no
entry point pins a vendor model, and none carries its own default command
vector. ADR-017's scope was a hand-kept list of files, and `bin/adr-substance`
grew a model call outside it. So the gate checks the scope against the code:
every file that resolves an LLM backend must be inside the rule's `path_glob`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_adr_judge_llm import _load_judge_module  # noqa: E402

GATE_ADR_NO_PINNED_MODEL_V1 = "adr-no-pinned-model-v1"
ADR_PATH = next((REPO_ROOT / "docs" / "adr").glob("ADR-043-*.md"))
CLIENT_ROOTS = ("bin", "codex/bin", "copilot/bin")


def _rules() -> list:
    judge = _load_judge_module()
    enforcement = judge.parse_enforcement(ADR_PATH.read_text(encoding="utf-8"), ADR_PATH)
    assert enforcement is not None, "ADR-043 must carry an Enforcement block"
    return enforcement["forbid_pattern"]


def _model_callers() -> list[str]:
    """Every shipped file that resolves an LLM backend, as a repo-relative path."""
    found = []
    for root in CLIENT_ROOTS:
        for path in sorted((REPO_ROOT / root).iterdir()):
            if not path.is_file() or path.suffix not in ("", ".py"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "resolve_llm_backend" in text:
                found.append(path.relative_to(REPO_ROOT).as_posix())
    return found


def test_gate_names_this_adr():
    text = ADR_PATH.read_text(encoding="utf-8")
    assert f'gate: "{GATE_ADR_NO_PINNED_MODEL_V1}"' in text


def test_every_model_calling_entry_point_is_in_scope():
    judge = _load_judge_module()
    callers = _model_callers()
    assert any(c.endswith("adr-substance") for c in callers), "fixture sanity: adr-substance calls a model"
    for rule in _rules():
        outside = [c for c in callers if not judge.path_matches(c, rule["path_glob"])]
        assert not outside, (
            f"model-calling files outside ADR-043's scope {rule['path_glob']!r}: {outside}. "
            "Add them to the path_glob in the same change."
        )


def test_no_file_in_scope_breaks_either_rule_today():
    judge = _load_judge_module()
    for rule in _rules():
        pattern = re.compile(rule["pattern"])
        for caller in _model_callers():
            if judge.path_matches(caller, rule["path_glob"]):
                text = (REPO_ROOT / caller).read_text(encoding="utf-8", errors="replace")
                assert not pattern.search(text), f"{caller} matches {rule['pattern']!r}"


def test_the_patterns_catch_the_shapes_they_were_written_for():
    pinned, default_cmd = (re.compile(rule["pattern"]) for rule in _rules())
    assert pinned.search('cmd = ["claude", "-p", "--model", "claude-sonnet-4-6"]')
    assert pinned.search("claude -p --model=claude-opus")
    assert default_cmd.search('DEFAULT_LLM_CMD = "claude -p"')
    assert not pinned.search('HOST_COMMANDS = {"claude-code-cli": ["claude", "-p"]}')
