"""Tests for detected-client installation and client contract separation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "install-agent-envs.py"
SYNC = ROOT / "scripts" / "sync-agent-plugins.py"

spec = importlib.util.spec_from_file_location("install_agent_envs", SCRIPT)
installer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = installer
spec.loader.exec_module(installer)


def completed(command, stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def test_detects_only_verified_cli_executables(tmp_path: Path):
    executables = {}
    versions = {
        "claude": "2.1.214 (Claude Code)",
        "codex": "codex-cli 0.144.5",
        "copilot": "GitHub Copilot CLI 1.0.70.",
    }
    for name in installer.SUPPORTED:
        path = tmp_path / "bin with spaces" / f"{name}.exe"
        path.parent.mkdir(exist_ok=True)
        path.touch()
        executables[name] = str(path)

    def runner(command):
        name = Path(command[0]).stem
        return completed(command, versions[name])

    detected = installer.detect_clients(
        which=lambda name: executables.get(name),
        runner=runner,
    )
    assert set(detected) == set(installer.SUPPORTED)
    assert "bin with spaces" in detected["codex"].executable


def test_rejects_unrelated_binary_with_same_name(tmp_path: Path):
    fake = tmp_path / "copilot.exe"
    fake.touch()
    detected = installer.detect_client(
        "copilot",
        which=lambda _: str(fake),
        runner=lambda command: completed(command, "gh copilot extension 1.0"),
    )
    assert detected is None


def test_auto_selects_every_detected_client():
    clients = {
        name: installer.Client(name, f"/bin/{name}", "test")
        for name in installer.SUPPORTED
    }
    assert installer.parse_selection("auto", clients) == list(installer.SUPPORTED)


def test_explicit_missing_client_fails():
    with pytest.raises(ValueError, match="not detected"):
        installer.parse_selection(
            "codex,copilot",
            {"codex": installer.Client("codex", "/bin/codex", "test")},
        )


def test_dry_run_is_repeatable_and_does_not_execute_install(tmp_path: Path, capsys):
    source = tmp_path / "source with spaces"
    (source / "codex" / ".codex-plugin").mkdir(parents=True)
    (source / "codex" / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"version": "1.0.0"}), encoding="utf-8"
    )
    client = installer.Client("codex", "C:/Tools/Codex/codex.exe", "codex-cli 1")
    calls = []

    def runner(command):
        calls.append(list(command))
        if "marketplace" in command:
            return completed(
                command,
                json.dumps(
                    {
                        "marketplaces": [
                            {"name": installer.MARKETPLACES["codex"]}
                        ]
                    }
                ),
            )
        return completed(command, json.dumps({"installed": []}))

    installer.install_codex(client, source, True, runner)
    installer.install_codex(client, source, True, runner)
    assert all("plugin add" not in " ".join(call) for call in calls)
    output = capsys.readouterr().out
    assert output.count("plugin add") == 2
    assert "source with spaces" not in output  # marketplace already registered


def test_post_install_validation_requires_plugin_and_mcp():
    client = installer.Client("codex", "/bin/codex", "codex-cli")

    def runner(command):
        if "mcp" in command:
            return completed(command, "adr-kit enabled")
        return completed(
            command,
            json.dumps(
                {"installed": [{"pluginId": "adr-kit@rvdbreemen-adr-kit-codex"}]}
            ),
        )

    installer.validate_install("codex", client, runner)

    with pytest.raises(RuntimeError, match="MCP"):
        installer.validate_install(
            "codex",
            client,
            lambda command: (
                completed(command, "missing")
                if "mcp" in command
                else runner(command)
            ),
        )


def test_installed_clients_use_update_or_noop_paths(tmp_path: Path, capsys):
    source = tmp_path / "repo"
    source.mkdir()
    claude = installer.Client("claude", "/bin/claude", "Claude Code")
    copilot = installer.Client("copilot", "/bin/copilot", "GitHub Copilot CLI")

    def runner(command):
        joined = " ".join(command)
        if "marketplace list" in joined:
            if command[0] == copilot.executable:
                return completed(command, installer.MARKETPLACES["copilot"])
            return completed(
                command,
                json.dumps([{"name": installer.MARKETPLACES["claude"]}]),
            )
        if command[0] == claude.executable:
            return completed(
                command,
                json.dumps([{"id": "adr-kit@rvdbreemen-adr-kit"}]),
            )
        return completed(command, "adr-kit 0.32.0 enabled")

    installer.install_claude(claude, source, True, runner)
    installer.install_copilot(copilot, source, True, runner)
    output = capsys.readouterr().out
    assert "plugin update adr-kit@rvdbreemen-adr-kit" in output
    assert "plugin update adr-kit" in output


def test_codex_payload_is_synced():
    proc = subprocess.run(
        [sys.executable, str(SYNC), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_claude_and_codex_manifests_are_separate_and_versioned_together():
    claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((ROOT / "codex" / ".codex-plugin" / "plugin.json").read_text())
    assert claude["version"] == codex["version"]
    assert "hooks" in claude
    assert "hooks" not in codex
    assert codex["skills"] == "./skills/"
    assert codex["mcpServers"] == "./.mcp.json"
    assert "CLAUDE_PLUGIN_ROOT" in json.dumps(claude["hooks"])
    assert "codex" not in json.dumps(claude["hooks"]).lower()


def test_copilot_has_a_native_manifest_and_mcp_contract():
    manifest = json.loads((ROOT / "copilot" / "plugin.json").read_text())
    assert manifest["name"] == "adr-kit"
    assert manifest["skills"] == "skills/"
    assert manifest["mcpServers"] == ".mcp.json"
    assert not (ROOT / "copilot" / ".claude-plugin").exists()


def test_codex_marketplace_points_only_to_codex_distribution():
    marketplace = json.loads(
        (ROOT / ".agents" / "plugins" / "marketplace.json").read_text()
    )
    entry = marketplace["plugins"][0]
    assert entry["name"] == "adr-kit"
    assert entry["source"] == {"source": "local", "path": "./codex"}


def test_copilot_marketplace_points_only_to_copilot_distribution():
    marketplace = json.loads(
        (ROOT / ".github" / "plugin" / "marketplace.json").read_text()
    )
    entry = marketplace["plugins"][0]
    assert marketplace["name"] == "rvdbreemen-adr-kit-copilot"
    assert entry["source"] == "copilot"
