"""Tests for bin/adr-guardian copied-artifact staleness detection (task-15).

Invariants under test:
  - A git pre-commit wrapper stamped with an older version than the plugin is
    reported stale; one stamped with the current version is not (AC#3: no
    false positives when up to date).
  - An adr-kit wrapper WITHOUT a stamp (pre-0.27 install) is reported stale.
  - A pre-commit hook that is not adr-kit's is never reported.
  - A settings guardian entry stamped older is stale; an unstamped entry is
    reported present but never stale (it self-resolves engines).
  - The `artifacts` subcommand always exits 0 and supports --format json.
  - The check nudge block includes the wrapper line for a stale wrapper and
    counts it as a due item.
  - The template stamps (pre-commit wrapper, guardian entry) match the
    plugin.json version, so a fresh install is never reported stale and a
    release bump cannot silently skip the stamps.

Import strategy: SourceFileLoader, same pattern as test_adr_guardian_state.py.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_GUARDIAN = REPO_ROOT / "bin" / "adr-guardian"
PRECOMMIT_TEMPLATE = REPO_ROOT / "templates" / "githooks" / "pre-commit"
GUARDIAN_ENTRY_TEMPLATE = REPO_ROOT / "templates" / "cc-settings" / "guardian-hook-entry.json"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"


def _load_module():
    loader = importlib.machinery.SourceFileLoader(
        "adr_guardian_artifacts_mod", str(ADR_GUARDIAN)
    )
    spec = importlib.util.spec_from_loader("adr_guardian_artifacts_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def guardian():
    return _load_module()


@pytest.fixture(scope="module")
def plugin_version() -> str:
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]


def _run(args: list, cwd: Path) -> "subprocess.CompletedProcess":
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    env.pop("CURSOR_PLUGIN_ROOT", None)
    return subprocess.run(
        [sys.executable, str(ADR_GUARDIAN)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
        env=env,
    )


ADR_BODY = "# ADR-001 Test\n\n## Status\n\nAccepted\n\n## Decision\n\nYes.\n"


def _make_project(tmp_path: Path, wrapper: str = None, settings: str = None) -> Path:
    root = tmp_path / "proj"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "ADR-001-test.md").write_text(ADR_BODY, encoding="utf-8")
    if wrapper is not None:
        hooks = root / ".githooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text(wrapper, encoding="utf-8")
    if settings is not None:
        cc = root / ".claude"
        cc.mkdir()
        (cc / "settings.json").write_text(settings, encoding="utf-8")
    return root


def _adr_kit_wrapper(version: str = None) -> str:
    stamp = f'ADR_KIT_WRAPPER_VERSION="{version}"\n' if version else ""
    return (
        "#!/usr/bin/env bash\n"
        "# adr-kit pre-commit hook (template)\n"
        f"{stamp}"
        "echo adr-judge would run here\n"
    )


def _settings_with_entry(version: str = None) -> str:
    entry = {
        "type": "command",
        "command": "python adr-guardian check",
        "_remove_marker": "adr-guardian-session-start",
    }
    if version is not None:
        entry["_wrapper_version"] = version
    return json.dumps(
        {"hooks": {"SessionStart": [{"hooks": [entry]}]}}, indent=2
    )


# ---------------------------------------------------------------------------
# _artifact_report unit level
# ---------------------------------------------------------------------------

def test_stale_stamped_wrapper_reported(guardian, tmp_path):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper("0.18.0"))
    report = guardian._artifact_report(root)
    wrappers = [a for a in report["artifacts"] if a["kind"] == "git-pre-commit-wrapper"]
    assert len(wrappers) == 1
    assert wrappers[0]["version"] == "0.18.0"
    assert wrappers[0]["stale"] is True


def test_current_version_wrapper_not_stale(guardian, tmp_path, plugin_version):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper(plugin_version))
    report = guardian._artifact_report(root)
    wrappers = [a for a in report["artifacts"] if a["kind"] == "git-pre-commit-wrapper"]
    assert len(wrappers) == 1
    assert wrappers[0]["stale"] is False


def test_unstamped_adr_kit_wrapper_is_stale(guardian, tmp_path):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper(None))
    report = guardian._artifact_report(root)
    wrappers = [a for a in report["artifacts"] if a["kind"] == "git-pre-commit-wrapper"]
    assert len(wrappers) == 1
    assert wrappers[0]["version"] is None
    assert wrappers[0]["stale"] is True


def test_foreign_pre_commit_hook_ignored(guardian, tmp_path):
    root = _make_project(
        tmp_path, wrapper="#!/bin/sh\nnpx lint-staged\n"
    )
    report = guardian._artifact_report(root)
    assert report["artifacts"] == []


def test_no_artifacts_no_findings(guardian, tmp_path):
    root = _make_project(tmp_path)
    report = guardian._artifact_report(root)
    assert report["artifacts"] == []


def test_settings_entry_stamped_old_is_stale(guardian, tmp_path):
    root = _make_project(tmp_path, settings=_settings_with_entry("0.18.0"))
    report = guardian._artifact_report(root)
    entries = [a for a in report["artifacts"] if a["kind"] == "settings-guardian-entry"]
    assert len(entries) == 1
    assert entries[0]["stale"] is True


def test_settings_entry_current_not_stale(guardian, tmp_path, plugin_version):
    root = _make_project(tmp_path, settings=_settings_with_entry(plugin_version))
    report = guardian._artifact_report(root)
    entries = [a for a in report["artifacts"] if a["kind"] == "settings-guardian-entry"]
    assert len(entries) == 1
    assert entries[0]["stale"] is False


def test_settings_entry_unstamped_present_but_not_stale(guardian, tmp_path):
    root = _make_project(tmp_path, settings=_settings_with_entry(None))
    report = guardian._artifact_report(root)
    entries = [a for a in report["artifacts"] if a["kind"] == "settings-guardian-entry"]
    assert len(entries) == 1
    assert entries[0]["stale"] is False


def test_corrupt_settings_ignored(guardian, tmp_path):
    root = _make_project(tmp_path, settings="{not json, but mentions adr-guardian")
    report = guardian._artifact_report(root)
    assert report["artifacts"] == []


# ---------------------------------------------------------------------------
# artifacts subcommand (CLI)
# ---------------------------------------------------------------------------

def test_artifacts_cli_json(tmp_path, plugin_version):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper("0.18.0"))
    proc = _run(["artifacts", "--project-root", str(root), "--format", "json"], cwd=root)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["plugin_version"] == plugin_version
    assert any(a["stale"] for a in report["artifacts"])


def test_artifacts_cli_human_clean(tmp_path, plugin_version):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper(plugin_version))
    proc = _run(["artifacts", "--project-root", str(root)], cwd=root)
    assert proc.returncode == 0
    assert "STALE" not in proc.stdout
    assert "/adr-kit:upgrade" not in proc.stdout


def test_artifacts_cli_always_exit_zero_outside_project(tmp_path):
    proc = _run(["artifacts", "--project-root", str(tmp_path)], cwd=tmp_path)
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# check integration: stale wrapper rides the nudge block
# ---------------------------------------------------------------------------

def test_check_nudge_includes_stale_wrapper(tmp_path):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper("0.18.0"))
    proc = _run(["check"], cwd=root)
    assert proc.returncode == 0
    assert "wrapper:" in proc.stdout
    assert "0.18.0" in proc.stdout
    assert "/adr-kit:upgrade" in proc.stdout


def test_check_silent_when_fresh_and_no_tier_due(tmp_path, plugin_version, guardian):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper(plugin_version))
    # Stamp both tiers as just-run so neither is due; with a fresh wrapper
    # the check must stay silent (AC#3).
    now = guardian._now_utc().isoformat()
    state = {
        "cheap_tier": {"last_run": now},
        "llm_tier": {"last_run": now},
        "last_nudged": None,
    }
    (root / "docs" / "adr" / ".adr-kit-state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    proc = _run(["check"], cwd=root)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_check_fires_on_stale_wrapper_even_when_tiers_fresh(tmp_path, guardian):
    root = _make_project(tmp_path, wrapper=_adr_kit_wrapper("0.18.0"))
    now = guardian._now_utc().isoformat()
    state = {
        "cheap_tier": {"last_run": now},
        "llm_tier": {"last_run": now},
        "last_nudged": None,
    }
    (root / "docs" / "adr" / ".adr-kit-state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    proc = _run(["check"], cwd=root)
    assert proc.returncode == 0
    assert "wrapper:" in proc.stdout
    assert "1 item(s) due" in proc.stdout


# ---------------------------------------------------------------------------
# Template stamps stay in lockstep with the release
# ---------------------------------------------------------------------------

def test_precommit_template_stamp_matches_plugin_version(plugin_version):
    content = PRECOMMIT_TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'^ADR_KIT_WRAPPER_VERSION="([0-9.]+)"', content, re.MULTILINE)
    assert m, "pre-commit template lost its ADR_KIT_WRAPPER_VERSION stamp"
    assert m.group(1) == plugin_version


def test_guardian_entry_template_stamp_matches_plugin_version(plugin_version):
    data = json.loads(GUARDIAN_ENTRY_TEMPLATE.read_text(encoding="utf-8"))
    assert data.get("_wrapper_version") == plugin_version


def test_guide_template_version_line_matches_plugin_version(plugin_version):
    guide = REPO_ROOT / "templates" / "adr-kit-guide.md"
    first_line = guide.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == f"<!-- adr-kit-guide v{plugin_version} -->"
