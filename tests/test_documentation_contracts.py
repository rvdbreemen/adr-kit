"""Regression tests for executable examples in canonical documentation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
ADR_TEMPLATE = REPO_ROOT / "templates" / "adr-template.md"
AGENT_INSTALL = REPO_ROOT / "INSTALL-AGENT.md"
README = REPO_ROOT / "README.md"
PROJECT_GUIDE = REPO_ROOT / "templates" / "adr-kit-guide.md"


def test_canonical_template_enforcement_example_is_valid_json():
    text = ADR_TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"## Enforcement.*?```json\s*(.*?)```", text, re.DOTALL)
    assert match is not None

    enforcement = json.loads(match.group(1))
    assert set(enforcement) == {
        "forbid_pattern",
        "forbid_import",
        "require_pattern",
        "llm_judge",
    }
    assert isinstance(enforcement["forbid_pattern"], list)
    assert isinstance(enforcement["forbid_import"], list)
    assert isinstance(enforcement["require_pattern"], list)
    assert enforcement["llm_judge"] is False


def test_filled_canonical_template_passes_strict_schema_gate(tmp_path):
    text = ADR_TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("ADR-NNN", "ADR-005")
    text = text.replace("YYYY-MM-DD", "2026-07-18")
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-005-short-imperative-title.md").write_text(
        text,
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "bin" / "adr-lint"),
            "--strict",
            "--gates",
            "schema",
            str(adr_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_readme_prominently_links_the_agent_install_runbook():
    lines = (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if "INSTALL-AGENT.md" in line]
    assert matches
    assert matches[0] < 30


def test_agent_docs_explain_json_graph_discovery_before_source_reading():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    context_skill = (REPO_ROOT / "skills" / "context" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert readme.index("ADR-INDEX.json") < readme.index("## Why")
    for text in (readme, install, context_skill):
        assert "ADR-INDEX.json" in text
        assert "adr-context" in text
        assert "Markdown" in text
    assert "Never hand-edit" in readme
    assert "must never be hand-edited" in install
    assert "Never treat it as the decision authority" in re.sub(
        r"\s+", " ", context_skill
    )


def test_agent_install_runbook_covers_native_and_portable_paths():
    text = AGENT_INSTALL.read_text(encoding="utf-8")
    required = [
        "--detect-only",
        "--dry-run",
        "Claude Code",
        "OpenAI Codex",
        "GitHub Copilot CLI",
        "## Fallback A: MCP",
        "## Fallback B: Agent Skills",
        "## Fallback C: Direct Python commands",
        "adr_context",
        "template.profile",
        "--project-root",
        "adr-migrate --plan",
        "adr-migrate --dry-run",
    ]
    assert all(item in text for item in required)


def test_agent_install_runbook_is_prominent_and_client_neutral():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    normalized_install = re.sub(r"\s+", " ", install)

    assert readme.index("[INSTALL-AGENT.md](INSTALL-AGENT.md)") < readme.index(
        "## Why"
    )
    assert "Do not read the full README" in normalized_install
    assert "scripts/install-agent-envs.py --detect-only" in install
    assert "scripts/install-agent-envs.py --dry-run" in install
    assert "scripts/install-agent-envs.py --agents auto" in install

    for native_client in ("Claude Code", "OpenAI Codex", "GitHub Copilot CLI"):
        assert native_client in install
    for portable_surface in ("MCP", "Agent Skills", "Direct Python commands"):
        assert portable_surface in install


def test_agent_install_runbook_has_project_init_and_verification_contracts():
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    normalized_install = re.sub(r"\s+", " ", install)

    assert "/adr-kit:init" in install
    assert "$adr-kit:init" in install
    assert "instead of guessing client configuration" in normalized_install
    assert "<absolute-adr-kit-checkout>" in install
    assert "<absolute-target-project>" in install
    assert "adr_context" in install
    assert "adr-lint --strict" in install
    assert "adr-migrate --plan" in install
    assert "template.profile" in install
    assert (REPO_ROOT / "docs" / "format-migration.md").is_file()

    for relative_path in (
        "scripts/install-agent-envs.py",
        "bin/adr-mcp",
        "instructions/adr.coding.md",
        "instructions/adr.review.md",
    ):
        assert (REPO_ROOT / relative_path).is_file()


def test_template_default_is_explained_for_humans_and_agents():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    project_guide = PROJECT_GUIDE.read_text(encoding="utf-8")

    for text in (readme, install, project_guide):
        assert "no authoritative format census exists" in text.lower()
        assert "agent-reliability" in text.lower()

    assert "### Why MADR is the default" in readme
    assert "4.52/5" in readme
    for text in (readme, install):
        assert "docs/research/adr-format-evaluation.md" in text
        assert "ADR-005-selectable-agent-friendly-adr-formats.md" in text

    assert "## Choosing an ADR body profile" in project_guide
    assert "`nygard`" in project_guide
    assert "`canonical`" in project_guide


def test_agent_docs_use_only_the_shipped_profile_catalog_and_templates():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    project_guide = PROJECT_GUIDE.read_text(encoding="utf-8")

    assert readme.index("adr profiles --format json") < readme.index("## Why")
    for text in (readme, install, project_guide):
        normalized = text.lower()
        assert "adr profiles --format json" in normalized
        assert "madr" in normalized
        assert "nygard" in normalized
        assert "canonical" in normalized
        assert "invent" in normalized

    for client in ("codex", "copilot"):
        skill = (
            REPO_ROOT / client / "skills" / "adr" / "SKILL.md"
        ).read_text(encoding="utf-8").lower()
        assert "adr profiles --format json" in skill
        assert "available: true" in skill
        assert "never invent" in skill


def test_install_docs_define_the_three_platform_runtime_contract():
    readme = README.read_text(encoding="utf-8")
    install = (REPO_ROOT / "INSTALL.md").read_text(encoding="utf-8")
    agent_install = AGENT_INSTALL.read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "validate.yml").read_text(
        encoding="utf-8"
    )

    for text in (readme, install, agent_install):
        assert "Windows" in text
        assert "macOS" in text
        assert "Linux" in text
        assert "Python 3.10" in text
        assert "prepar" in text.lower()

    assert "initialize plus tools/list" in install
    assert "macos-latest" in workflow
    assert "os: [ubuntu-latest, macos-latest, windows-latest]" in workflow
    assert "update the installed `.mcp.json`" not in agent_install.lower()
