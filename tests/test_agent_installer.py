"""Tests for detected-client installation and client contract separation."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from clients.installer import native
from clients.installer.contracts import DetectedClient
from clients.installer.detection import detailed_detection
from clients.installer.planning import build_plan, render_plan
from clients.installer.transaction import client_lock, run_transaction
from clients.installer.payload import payload_digest, remove_owned_payloads
from clients.installer.updates import record_update_state, update_decision

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


def test_claude_marketplace_repoints_on_version_bump(tmp_path):
    # A prepared-directory registration that points at a DIFFERENT (older)
    # version directory must NOT be treated as matching the new prepared source,
    # otherwise install_claude skips the re-point and the version never advances
    # (regression: 0.36.0 -> 0.37.0 stayed on 0.36.0).
    new_source = tmp_path / "marketplaces" / "0.37.0"
    new_source.mkdir(parents=True)
    (new_source / installer.PREPARED_MARKER).write_text("{}\n", encoding="utf-8")
    stale = {
        "name": "rvdbreemen-adr-kit",
        "source": "directory",
        "path": str(tmp_path / "marketplaces" / "0.36.0"),
        "installLocation": str(tmp_path / "marketplaces" / "0.36.0"),
    }
    assert not installer.claude_marketplace_source_matches(stale, new_source)
    # The matching version directory still matches.
    current = {
        "name": "rvdbreemen-adr-kit",
        "source": "directory",
        "path": str(new_source),
    }
    assert installer.claude_marketplace_source_matches(current, new_source)


def test_installer_subprocesses_never_inherit_console_stdin():
    """No installer subprocess may inherit the console's stdin.

    ``hooks/adr-hook.py`` reads its payload from stdin, so a call without an
    explicit ``stdin``/``input`` blocks until an EOF the console never sends,
    and ``subprocess.run`` then re-enters ``communicate()`` unbounded after its
    own timeout. Under pytest fd 0 is already closed, so a behavioural test
    cannot see this; the source is the only place the contract is visible.
    """

    def closes_stdin(node: ast.Call) -> bool:
        for keyword in node.keywords:
            if keyword.arg not in {"stdin", "input"}:
                continue
            # ``stdin=None`` is the default, which is exactly the broken form.
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is None:
                continue
            return True
        return False

    offenders = []
    sources = sorted((ROOT / "clients" / "installer").glob("*.py"))
    assert sources, "expected installer sources to scan"
    # The entrypoint owns the runner every client-CLI mutation flows through,
    # so the contract is only real if it is scanned along with the package.
    sources.append(ROOT / "scripts" / "install-agent-envs.py")
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None)
            if name not in {"run", "Popen", "check_output", "call"}:
                continue
            if not closes_stdin(node):
                offenders.append(f"{source.name}:{node.lineno}")

    assert not offenders, (
        "installer subprocess calls must pass stdin= or input=; "
        f"these inherit the console and can block forever: {offenders}"
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
    claude_config = json.loads((prepared / ".mcp.json").read_text())
    assert claude_config["mcpServers"]["adr-kit"]["command"] == str(
        Path(sys.executable).resolve()
    )
    copilot_config = json.loads((prepared / "copilot" / ".mcp.json").read_text())
    assert copilot_config["mcpServers"]["adr-kit"] == {
        "cwd": ".",
        "command": str(Path(sys.executable).resolve()),
        "args": ["${PLUGIN_ROOT}/bin/adr-mcp"],
    }
    assert (prepared / installer.PREPARED_MARKER).is_file()
    assert not (prepared / ".git").exists()
    assert not (prepared / "backlog").exists()
    assert not (prepared / "tests").exists()
    assert not (prepared / "docs" / "plans").exists()
    assert (prepared / "agents" / "adr-generator.md").is_file()
    consumer = tmp_path / "unrelated consumer project"
    installer.validate_prepared_mcp(
        prepared,
        str(Path(sys.executable).resolve()),
        copilot_project_root=consumer,
    )
    installer.validate_prepared_hooks(prepared)
    assert consumer.is_dir()
    assert not (consumer / "bin" / "adr-mcp").exists()

    if os.name != "nt":
        entrypoints = [
            prepared / "hooks" / "run-hook.cmd",
            prepared / "codex" / "hooks" / "run-hook.cmd",
            prepared / "copilot" / "hooks" / "run-hook.cmd",
            *[
                path
                for prefix in ("bin", "codex/bin", "copilot/bin")
                for path in (prepared / prefix).iterdir()
                if path.is_file() and path.suffix != ".py"
            ],
        ]
        assert all(path.stat().st_mode & stat.S_IXUSR for path in entrypoints)

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


def _locked_copilot_plugin_dir(tmp_path: Path, monkeypatch) -> Path:
    """Point COPILOT_HOME at a plugin directory whose rename always fails."""
    monkeypatch.setenv("COPILOT_HOME", str(tmp_path / "copilot home"))
    plugins = native.copilot_plugin_directory()
    plugins.mkdir(parents=True)
    real_rename = Path.rename

    def refuse(self, target):
        if self == plugins:
            raise OSError(5, "Access is denied")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", refuse)
    return plugins


def test_replaceability_probe_restores_the_directory_it_renames(tmp_path, monkeypatch):
    monkeypatch.setenv("COPILOT_HOME", str(tmp_path / "copilot home"))
    plugins = native.copilot_plugin_directory()
    (plugins / "adr-kit").mkdir(parents=True)

    assert native.directory_replacement_blocked_by(plugins) is None
    assert (plugins / "adr-kit").is_dir(), "the probe must put the directory back"
    assert not list(plugins.parent.glob("*.adr-kit-probe"))
    # A directory that is not there yet cannot block anything.
    assert native.directory_replacement_blocked_by(tmp_path / "absent") is None


def test_copilot_install_refuses_a_locked_plugin_directory_before_touching_anything(
    tmp_path, monkeypatch
):
    """A locked plugin directory must stop the run before the first mutation.

    Copilot replaces the directory to upgrade, so a rename it cannot perform
    means the install fails partway and the rollback then dismantles the
    registration the client was happily using. Refusing up front is the only
    outcome that leaves the client no worse off.
    """
    plugins = _locked_copilot_plugin_dir(tmp_path, monkeypatch)
    calls = []

    def runner(command):
        calls.append(command)
        return completed(command, "")

    copilot = installer.Client("copilot", "/bin/copilot", "GitHub Copilot CLI")
    with pytest.raises(RuntimeError) as error:
        native.install_copilot(copilot, tmp_path / "repo", False, runner)

    assert not calls, "no client command may run once the directory is known to be locked"
    message = str(error.value)
    assert "VS Code" in message
    assert "MCP server" in message
    assert str(plugins) in message
    assert "Access is denied" in message


def test_copilot_dry_run_does_not_probe_the_plugin_directory(tmp_path, monkeypatch):
    """Dry run reports; it does not rename directories to find things out."""
    _locked_copilot_plugin_dir(tmp_path, monkeypatch)
    copilot = installer.Client("copilot", "/bin/copilot", "GitHub Copilot CLI")

    native.install_copilot(
        copilot,
        tmp_path / "repo",
        True,
        lambda command: completed(command, installer.MARKETPLACES["copilot"]),
    )


def _sync_check(root: Path):
    """Run the drift check against one tree and return the completed process."""
    return subprocess.run(
        [sys.executable, str(SYNC), "--check", "--root", str(root), "--format", "json"],
        # cwd stays at the repo root on purpose: the entrypoint must resolve its
        # target from --root, not from where it happens to be invoked.
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.tree_snapshot
def test_codex_payload_is_synced(tree_snapshot):
    """The generated trees are a pure function of the source trees.

    Checked against the session-start snapshot rather than the live checkout.
    Pointed at the live tree this assertion is sensitive to every other test in
    the run -- any neighbouring write under a COPY_ROOT or inside a generated
    root fails it, and the failure names the drifting file rather than the test
    that caused it (TASK-128).
    """
    proc = _sync_check(tree_snapshot)
    assert proc.returncode == 0, (
        f"snapshot at {tree_snapshot}\n{proc.stdout}{proc.stderr}"
    )


@pytest.mark.tree_snapshot
def test_a_neighbouring_write_cannot_fail_the_sync_check(tmp_path, tree_snapshot):
    """The hazard is real, and the snapshot is immune to it."""
    live = tmp_path / "live"
    shutil.copytree(tree_snapshot, live)
    stray = live / "codex" / "skills" / "zzz-stray" / "SKILL.md"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("a file a neighbouring test wrote\n", encoding="utf-8")

    drifted = _sync_check(live)
    assert drifted.returncode == 1, drifted.stdout + drifted.stderr
    assert json.loads(drifted.stdout)["drift"] == ["codex/skills/zzz-stray/SKILL.md"]

    # The snapshot never sees the write, which is the whole point.
    assert _sync_check(tree_snapshot).returncode == 0


@pytest.mark.tree_snapshot
def test_sync_check_still_fails_on_a_deliberate_desync(tmp_path, tree_snapshot):
    """Isolation must not cost the assertion its teeth."""
    desynced = tmp_path / "desynced"
    shutil.copytree(tree_snapshot, desynced)
    target = desynced / "codex" / "hooks" / "hooks.json"
    target.write_bytes(target.read_bytes() + b"\n")

    proc = _sync_check(desynced)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "codex/hooks/hooks.json" in json.loads(proc.stdout)["drift"]


def test_ci_still_checks_the_live_tree_for_adapter_drift():
    """The snapshot protects the test; CI still has to check the real tree.

    Without this, moving the test onto a snapshot would quietly remove the only
    assertion that the committed mirrors match the committed source.
    """
    workflows = ("validate.yml", "release-candidate.yml", "release-publish.yml")
    missing = [
        name
        for name in workflows
        if "build-client-adapters.py --check"
        not in (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    ]
    assert not missing, f"live-tree drift gate missing from: {missing}"


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
    assert "hooks" not in claude
    assert codex["hooks"] == "./hooks/hooks.json"
    assert codex["skills"] == "./skills/"
    assert codex["mcpServers"] == "./.mcp.json"
    claude_hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())
    assert "CLAUDE_PLUGIN_ROOT" in json.dumps(claude_hooks)
    assert "codex" not in json.dumps(claude_hooks).lower()


def test_copilot_has_a_native_manifest_and_mcp_contract():
    manifest = json.loads((ROOT / "copilot" / "plugin.json").read_text())
    mcp = json.loads((ROOT / "copilot" / ".mcp.json").read_text())
    assert manifest["name"] == "adr-kit"
    assert manifest["skills"] == "skills/"
    assert manifest["hooks"] == "hooks.json"
    assert manifest["mcpServers"] == ".mcp.json"
    assert mcp["mcpServers"]["adr-kit"]["cwd"] == "."
    assert mcp["mcpServers"]["adr-kit"]["args"] == [
        "${PLUGIN_ROOT}/bin/adr-mcp"
    ]
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


def _effective_settings():
    return {
        "clients": {
            "claude": {"enabled": None},
            "codex": {"enabled": None},
            "copilot": {"enabled": None},
        }
    }


def test_detailed_detection_is_read_only_and_reports_overrides(tmp_path):
    install_root = tmp_path / "marketplaces"
    old = install_root / "0.34.0"
    current = install_root / "0.35.0"
    for root, version in ((old, "0.34.0"), (current, "0.35.0")):
        root.mkdir(parents=True)
        (root / installer.PREPARED_MARKER).write_text(
            json.dumps({"version": version, "source": str(ROOT)}),
            encoding="utf-8",
        )
    before = sorted(str(path) for path in tmp_path.rglob("*"))
    clients = {"codex": installer.Client("codex", "C:/Codex/codex.exe", "codex-cli 1")}
    detected = detailed_detection(
        clients,
        install_root=install_root,
        effective_settings=_effective_settings(),
        env={"CODEX_HOME": "C:/custom codex"},
    )
    after = sorted(str(path) for path in tmp_path.rglob("*"))
    assert before == after
    assert detected["codex"].config_override == "C:/custom codex"
    assert detected["codex"].installed_version == "0.35.0"
    assert detected["codex"].duplicate_roots == (str(old.resolve()),)


def test_plan_is_stable_complete_and_opt_out_aware(tmp_path):
    detected = {
        "claude": DetectedClient(
            "claude",
            "C:/claude.exe",
            "Claude Code 2",
            None,
            True,
            "0.35.0",
            str(tmp_path),
            "abc",
            (),
            False,
            True,
            (),
        )
    }
    settings = _effective_settings()
    settings["clients"]["claude"]["enabled"] = False
    plan = build_plan(
        detected,
        source=tmp_path,
        version="0.35.0",
        source_sha256="abc",
        effective_settings=settings,
    )
    assert not plan.clients[0].selected
    assert "validation" in render_plan(plan)
    assert json.loads(render_plan(plan, format="json"))["schema_version"] == 1


def test_major_version_plan_requires_confirmation(tmp_path):
    state = DetectedClient(
        "codex",
        "C:/codex.exe",
        "codex-cli 1",
        None,
        True,
        "0.35.0",
        str(tmp_path),
        "abc",
        (),
        False,
        True,
        (),
    )
    plan = build_plan(
        {"codex": state},
        source=tmp_path,
        version="1.0.0",
        source_sha256="def",
        effective_settings=_effective_settings(),
    )
    assert plan.requires_confirmation
    assert plan.clients[1].migrations == ("major-version:0.35.0->1.0.0",)


def test_client_transactions_are_isolated_and_retain_failure_evidence(tmp_path):
    events = []
    with pytest.raises(RuntimeError, match="activation failed"):
        run_transaction(
            "claude",
            state_root=tmp_path,
            apply=lambda: events.append("apply"),
            validate=lambda: (_ for _ in ()).throw(RuntimeError("activation failed")),
            rollback=lambda: events.append("rollback"),
        )
    assert events == ["apply", "rollback"]
    evidence = json.loads(
        (tmp_path / "evidence" / "claude-last-transaction.json").read_text()
    )
    assert evidence["status"] == "rolled-back"
    assert evidence["error"] == "activation failed"

    with client_lock(tmp_path, "codex"):
        with pytest.raises(RuntimeError, match="already locked"):
            with client_lock(tmp_path, "codex"):
                pass


def test_payload_digest_is_newline_stable_and_uninstall_is_ownership_bounded(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "file.txt").write_bytes(b"one\r\ntwo\r\n")
    (second / "file.txt").write_bytes(b"one\ntwo\n")
    assert payload_digest(first) == payload_digest(second)
    (first / installer.PREPARED_MARKER).write_text("{}\n", encoding="utf-8")
    user = tmp_path / "user"
    user.mkdir()
    (user / "keep.txt").write_text("keep", encoding="utf-8")
    assert remove_owned_payloads(tmp_path) == [first]
    assert user.is_dir()
    assert second.is_dir()


def test_update_policy_is_deferred_pinned_and_records_last_check(tmp_path):
    values = {
        "update": {
            "policy": "pinned",
            "trigger": "project-setup",
            "frequency_hours": 24,
            "offline": False,
            "pinned_version": "0.35.0",
        }
    }
    decision = update_decision(values, "0.35.0", now=100, last_check=99)
    assert decision["activation_allowed"]
    assert not decision["due"]
    path = record_update_state(
        tmp_path, "copilot", version="0.35.0", trigger=decision["trigger"]
    )
    state = json.loads(path.read_text())
    assert state["client"] == "copilot"
    assert state["trigger"] == "project-setup"


def test_stale_lock_is_recovered_and_interruption_is_evidenced(tmp_path):
    lock = tmp_path / "locks" / "codex.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("stale\n", encoding="utf-8")
    os.utime(lock, (time.time() - 3600, time.time() - 3600))
    with client_lock(tmp_path, "codex", stale_seconds=1):
        assert lock.is_file()
    assert not lock.exists()

    with pytest.raises(KeyboardInterrupt):
        run_transaction(
            "copilot",
            state_root=tmp_path,
            apply=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            validate=lambda: None,
            rollback=lambda: None,
        )
    evidence = json.loads(
        (tmp_path / "evidence" / "copilot-last-transaction.json").read_text()
    )
    assert evidence["status"] == "rolled-back"


# ---------------------------------------------------------------------------
# TASK-51: a failed install must not leave the marketplace registered
# ---------------------------------------------------------------------------


class _HalfInstallRunner:
    """CLI stand-in where marketplace ops succeed but `plugin install` fails.

    This is the shape reported in TASK-51 during the 0.39.0 local publish: the
    Copilot marketplace ended up registered at the new version while
    `copilot plugin list` said "No plugins installed".
    """

    def __init__(self, client: str) -> None:
        self.client = client
        self.calls: list[list[str]] = []

    def __call__(self, command):
        self.calls.append(list(command))
        joined = " ".join(command)
        if "marketplace" in joined and "list" in joined:
            empty = {"claude": "[]", "codex": '{"marketplaces": []}', "copilot": ""}
            return subprocess.CompletedProcess(command, 0, empty[self.client], "")
        if "plugin" in joined and "list" in joined:
            empty = {
                "claude": "[]",
                "codex": '{"installed": []}',
                "copilot": "No plugins installed\n",
            }
            return subprocess.CompletedProcess(command, 0, empty[self.client], "")
        if "marketplace" in joined and ("add" in command or "remove" in command):
            return subprocess.CompletedProcess(command, 0, "ok", "")
        if "install" in command or "add" in command:
            return subprocess.CompletedProcess(command, 1, "", "install failed: boom")
        return subprocess.CompletedProcess(command, 0, "", "")

    def issued(self, *fragments: str) -> bool:
        return any(all(f in " ".join(c) for f in fragments) for c in self.calls)


@pytest.mark.parametrize("client_name", ["claude", "codex", "copilot"])
def test_failed_install_removes_a_marketplace_this_run_registered(tmp_path, client_name):
    """A half-registered marketplace is worse than a clean failure.

    The generic transaction rollback cannot cover this case: it restores the
    PREVIOUS prepared source, so it is a no-op when no `<source>.old` exists --
    which is precisely a first install. Only the installer knows it registered
    the marketplace, so the undo lives there.
    """
    from clients.installer import native

    source = tmp_path / "prepared"
    (source / "codex" / ".codex-plugin").mkdir(parents=True)
    (source / "codex" / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"version": "0.39.0"}), encoding="utf-8"
    )
    client = native.Client(name=client_name, executable=client_name, version="1.0.0")
    runner = _HalfInstallRunner(client_name)

    with pytest.raises(RuntimeError, match="install failed: boom"):
        native.INSTALLERS[client_name](
            client, source, False, runner, desired_version="0.39.0"
        )

    assert runner.issued("marketplace", "add"), "precondition: this run registered it"
    assert runner.issued("marketplace", "remove"), (
        f"{client_name}: marketplace left registered after a failed install"
    )
    # The undo must come after the failure, not replace it.
    add_at = next(i for i, c in enumerate(runner.calls) if "add" in c and "marketplace" in " ".join(c))
    remove_at = next(i for i, c in enumerate(runner.calls) if "remove" in c and "marketplace" in " ".join(c))
    assert remove_at > add_at


@pytest.mark.parametrize("client_name", ["claude", "codex", "copilot"])
def test_failed_install_keeps_a_marketplace_it_did_not_register(tmp_path, client_name):
    """Only undo what this run did: a pre-existing registration is not ours."""
    from clients.installer import native

    source = tmp_path / "prepared"
    (source / "codex" / ".codex-plugin").mkdir(parents=True)
    (source / "codex" / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"version": "0.39.0"}), encoding="utf-8"
    )
    client = native.Client(name=client_name, executable=client_name, version="1.0.0")

    marketplace = native.MARKETPLACES[client_name]
    listings = {
        "claude": json.dumps([{"name": marketplace, "source": {"source": str(source)}}]),
        "codex": json.dumps({"marketplaces": [{"name": marketplace, "source": str(source)}]}),
        "copilot": f"{marketplace}  {source}\n",
    }

    class _PreRegistered(_HalfInstallRunner):
        def __call__(self, command):
            joined = " ".join(command)
            if "marketplace" in joined and "list" in joined:
                self.calls.append(list(command))
                return subprocess.CompletedProcess(command, 0, listings[self.client], "")
            return super().__call__(command)

    runner = _PreRegistered(client_name)
    with pytest.raises(RuntimeError):
        native.INSTALLERS[client_name](
            client, source, False, runner, desired_version="0.39.0"
        )

    assert not runner.issued("marketplace", "add"), "precondition: already registered"
    assert not runner.issued("marketplace", "remove"), (
        f"{client_name}: removed a marketplace this run did not register"
    )
