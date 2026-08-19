"""Cross-client doctor contracts and stale-launcher regressions."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
DOCTOR = BIN / "adr-doctor"

for value in (str(ROOT), str(BIN), str(ROOT / "scripts")):
    if value not in sys.path:
        sys.path.insert(0, value)

from adr_doctor_checks import check_mcp_launcher
from adr_doctor_models import benchmark_extension
import adr_doctor_probes
from adr_doctor_probes import _mcp_deep, _native_deep


def _doctor(
    project: Path,
    *extra: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--repo-root",
            str(project),
            "--plugin-root",
            str(ROOT),
            "--format",
            "json",
            *extra,
            str(project / "docs" / "adr"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
        env=env,
    )


def test_deep_native_probe_closes_stdin(tmp_path, monkeypatch):
    """`adr doctor --deep` starts three third-party CLIs; none may hold stdin.

    On Windows `copilot` resolves to a .CMD shim, so the declared `timeout=10`
    is not a bound: subprocess.run's TimeoutExpired handler re-enters
    communicate() unbounded and its kill reaches only cmd.exe, not the node
    grandchild. A descendant waiting on an inherited console stdin would make
    that wait permanent. Asserted here rather than in the source-level guard
    because this is the call the doctor actually makes (TASK-167).
    """
    recorded = {}

    def recorder(values, **kwargs):  # run_bounded's signature, same shape
        recorded["values"] = values
        recorded.update(kwargs)
        return subprocess.CompletedProcess(
            values, 0, "adr-kit@rvdbreemen-adr-kit-copilot", ""
        )

    monkeypatch.setattr(adr_doctor_probes, "run_bounded", recorder)
    result = _native_deep(tmp_path, "copilot", "C:/fake/copilot.CMD")

    assert recorded["stdin"] is subprocess.DEVNULL
    assert recorded["capture_output"] is True
    assert recorded["timeout"] == 10
    assert result["status"] == "healthy"


def test_removed_cache_launcher_is_stale_and_reports_exact_owned_path(tmp_path):
    plugin = tmp_path / "plugin"
    config = plugin / "codex" / ".mcp.json"
    config.parent.mkdir(parents=True)
    removed = tmp_path / "cache" / "0.34.0" / "bin" / "adr-mcp"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "adr-kit": {
                        "command": sys.executable,
                        "args": [str(removed)],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    result = check_mcp_launcher(plugin, "codex", required=True)
    assert result["status"] == "stale"
    assert result["required"]
    assert str(removed.resolve()) in result["evidence"][0]["missing_targets"]
    assert "install-agent-envs.py" in result["actions"][0]["command"]


def test_check_mode_is_read_only_and_default_repairs_owned_index(tmp_path):
    project = tmp_path / "project"
    adr_dir = project / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    user = project / "user.txt"
    user.write_text("keep\n", encoding="utf-8")
    before = user.read_bytes()
    checked = _doctor(project, "--check")
    assert checked.returncode == 1
    assert not (adr_dir / "ADR-INDEX.json").exists()
    assert user.read_bytes() == before

    repaired = _doctor(project)
    payload = json.loads(repaired.stdout)
    assert (adr_dir / "ADR-INDEX.json").is_file()
    assert payload["schema_version"] == 1
    assert user.read_bytes() == before


def test_fix_backs_up_instruction_before_managed_rewrite(tmp_path):
    project = tmp_path / "project"
    (project / "docs" / "adr").mkdir(parents=True)
    agents = project / "AGENTS.md"
    agents.write_text("user guidance\n", encoding="utf-8")
    executable_dir = tmp_path / "bin"
    executable_dir.mkdir()
    if os.name == "nt":
        executable = executable_dir / "codex.cmd"
        executable.write_text("@echo codex-cli 1.0\n", encoding="utf-8")
    else:
        executable = executable_dir / "codex"
        executable.write_text(
            "#!/bin/sh\nprintf 'codex-cli 1.0\\n'\n",
            encoding="utf-8",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env["PATH"] = str(executable_dir) + os.pathsep + env.get("PATH", "")
    result = _doctor(project, "--fix", env=env)
    assert result.returncode in {0, 1}
    assert "user guidance" in agents.read_text(encoding="utf-8")
    assert "ADR-KIT CODEX START" in agents.read_text(encoding="utf-8")
    backups = list((project / ".adr-kit" / "backups").glob("*instruction.bak"))
    assert backups
    assert backups[0].read_text(encoding="utf-8") == "user guidance\n"
    assert not (project / ".adr-kit" / "ADR-guide.local.md").exists()


def test_deep_extension_contract_is_versioned_and_unpopulated_safely():
    extension = benchmark_extension(
        method_id="test-v1",
        state="warm",
        sample_count=5,
        reference_fixture="fixture.json",
        budget={"p50_ms": 10, "p95_ms": 20, "hard_timeout_ms": 50},
    )
    assert extension["contract_version"] == 1
    assert extension["measurements"] == {
        "p50_ms": None,
        "p95_ms": None,
        "max_ms": None,
    }


def test_deep_mcp_probe_accepts_complete_seven_tool_contract():
    result = _mcp_deep(ROOT, ROOT)

    assert result["status"] == "healthy"
    assert result["evidence"][0]["call_ok"]
    assert result["evidence"][0]["tools"] == [
        "adr_context",
        "adr_judge",
        "adr_lint",
        "adr_quality",
        "adr_readiness",
        "adr_related",
        "adr_status",
    ]
