"""Turning an LLM layer off is a machine choice, not a team one (TASK-233).

The maintainer decided that an "off" answer at init or upgrade applies to this
machine only: it goes to the gitignored .adr-kit.local.json, so one developer's
answer does not switch the LLM layers off for the whole team (ADR-025: a
personal choice is a machine fact). These tests hold every reader to that.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import adr_config  # noqa: E402

from test_adr_substance import _adr_dir, _fake_cli  # noqa: E402
from test_llm_kill_switch import CODE_DIFF  # noqa: E402


def _local(adr_dir: Path, document: dict) -> None:
    (adr_dir / ".adr-kit.local.json").write_text(json.dumps(document), encoding="utf-8")


def _env(fake: str) -> dict:
    env = dict(os.environ)
    for name in ("ADR_KIT_NO_LLM", "ADR_KIT_SUGGEST_DISABLE", "ADR_KIT_SUGGEST"):
        env.pop(name, None)
    env["ADR_KIT_LLM_CMD"] = fake
    return env


def test_machine_values_override_the_project_for_the_llm_switches_only():
    project = {"judge": {"llm_enabled": True, "llm_timeout_seconds": 90}, "suggest": {"enabled": True}}
    local = {
        "judge": {"llm_enabled": False, "llm_timeout_seconds": 5, "host_client": "codex-cli"},
        "suggest": {"enabled": False},
        "guardian": {"llm_enabled": False, "llm_autorun": True},
    }
    merged = adr_config.apply_machine_overrides(project, local)
    assert merged["judge"]["llm_enabled"] is False
    assert merged["suggest"]["enabled"] is False
    assert merged["guardian"] == {"llm_enabled": False, "llm_autorun": True}
    # Only the listed switches cross over; a machine file cannot retune the team.
    assert merged["judge"]["llm_timeout_seconds"] == 90
    assert project["judge"]["llm_enabled"] is True, "the input is not mutated"


def test_a_non_boolean_machine_value_is_ignored():
    merged = adr_config.apply_machine_overrides({}, {"judge": {"llm_enabled": "no"}})
    assert "llm_enabled" not in (merged.get("judge") or {})


def test_adr_judge_reports_the_machine_value_with_its_provenance(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    _local(adr_dir, {"judge": {"llm_enabled": False}})
    out = subprocess.run(
        [sys.executable, str(BIN / "adr-judge"), "--adr-dir", str(adr_dir), "--show-config", "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    report = json.loads(out.stdout)
    entry = next(e for e in report["entries"] if e["key"] == "judge.llm_enabled")
    assert entry["value"] is False
    assert entry["source"] == "machine-local"


def test_adr_suggest_skips_when_this_machine_switched_it_off(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    fake = _fake_cli(tmp_path, {"suggest": False})
    _local(adr_dir, {"suggest": {"enabled": False}})
    subprocess.run(
        [sys.executable, str(BIN / "adr-suggest"), "--diff", "-", "--adr-dir", str(adr_dir)],
        input=CODE_DIFF, capture_output=True, text=True, encoding="utf-8",
        env=_env(fake), timeout=60,
    )
    assert not (tmp_path / "prompts.txt").exists()


def test_adr_substance_skips_when_this_machine_switched_the_guardian_tier_off(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    fake = _fake_cli(tmp_path, {"findings": []})
    _local(adr_dir, {"guardian": {"llm_enabled": False}})
    result = subprocess.run(
        [sys.executable, str(BIN / "adr-substance"), "--adr-dir", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL, env=_env(fake), timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "prompts.txt").exists()


def test_adr_settings_writes_a_machine_override_to_the_local_file(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, str(BIN / "adr-settings"), "--adr-dir", str(adr_dir),
         "--set", "judge.llm_enabled=false", "--local"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == 0, result.stderr
    local = json.loads((adr_dir / ".adr-kit.local.json").read_text(encoding="utf-8"))
    assert local["judge"]["llm_enabled"] is False
    assert not (adr_dir / ".adr-kit.json").exists(), "the team file is untouched"


def test_the_guardian_llm_tier_is_never_due_when_switched_off():
    import importlib.machinery
    import importlib.util
    from datetime import datetime, timezone

    loader = importlib.machinery.SourceFileLoader("adr_guardian_mod", str(BIN / "adr-guardian"))
    spec = importlib.util.spec_from_loader("adr_guardian_mod", loader)
    guardian = importlib.util.module_from_spec(spec)
    loader.exec_module(guardian)
    now = datetime.now(timezone.utc)
    on = guardian._guardian_config({})
    off = guardian._guardian_config({"guardian": {"llm_enabled": False}})
    assert guardian._compute_due_tiers({}, on, now)[1] is True, "control: a never-run tier is due"
    assert guardian._compute_due_tiers({}, off, now)[1] is False
