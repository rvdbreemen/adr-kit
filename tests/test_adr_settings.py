"""One settings surface, with provenance and the right target file (TASK-78).

The two failures this command was built for are pinned here: judge-by-default
could be switched on by a shipped writer but never off, and a personal setting
had nowhere to live that a user would find.
"""

# Gate anchor for ADR-025: adr-config-trust-boundary-v1
# Verified here: tracked configuration may select among backends; only machine-local configuration may introduce one.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS = REPO_ROOT / "bin" / "adr-settings"


def _run(adr_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SETTINGS), "--adr-dir", str(adr_dir), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )


@pytest.fixture()
def adr_dir(tmp_path: Path) -> Path:
    path = tmp_path / "docs" / "adr"
    path.mkdir(parents=True)
    return path


def _project(adr_dir: Path) -> dict:
    return json.loads((adr_dir / ".adr-kit.json").read_text(encoding="utf-8"))


def _local(adr_dir: Path) -> dict:
    return json.loads((adr_dir / ".adr-kit.local.json").read_text(encoding="utf-8"))


def test_judge_by_default_can_be_turned_off(adr_dir):
    """The gap that motivated the command: no shipped writer could write false."""
    result = _run(adr_dir, "--set", "judge.llm_enabled=false")

    assert result.returncode == 0, result.stderr
    assert _project(adr_dir)["judge"]["llm_enabled"] is False


def test_a_personal_setting_lands_in_the_gitignored_file(adr_dir):
    """A committed signer would put one name on every teammate's acceptance."""
    result = _run(adr_dir, "--set", "lifecycle.signer=User: Someone Else")

    assert result.returncode == 0, result.stderr
    assert _local(adr_dir)["lifecycle"]["signer"] == "User: Someone Else"
    assert not (adr_dir / ".adr-kit.json").exists(), "a personal setting must not touch the tracked file"


def test_a_team_setting_lands_in_the_tracked_file(adr_dir):
    result = _run(adr_dir, "--set", "guardian.drift_stale_days=3")

    assert result.returncode == 0, result.stderr
    assert _project(adr_dir)["guardian"]["drift_stale_days"] == 3
    assert not (adr_dir / ".adr-kit.local.json").exists()


def test_values_are_typed_not_stringified(adr_dir):
    """`--set x=false` must not store the truthy string 'false'."""
    _run(adr_dir, "--set", "guardian.enabled=false")
    _run(adr_dir, "--set", "judge.max_diff_bytes=4194304")
    data = _project(adr_dir)

    assert data["guardian"]["enabled"] is False
    assert data["judge"]["max_diff_bytes"] == 4194304


@pytest.mark.parametrize(
    ("assignment", "fragment"),
    [
        ("guardian.enabled=maybe", "expected a boolean"),
        ("judge.backend=hosted", "expected one of"),
        ("judge.max_diff_bytes=-5", "minimum"),
        ("judge.no_such_key=1", "unknown setting"),
    ],
)
def test_invalid_writes_are_refused_before_they_land(adr_dir, assignment, fragment):
    result = _run(adr_dir, "--set", assignment)

    assert result.returncode == 2
    assert fragment in result.stderr
    assert not (adr_dir / ".adr-kit.json").exists(), "a refused write must leave no file behind"


def test_provenance_distinguishes_project_from_default(adr_dir):
    _run(adr_dir, "--set", "judge.advisory_only=true")
    result = _run(adr_dir, "--format", "json")
    rows = {row["key"]: row for row in json.loads(result.stdout)["settings"]}

    assert rows["judge.advisory_only"]["source"] == "project"
    assert rows["judge.llm_enabled"]["source"] == "default"
    assert rows["grill.auto_start"]["value"] is True
    assert rows["grill.auto_start"]["source"] == "default"
    assert rows["lifecycle.signer"]["source"] == "unset"


def test_automatic_grilling_default_can_be_materialized_without_overriding_opt_out(adr_dir):
    default = _run(adr_dir, "--format", "json")
    rows = {row["key"]: row for row in json.loads(default.stdout)["settings"]}
    assert rows["grill.auto_start"]["value"] is True
    assert rows["grill.auto_start"]["source"] == "default"

    enabled = _run(adr_dir, "--set", "grill.auto_start=true")
    assert enabled.returncode == 0, enabled.stderr
    assert _project(adr_dir)["grill"]["auto_start"] is True

    disabled = _run(adr_dir, "--set", "grill.auto_start=false")
    assert disabled.returncode == 0, disabled.stderr
    assert _project(adr_dir)["grill"]["auto_start"] is False


def test_machine_local_beats_project_for_a_local_key(adr_dir):
    (adr_dir / ".adr-kit.local.json").write_text(
        json.dumps({"judge": {"host_client": "codex-cli"}}), encoding="utf-8"
    )
    result = _run(adr_dir, "--format", "json")
    rows = {row["key"]: row for row in json.loads(result.stdout)["settings"]}

    assert rows["judge.host_client"]["value"] == "codex-cli"
    assert rows["judge.host_client"]["source"] == "machine-local"


def test_unset_restores_the_default(adr_dir):
    _run(adr_dir, "--set", "guardian.enabled=false")
    result = _run(adr_dir, "--unset", "guardian.enabled")

    assert result.returncode == 0, result.stderr
    rows = {row["key"]: row for row in json.loads(_run(adr_dir, "--format", "json").stdout)["settings"]}
    assert rows["guardian.enabled"]["value"] is True
    assert rows["guardian.enabled"]["source"] == "default"


def test_an_env_override_is_reported_rather_than_silently_winning(adr_dir, monkeypatch):
    """A config value that is not taking effect must say why."""
    env = {**dict(__import__("os").environ), "ADR_KIT_NO_LLM": "1"}
    result = subprocess.run(
        [sys.executable, str(SETTINGS), "--adr-dir", str(adr_dir), "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=env,
    )
    rows = {row["key"]: row for row in json.loads(result.stdout)["settings"]}

    assert "ADR_KIT_NO_LLM" in rows["judge.llm_enabled"].get("env_override", "")


def test_list_names_every_settable_key(adr_dir):
    result = _run(adr_dir, "--list")

    assert result.returncode == 0
    keys = result.stdout.split()
    assert "lifecycle.signer" in keys
    assert "judge.llm_enabled" in keys
    assert "guardian.llm_stale_days" in keys
    assert "grill.auto_start" in keys
