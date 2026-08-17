"""Static and packaging contracts for the native OpenCode surface."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_opencode_package_is_a_self_contained_native_plugin_entrypoint():
    package = _json("package.json")

    assert package["name"] == "@rvdbreemen/adr-kit-opencode"
    assert package["version"] == _json(".claude-plugin/plugin.json")["version"]
    assert package["type"] == "module"
    assert package["main"] == "./opencode/plugin.ts"
    assert package["engines"]["opencode"]
    assert "dependencies" not in package
    assert "scripts/*.py" in package["files"]
    assert "bin" not in package["files"]
    assert "clients" not in package["files"]
    for pattern in package["files"]:
        assert list(ROOT.glob(pattern)), pattern


def test_npm_package_excludes_generated_and_client_specific_payloads():
    npmignore = (ROOT / ".npmignore").read_text(encoding="utf-8")

    for pattern in ("**/__pycache__/", "**/*.pdb", "tests/", "codex/", "copilot/"):
        assert pattern in npmignore


def test_project_opencode_config_uses_the_official_schema_and_local_package():
    config = _json("opencode.json")

    assert config["$schema"] == "https://opencode.ai/config.json"
    assert config["plugin"] == ["./"]


def test_plugin_uses_native_hooks_but_delegates_governance_to_shared_engines():
    source = (ROOT / "opencode" / "plugin.ts").read_text(encoding="utf-8")

    for hook in (
        '"chat.message"',
        '"experimental.chat.system.transform"',
        '"tool.execute.before"',
        '"tool.execute.after"',
        '"experimental.session.compacting"',
        '"tool.definition"',
        '"shell.env"',
        "event:",
    ):
        assert hook in source
    for shared_path in (
        'join(runtimeRoot, "bin", "adr-mcp")',
        'join(runtimeRoot, "hooks", "adr-hook.py")',
        'join(runtimeRoot, "clients", "workflows.json")',
    ):
        assert shared_path in source
    assert "Bun.spawn" in source
    assert "permissionDecision" in source


def test_opencode_does_not_enter_the_certified_three_client_registry():
    for relative in ("clients/capabilities.json", "clients/workflows.json"):
        raw = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "opencode" not in raw


def test_canonical_skills_are_valid_opencode_skill_definitions():
    name_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\n"), skill
        frontmatter = text.split("---", 2)[1]
        name = re.search(r"^name:\s*['\"]?([^'\"\n]+)", frontmatter, re.MULTILINE)
        description = re.search(r"^description:\s*['\"]?(.+)", frontmatter, re.MULTILINE)
        assert name and name.group(1).strip() == skill.parent.name
        assert description and description.group(1).strip()
        assert name_pattern.fullmatch(skill.parent.name)


def test_public_artifact_allowlist_carries_the_opencode_package():
    allowlist = _json("packaging/public-artifacts.json")
    roots = set(allowlist["include_roots"])

    assert {".npmignore", "opencode", "opencode.json", "package.json"} <= roots


def test_opencode_version_is_declared_in_the_shared_release_registry():
    registry = _json("packaging/version-sites.json")
    sites = {site["path"]: site for site in registry["sites"]}

    assert sites["package.json"]["kind"] == "regex"
    assert sites["package.json"]["path"] == "package.json"
