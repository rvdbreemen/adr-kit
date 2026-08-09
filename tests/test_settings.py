import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


settings = _load("adr_settings_for_test", SCRIPTS / "adr_settings.py")


def _entry(resolved: dict, key: str) -> dict:
    return next(item for item in resolved["entries"] if item["key"] == key)


def test_defaults_cover_automation_clients_and_doctor(tmp_path):
    resolved = settings.resolve_settings(
        tmp_path, global_path=tmp_path / "global.json"
    )

    assert _entry(resolved, "pre_commit.enabled") == {
        "key": "pre_commit.enabled",
        "value": True,
        "source": "default",
    }
    assert resolved["values"]["update"] == {
        "policy": "verified-stable-auto",
        "trigger": "project-setup",
        "frequency_hours": 24,
        "offline": False,
        "pinned_version": None,
    }
    assert set(resolved["values"]["clients"]) == {
        "claude",
        "codex",
        "copilot",
    }
    assert resolved["values"]["doctor"] == {
        "auto_repair": True,
        "check_only": False,
    }
    assert "judgment" not in resolved["values"], (
        "the local-judgment settings shape was retired by ADR-036"
    )


def test_project_overrides_global_and_sources_are_reported(tmp_path):
    global_path = tmp_path / "global.json"
    global_path.write_text(
        json.dumps(
            {
                "pre_commit": {"enabled": False},
                "update": {"offline": True},
            }
        ),
        encoding="utf-8",
    )
    project = tmp_path / ".adr-kit" / "settings.json"
    project.parent.mkdir()
    project.write_text(
        json.dumps({"pre_commit": {"enabled": True}}),
        encoding="utf-8",
    )

    resolved = settings.resolve_settings(tmp_path, global_path=global_path)

    assert _entry(resolved, "pre_commit.enabled")["source"] == "project"
    assert _entry(resolved, "pre_commit.enabled")["value"] is True
    assert _entry(resolved, "update.offline")["source"] == "global"
    assert _entry(resolved, "update.frequency_hours")["source"] == "default"


def test_set_and_unset_are_atomic_and_preserve_other_values(tmp_path):
    global_path = tmp_path / "global.json"

    written = settings.write_setting(
        tmp_path,
        "project",
        "clients.codex.enabled",
        False,
        global_path=global_path,
    )
    settings.write_setting(
        tmp_path,
        "project",
        "update.pinned_version",
        "0.35.0",
        global_path=global_path,
    )
    settings.write_setting(
        tmp_path,
        "project",
        "clients.codex.enabled",
        unset=True,
        global_path=global_path,
    )

    assert written == tmp_path / ".adr-kit" / "settings.json"
    assert json.loads(written.read_text(encoding="utf-8")) == {
        "update": {"pinned_version": "0.35.0"}
    }
    assert not list(written.parent.glob("*.tmp"))


def test_unknown_keys_and_invalid_documents_fail_closed(tmp_path):
    global_path = tmp_path / "global.json"
    global_path.write_text('{"future": true}', encoding="utf-8")

    try:
        settings.resolve_settings(tmp_path, global_path=global_path)
    except settings.SettingsError as exc:
        assert "unknown settings" in str(exc)
    else:
        raise AssertionError("unknown key should fail")

    global_path.write_text(
        '{"pre_commit": {"enabled": "false"}}', encoding="utf-8"
    )
    with pytest.raises(settings.SettingsError, match="must be boolean"):
        settings.resolve_settings(tmp_path, global_path=global_path)


def test_settings_cli_emits_effective_value_and_source(tmp_path):
    command = [
        sys.executable,
        str(SCRIPTS / "settings.py"),
        "--project-root",
        str(tmp_path),
        "--global-settings",
        str(tmp_path / "global.json"),
        "--format",
        "json",
        "set",
        "doctor.check_only",
        "true",
    ]

    result = subprocess.run(command, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    item = next(
        entry
        for entry in payload["entries"]
        if entry["key"] == "doctor.check_only"
    )
    assert item == {
        "key": "doctor.check_only",
        "source": "project",
        "value": True,
    }
