"""Native package contracts for Claude, Codex, and Copilot CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "bin", ROOT / "scripts"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from adr_doctor_checks import check_hook_package


CLIENTS = {
    "claude": ("claude", ROOT / "skills"),
    "codex": ("codex", ROOT / "codex" / "skills"),
    "copilot": ("copilot", ROOT / "copilot" / "skills"),
}


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_native_contract_fixtures_match_manifests_skills_and_hooks():
    fixtures = {
        name: _json(f"tests/fixtures/{name}/native-contract.json")
        for name in CLIENTS
    }
    assert [fixtures[name]["client"] for name in CLIENTS] == [
        "claude-code-cli",
        "codex-cli",
        "github-copilot-cli",
    ]
    for name, (doctor_name, skills) in CLIENTS.items():
        assert len(list(skills.glob("*/SKILL.md"))) == 14
        result = check_hook_package(ROOT, doctor_name)
        assert result["status"] == "healthy", result
        assert result["evidence"][0]["events"] == sorted(fixtures[name]["events"])


def test_windows_native_evidence_is_independent_and_not_release_promoted_dirty():
    expected = {
        "claude": "2.1.215 (Claude Code)",
        "codex": "codex-cli 0.144.6",
        "copilot": "GitHub Copilot CLI 1.0.71",
    }
    hashes = set()
    for name, version in expected.items():
        evidence = _json(f"tests/certification/{name}/windows-native.json")
        assert evidence["client_version"] == version
        assert evidence["platforms"]["windows"]["status"] == "pass"
        assert evidence["working_tree_clean"] is False
        assert evidence["release_eligible"] is False
        assert evidence["model_invocation"].startswith("not-run")
        assert evidence["official_contract"]["checked_on"] == "2026-07-19"
        assert evidence["evidence_links"]
        assert evidence["latency_evidence"]["hooks"] == {
            "method_id": "adr-kit-hook-latency-v1",
            "state": "warm-filesystem",
            "samples": 30,
            "all_targets_met": True,
            "source": "docs/hook-performance.md",
        }
        generation = evidence["latency_evidence"]["generation"]
        assert generation["samples"] >= 5
        assert generation["warm_writes"] == 0
        assert generation["source"] == "packaging/client-generation-benchmark.json"
        certification = evidence["certification"]
        for key in (
            "required_outcomes",
            "fixtures",
            "native_smoke",
            "lifecycle_preservation",
        ):
            assert all(certification[key].values())
        assert certification["native_optimization"][
            "deprecated-prompt-first-class"
        ] is False
        assert all(
            value is True
            for key, value in certification["native_optimization"].items()
            if key != "deprecated-prompt-first-class"
        )
        hashes.add(evidence["prepared_payload_sha256"])
    assert len(hashes) == 1


def test_claude_uses_root_components_and_native_skill_metadata():
    manifest = _json(".claude-plugin/plugin.json")
    assert "hooks" not in manifest
    assert not (ROOT / ".claude-plugin/hooks").exists()
    assert (ROOT / "hooks/hooks.json").is_file()
    assert (ROOT / ".mcp.json").is_file()
    for path in (ROOT / "skills").glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        assert "description:" in frontmatter
        assert "argument-hint:" in frontmatter
        assert "$ARGUMENTS" in text
        assert "Codex CLI" not in text and "GitHub Copilot CLI" not in text


def test_codex_and_copilot_skills_use_only_their_native_discovery_syntax():
    for path in (ROOT / "codex/skills").glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert "$adr-kit:" in text
        assert "/adr-kit:" not in text
        assert "Claude" not in text and "GitHub Copilot" not in text
    for path in (ROOT / "copilot/skills").glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert "/skills" in text
        assert "$adr-kit:" not in text and "/adr-kit:" not in text
        assert "Claude" not in text and "Codex" not in text


def test_copilot_hooks_are_lower_camel_and_cross_platform():
    hooks = _json("copilot/hooks.json")
    assert set(hooks["hooks"]) == {
        "sessionStart",
        "userPromptSubmitted",
        "postToolUse",
    }
    for handlers in hooks["hooks"].values():
        for handler in handlers:
            assert handler["type"] == "command"
            assert handler["bash"].endswith("|| true")
            assert handler["powershell"].endswith("exit 0")


def test_doctor_distinguishes_broken_hook_package(tmp_path):
    plugin = tmp_path / "plugin"
    config = plugin / "hooks" / "hooks.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"hooks":{"SessionStart":[]}}\n', encoding="utf-8")
    result = check_hook_package(plugin, "claude")
    assert result["status"] == "failed"
    assert "broken native hook package" in result["summary"]
