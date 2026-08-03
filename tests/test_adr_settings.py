"""One settings surface, with provenance and the right target file (TASK-78).

The two failures this command was built for are pinned here: judge-by-default
could be switched on by a shipped writer but never off, and a personal setting
had nowhere to live that a user would find.
"""

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
    assert rows["judge.ollama_model"]["source"] == "default"
    assert rows["lifecycle.signer"]["source"] == "unset"


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


def test_a_stored_credential_is_never_printed_back(adr_dir):
    """The docstring promised this from day one; nothing implemented it.

    `adr-settings --all` rendered `judge.openai_api_key` like any other string,
    so a key stored in the gitignored local file came straight back out onto the
    terminal. The file is not the exposure -- the terminal is: scrollback,
    screenshots, and a pasted bug report all carry it. A settings screen needs to
    answer "is a credential configured?", never "what is it".
    """
    secret = "sk-do-not-print-me-4242"
    _run(adr_dir, "--set", f"judge.openai_api_key={secret}")

    text = _run(adr_dir, "--all")
    payload = _run(adr_dir, "--all", "--format", "json")

    assert secret not in text.stdout, "the text renderer echoed the credential"
    assert secret not in payload.stdout, "the JSON output echoed the credential"

    rows = {row["key"]: row for row in json.loads(payload.stdout)["settings"]}
    row = rows["judge.openai_api_key"]
    assert row["secret"] is True
    assert row["value"] == "<set>", "presence must still be reportable"
    assert row["source"] == "machine-local"
    # And it is still stored, so the judge can use it.
    assert _local(adr_dir)["judge"]["openai_api_key"] == secret


def test_an_absent_credential_reads_as_not_set(adr_dir):
    payload = _run(adr_dir, "--all", "--format", "json")

    row = {r["key"]: r for r in json.loads(payload.stdout)["settings"]}["judge.openai_api_key"]

    assert row["value"] is None
    assert row["secret"] is True


def test_the_credential_environment_variable_is_reported_as_a_boolean(adr_dir):
    """Presence is actionable; the value is not."""
    import os

    env = {**dict(os.environ), "ADR_KIT_OPENAI_API_KEY": "sk-from-the-environment"}
    result = subprocess.run(
        [sys.executable, str(SETTINGS), "--adr-dir", str(adr_dir), "--all", "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=env,
    )

    assert "sk-from-the-environment" not in result.stdout
    row = {r["key"]: r for r in json.loads(result.stdout)["settings"]}["judge.openai_api_key"]
    assert row["env_present"] is True
    assert row["env_var"] == "ADR_KIT_OPENAI_API_KEY"
