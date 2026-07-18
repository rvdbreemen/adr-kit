"""Tests for detected-client installation and client contract separation."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
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
                            {
                                "name": installer.MARKETPLACES["codex"],
                                "root": str(source),
                            }
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


@pytest.mark.parametrize(
    ("system", "env", "expected"),
    [
        (
            "Windows",
            {"LOCALAPPDATA": "C:/Users/test/AppData/Local"},
            Path("C:/Users/test/AppData/Local/adr-kit/marketplaces"),
        ),
        (
            "Darwin",
            {},
            Path("/Users/test/Library/Application Support/adr-kit/marketplaces"),
        ),
        (
            "Linux",
            {"XDG_DATA_HOME": "/home/test/.data"},
            Path("/home/test/.data/adr-kit/marketplaces"),
        ),
    ],
)
def test_platform_install_roots(system, env, expected):
    home = Path("C:/Users/test") if system == "Windows" else Path("/Users/test")
    if system == "Linux":
        home = Path("/home/test")
    assert installer.default_install_root(
        system=system,
        env=env,
        home=home,
    ) == expected


def test_python_runtime_probe_accepts_spaces_and_rejects_old_versions():
    executable = "C:/Program Files/Python/python.exe"

    accepted = installer.validate_python(
        executable,
        lambda command: completed(
            command,
            json.dumps(
                {
                    "version": [3, 12, 4],
                    "executable": executable,
                }
            ),
        ),
    )
    assert "Program Files" in accepted

    with pytest.raises(RuntimeError, match=r"Python 3\.10\+ is required"):
        installer.validate_python(
            executable,
            lambda command: completed(
                command,
                json.dumps(
                    {
                        "version": [3, 9, 19],
                        "executable": executable,
                    }
                ),
            ),
        )


def test_detection_isolates_timeout_and_os_errors(tmp_path):
    executables = {
        name: str(tmp_path / f"{name}.exe")
        for name in installer.SUPPORTED
    }

    def runner(command):
        name = Path(command[0]).stem
        if name == "claude":
            raise subprocess.TimeoutExpired(command, 10)
        if name == "codex":
            raise OSError("cannot execute")
        return completed(command, "GitHub Copilot CLI 1.0.70")

    detected = installer.detect_clients(
        which=lambda name: executables[name],
        runner=runner,
    )
    assert list(detected) == ["copilot"]


def test_command_rendering_quotes_paths_for_windows_and_posix():
    command = ["/path with spaces/python", "script.py", "value with spaces"]
    windows = installer._display_command(command, system="Windows")
    posix = installer._display_command(command, system="Linux")
    assert '"/path with spaces/python"' in windows
    assert "'/path with spaces/python'" in posix
    assert "'value with spaces'" in posix


def test_marketplace_source_matching_is_separator_and_case_tolerant(tmp_path):
    source = tmp_path / "Prepared Source"
    payload = {"root": str(source).upper().replace("\\", "/")}
    assert installer.marketplace_source_matches(payload, source)
    assert not installer.marketplace_source_matches(
        {"root": str(tmp_path / "another")},
        source,
    )
    source.mkdir()
    (source / installer.PREPARED_MARKER).write_text("{}\n", encoding="utf-8")
    assert installer.claude_marketplace_source_matches(
        {"name": "rvdbreemen-adr-kit", "source": "directory"},
        source,
    )


def test_prepared_source_embeds_runtime_and_passes_real_mcp_smoke(tmp_path):
    version = installer.validate_source(ROOT)
    prepared = installer.prepare_install_source(
        ROOT,
        version=version,
        python_executable=str(Path(sys.executable).resolve()),
        install_root=tmp_path / "platform data with spaces",
        dry_run=False,
        system="Darwin" if os.name != "nt" else "Windows",
    )

    for client in ("codex", "copilot"):
        config = json.loads((prepared / client / ".mcp.json").read_text())
        assert config["mcpServers"]["adr-kit"]["command"] == str(
            Path(sys.executable).resolve()
        )
    assert (prepared / installer.PREPARED_MARKER).is_file()
    assert not (prepared / ".git").exists()
    assert not (prepared / "backlog").exists()
    installer.validate_prepared_mcp(prepared, str(Path(sys.executable).resolve()))

    if os.name != "nt":
        mode = (prepared / ".claude-plugin" / "hooks" / "run-hook.cmd").stat().st_mode
        assert mode & stat.S_IXUSR

    second = installer.prepare_install_source(
        ROOT,
        version=version,
        python_executable=str(Path(sys.executable).resolve()),
        install_root=tmp_path / "platform data with spaces",
        dry_run=False,
    )
    assert second == prepared


def test_prepared_source_dry_run_writes_nothing(tmp_path):
    destination = installer.prepare_install_source(
        ROOT,
        version="1.2.3",
        python_executable=sys.executable,
        install_root=tmp_path / "dry-run",
        dry_run=True,
        system="Linux",
    )
    assert not destination.exists()


def test_installer_continues_after_one_client_fails(monkeypatch, tmp_path):
    clients = {
        name: installer.Client(name, f"/bin/{name}", name)
        for name in ("claude", "codex")
    }
    calls = []

    def fail(*args, **kwargs):
        calls.append("claude")
        raise RuntimeError("broken client")

    def succeed(*args, **kwargs):
        calls.append("codex")

    monkeypatch.setitem(installer.INSTALLERS, "claude", fail)
    monkeypatch.setitem(installer.INSTALLERS, "codex", succeed)
    installed, failures = installer.install_selected_clients(
        ["claude", "codex"],
        clients,
        tmp_path,
        version="1.0.0",
        dry_run=False,
        skip_validation=True,
        runner=lambda command: completed(command),
    )

    assert calls == ["claude", "codex"]
    assert installed == ["codex"]
    assert failures == [("claude", "broken client")]


def test_failed_client_state_read_does_not_trigger_mutation(tmp_path):
    client = installer.Client("codex", "/bin/codex", "codex-cli")
    calls = []

    def runner(command):
        calls.append(list(command))
        return completed(command, stderr="state unavailable", returncode=1)

    with pytest.raises(RuntimeError, match="marketplace listing"):
        installer.install_codex(
            client,
            tmp_path,
            False,
            runner,
            desired_version="1.0.0",
        )
    assert len(calls) == 1
    assert calls[0][-3:] == ["marketplace", "list", "--json"]


def test_source_preflight_fails_before_client_detection(monkeypatch, tmp_path):
    called = False

    def detect():
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(installer, "detect_clients", detect)
    with pytest.raises(SystemExit) as exc:
        installer.main(["--source", str(tmp_path), "--detect-only"])
    assert exc.value.code == 2
    assert called is False


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


def test_payload_comparison_is_newline_stable(tmp_path):
    spec = importlib.util.spec_from_file_location("sync_agent_plugins", SYNC)
    sync = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(sync)
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"one\ntwo\n")
    crlf.write_bytes(b"one\r\ntwo\r\n")
    assert sync.comparison_bytes(lf) == sync.comparison_bytes(crlf)


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
