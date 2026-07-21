"""Contracts for bounded, deterministic three-client adapter generation."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "client_generation.py"
SPEC = importlib.util.spec_from_file_location("client_generation", MODULE_PATH)
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GEN
SPEC.loader.exec_module(GEN)


def _files(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def _manifests() -> dict[str, object]:
    return {
        name: json.loads((ROOT / name).read_text(encoding="utf-8"))
        for name in (
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".agents/plugins/marketplace.json",
            "codex/.codex-plugin/plugin.json",
            ".github/plugin/marketplace.json",
            "copilot/plugin.json",
            ".mcp.json",
            "codex/.mcp.json",
            "copilot/.mcp.json",
        )
    }


def test_registry_and_workflows_are_exactly_three_clients():
    capabilities = json.loads((ROOT / "clients/capabilities.json").read_text())
    workflows = json.loads((ROOT / "clients/workflows.json").read_text())

    assert capabilities["program_scope"]["first_class_clients"] == list(GEN.CLIENT_IDS)
    assert list(workflows["clients"]) == list(GEN.CLIENT_IDS)
    assert len(workflows["workflows"]) == 15
    assert [item["id"] for item in workflows["workflows"]] == sorted(
        item["id"] for item in workflows["workflows"]
    )
    raw = json.dumps((capabilities, workflows)).lower()
    for future in ("opencode", "kilocode", "kimicode", "cursor", "gemini", "qwen"):
        assert future not in raw


def test_clean_generation_is_byte_identical_and_warm_run_preserves_mtimes(tmp_path):
    output = tmp_path / "output with spaces and ünicode"
    first_stats, first_drift = GEN.generate(ROOT, output)
    first = _files(output)
    second_stats, second_drift = GEN.generate(ROOT, output)
    second = _files(output)

    assert first_drift
    assert first_stats.files_written == len(first)
    assert second_drift == []
    assert second_stats.files_written == 0
    assert first == second


def test_drift_check_detects_edit_missing_workflow_and_stale_output(tmp_path):
    output = tmp_path / "payload"
    GEN.generate(ROOT, output)
    skill = output / "codex/skills/adr/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "hand edit\n", encoding="utf-8")
    stale = output / "copilot/skills/stale/SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    _, drift = GEN.generate(ROOT, output, check=True)

    assert "codex/skills/adr/SKILL.md" in drift
    assert "copilot/skills/stale/SKILL.md" in drift
    invalid = json.loads((ROOT / "clients/workflows.json").read_text())
    invalid["workflows"].pop()
    with pytest.raises(GEN.GenerationError, match="complete canonical"):
        GEN._validate_workflows(invalid)
    invalid["workflows"].append({"id": "adr", "description": "duplicate", "procedure": ["x"]})
    with pytest.raises(GEN.GenerationError, match="complete canonical"):
        GEN._validate_workflows(invalid)


def test_native_manifests_validate_version_provenance_and_registered_divergence():
    manifests = _manifests()
    release_version = manifests[".claude-plugin/plugin.json"]["version"]
    GEN._validate_manifests(manifests, release_version)
    stale = dict(manifests)
    stale["copilot/plugin.json"] = dict(stale["copilot/plugin.json"])
    stale["copilot/plugin.json"]["version"] = "0.0.0"
    with pytest.raises(GEN.GenerationError, match="stale version"):
        GEN._validate_manifests(stale, release_version)
    divergent = dict(manifests)
    divergent["codex/.codex-plugin/plugin.json"] = dict(
        divergent["codex/.codex-plugin/plugin.json"]
    )
    divergent["codex/.codex-plugin/plugin.json"]["hooks"] = {}
    with pytest.raises(GEN.GenerationError, match="must reference"):
        GEN._validate_manifests(divergent, release_version)


def test_native_hook_shapes_are_generated_from_the_canonical_hook_manifest():
    hooks = json.loads((ROOT / "hooks/manifest.json").read_text())
    claude = json.loads(GEN._native_hook_config(hooks, "claude-code-cli"))
    codex = json.loads(GEN._native_hook_config(hooks, "codex-cli"))
    copilot = json.loads(
        GEN._native_hook_config(hooks, "github-copilot-cli")
    )

    assert "SessionStart" in claude["hooks"]
    assert claude["hooks"]["SessionStart"][0]["hooks"][0]["command"].startswith(
        '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd"'
    )
    assert codex["hooks"]["PreToolUse"][0]["hooks"][0][
        "command_windows"
    ].startswith('"%PLUGIN_ROOT%\\hooks\\run-hook.cmd"')
    assert set(copilot["hooks"]) == {
        "sessionStart",
        "userPromptSubmitted",
        "postToolUse",
    }
    assert all(
        {"bash", "powershell"} <= set(handler)
        for handlers in copilot["hooks"].values()
        for handler in handlers
    )


def test_exceptions_have_rationale_effect_and_real_fixtures():
    registry = json.loads((ROOT / "clients/exceptions.json").read_text())
    capabilities = json.loads((ROOT / "clients/capabilities.json").read_text())
    GEN._validate_capabilities(capabilities, registry)
    for exception in registry["exceptions"]:
        assert exception["rationale"]
        assert exception["user_effect"]
        fixture = ROOT / exception["fixture"]
        assert fixture.is_file()
        assert json.loads(fixture.read_text())["exception_id"] == exception["id"]


def test_generated_skills_prompts_guides_and_hooks_have_stable_provenance():
    workflows = json.loads((ROOT / "clients/workflows.json").read_text())
    ids = {item["id"] for item in workflows["workflows"]}
    for client, skill_root in (
        ("codex-cli", ROOT / "codex/skills"),
        ("github-copilot-cli", ROOT / "copilot/skills"),
    ):
        assert {path.parent.name for path in skill_root.glob("*/SKILL.md")} == ids
        for path in skill_root.glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            assert GEN.PROVENANCE in text
            assert client in text
            assert "C:\\" not in text and "/Users/" not in text
    for client in GEN.CLIENT_IDS:
        prompts = ROOT / "prompts" / client
        assert {path.stem for path in prompts.glob("*.md")} == ids
    assert GEN.PROVENANCE in (ROOT / "codex/instructions/ADR-guide.md").read_text()
    for path in (
        ROOT / "hooks/hooks.json",
        ROOT / "codex/hooks/hooks.json",
        ROOT / "copilot/hooks.json",
    ):
        value = json.loads(path.read_text())
        assert value.get("hooks")
    assert not (ROOT / ".claude-plugin/hooks").exists()
    native_hashes = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            ROOT / "hooks/bin/windows-x64/adr-hook.exe",
            ROOT / "codex/hooks/bin/windows-x64/adr-hook.exe",
            ROOT / "copilot/hooks/bin/windows-x64/adr-hook.exe",
        )
    }
    assert len(native_hashes) == 1


def test_fixture_text_and_mode_metadata_are_cross_platform_stable(tmp_path):
    workflow = {
        "id": "unicode",
        "description": "Works on Windows and POSIX paths with Unicode.",
        "title": "Café",
        "mutates": False,
        "procedure": ["Read `C:\\Program Files\\ADR Kit` and `/tmp/adr kit/é`."],
    }
    rendered = GEN._render_skill(workflow, "codex-cli")
    assert "Café".encode() in rendered
    assert b"\r\n" not in rendered
    inventory = json.loads((ROOT / "packaging/executables.json").read_text())
    assert inventory["entries"] == sorted(inventory["entries"], key=lambda item: item["path"])
    assert {item["expected_mode"] for item in inventory["entries"]} <= {"100644", "100755"}


def test_generator_has_no_network_or_runtime_dependency():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "http.client", "socket", "subprocess"):
        assert f"import {forbidden}" not in source
    dependencies = json.loads((ROOT / "packaging/dependencies.json").read_text())
    assert dependencies["runtime"] == []
    assert "coverage" not in json.dumps(dependencies["runtime"]).lower()
