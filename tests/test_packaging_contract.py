"""Release packaging contracts for manual and prepared installations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent


def _direct_entrypoints() -> list[str]:
    paths = [
        "hooks/run-hook.cmd",
        "codex/hooks/run-hook.cmd",
        ".githooks/pre-commit",
        "templates/githooks/pre-commit",
    ]
    for prefix in ("bin", "codex/bin", "copilot/bin"):
        paths.extend(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / prefix).iterdir()
            if path.is_file() and path.suffix != ".py"
        )
    return sorted(set(paths))


def _require_commit_bound_entrypoints() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--", *_direct_entrypoints()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.splitlines()
    if set(tracked) != set(_direct_entrypoints()):
        pytest.skip("direct-entrypoint index contract requires a committed candidate")


def test_git_index_records_every_direct_entrypoint_as_executable():
    _require_commit_bound_entrypoints()
    result = subprocess.run(
        ["git", "ls-files", "--stage", "--", *_direct_entrypoints()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    modes = {
        line.split(maxsplit=3)[3]: line.split(maxsplit=1)[0]
        for line in result.stdout.splitlines()
    }
    assert set(modes) == set(_direct_entrypoints())
    assert {path: mode for path, mode in modes.items() if mode != "100755"} == {}


def test_git_archive_preserves_manual_install_modes(tmp_path):
    _require_commit_bound_entrypoints()
    tree = subprocess.run(
        ["git", "write-tree"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    archive = tmp_path / "adr-kit.tar"
    subprocess.run(
        ["git", "archive", "--format=tar", f"--output={archive}", tree],
        cwd=ROOT,
        check=True,
    )
    with tarfile.open(archive) as payload:
        for path in _direct_entrypoints():
            assert payload.getmember(path).mode & 0o111, path


@pytest.mark.skipif(os.name == "nt", reason="Unix direct-execution contract")
def test_manual_checkout_entrypoints_execute_on_unix(tmp_path):
    profiles = subprocess.run(
        [str(ROOT / "bin" / "adr"), "profiles", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert profiles.returncode == 0, profiles.stderr
    hook = subprocess.run(
        [
            "sh",
            str(ROOT / "hooks" / "run-hook.cmd"),
            "SessionStart",
            "claude-code-cli",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert hook.returncode == 0, hook.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows polyglot-wrapper contract")
def test_manual_checkout_hook_wrapper_is_quiet_on_windows():
    wrapper = ROOT / "hooks" / "run-hook.cmd"
    result = subprocess.run(
        # Invoke by absolute path, matching how plugin.json launches the hook.
        # A bare name is not resolvable when NoDefaultCurrentDirectoryInExePath
        # is set, which is the default in several Windows shells.
        ["cmd.exe", "/d", "/c", str(wrapper), "SessionStart", "claude-code-cli"],
        cwd=wrapper.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert result.stderr == ""
    if result.stdout.strip():
        json.loads(result.stdout)


@pytest.mark.skipif(os.name != "nt", reason="Codex Windows command contract")
@pytest.mark.parametrize("shell", ["cmd.exe", "powershell.exe"])
@pytest.mark.parametrize("plugin_state", ["installed", "missing-wrapper", "missing-root"])
def test_codex_windows_hook_command_runs_with_piped_input(tmp_path, shell, plugin_state):
    plugin = tmp_path / "ADR Kit & test"
    if plugin_state == "installed":
        hook = plugin / "hooks" / "run-hook.cmd"
        hook.parent.mkdir(parents=True)
        hook.write_bytes(
            b'@echo off\r\nset /p INPUT=\r\necho %~1 %~2 %INPUT%\r\nexit /b 0\r\n'
        )
    elif plugin_state == "missing-wrapper":
        plugin.mkdir()
    env = dict(os.environ)
    env.pop("PLUGIN_ROOT", None)
    if plugin_state != "missing-root":
        env["PLUGIN_ROOT"] = str(plugin)

    manifest = json.loads((ROOT / "codex/hooks/hooks.json").read_text(encoding="utf-8"))
    command = manifest["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"]
    if shell == "cmd.exe":
        invocation = f'cmd.exe /d /c "{command}"'
    else:
        script = (
            "$global:LASTEXITCODE = 0\n"
            f"[Console]::In.ReadLine() | {command}\n"
            "if ($?) { exit 0 }\n"
            "if ($LASTEXITCODE) { exit $LASTEXITCODE }\n"
            "exit 1"
        )
        invocation = [shell, "-NoProfile", "-NonInteractive", "-Command", script]

    payload = '{"event":"PreToolUse"}'
    result = subprocess.run(
        invocation, cwd=tmp_path, env=env, input=payload + "\n",
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    expected = f"pre-tool-use codex-cli {payload}" if plugin_state == "installed" else ""
    assert result.stdout.strip() == expected
