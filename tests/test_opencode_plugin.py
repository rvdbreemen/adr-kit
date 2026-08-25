"""Bun smoke tests for the native OpenCode plugin adapter."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUN = shutil.which("bun")
pytestmark = pytest.mark.skipif(BUN is None, reason="Bun is required for the OpenCode plugin smoke")


ADR = """---
id: "ADR-001"
title: "Use the governed source path"
status: "Accepted"
date: "2026-08-14"
binding: true
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics: ["OpenCode", "hooks"]
components: ["src"]
context_scope: "selective"
format: "madr"
---

# ADR-001 Use the governed source path

## Status

Accepted, 2026-08-14.

## Context and Problem Statement

The source path is governed by an accepted decision.

## Decision Outcome

Use the governed source path for all edits.

## Alternatives Considered

- Use an ungoverned path: rejected.
- Use the governed path: accepted.

## Consequences

- The source remains discoverable.

## References

- `src/thing.py`

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
"""


def _project(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-governed-source-path.md").write_text(ADR, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "thing.py").write_text("# governed\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "adr-index"), str(adr_dir)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return tmp_path


def _run(project: Path, tmp_path: Path, session_id: str = "smoke-session") -> dict:
    plugin_url = (ROOT / "opencode" / "plugin.ts").as_uri()
    script = f"""
const mod = await import({json.dumps(plugin_url)});
const hooks = await mod.default(
  {{ directory: {json.dumps(str(project))}, worktree: {json.dumps(str(project))} }},
  {{ root: {json.dumps(str(ROOT))}, python: {json.dumps(sys.executable)} }}
);
const config = {{
  instructions: ["user-owned.md"],
  mcp: {{ "other-server": {{ type: "local", command: ["other"] }} }},
  command: {{ "adr-kit-context": {{ template: "user-owned-command" }} }},
  references: {{ "user-reference": "docs/context" }}
}};
await hooks.config(config);
const env = {{ env: {{}} }};
await hooks["shell.env"]({{ cwd: {json.dumps(str(project))} }}, env);
const message = {{ parts: [{{ type: "text", text: "Update the governed source path" }}] }};
await hooks["chat.message"]({{ sessionID: {json.dumps(session_id)} }}, message);
const system = {{ system: [] }};
await hooks["experimental.chat.system.transform"]({{ sessionID: {json.dumps(session_id)} }}, system);
const compact = {{ context: [] }};
await hooks["experimental.session.compacting"]({{ sessionID: "smoke-session" }}, compact);
const definition = {{ description: "Edit a file." }};
await hooks["tool.definition"]({{ toolID: "edit" }}, definition);
await hooks["tool.execute.before"](
  {{ tool: "edit", sessionID: {json.dumps(session_id)} }},
  {{ args: {{ filePath: "src/thing.py" }} }}
);
const editSystem = {{ system: [] }};
await hooks["experimental.chat.system.transform"]({{ sessionID: {json.dumps(session_id)} }}, editSystem);
console.log(JSON.stringify({{
  hookNames: Object.keys(hooks),
  config,
  env,
  system,
  compact,
  definition,
  editSystem
}}));
"""
    harness = tmp_path / "opencode-plugin-smoke.mjs"
    harness.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [BUN, "run", str(harness)],
        cwd=project,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_native_plugin_registers_additive_config_and_context_hooks(tmp_path):
    project = _project(tmp_path / "project")
    result = _run(project, tmp_path)

    config = result["config"]
    assert config["mcp"]["other-server"] == {"type": "local", "command": ["other"]}
    assert config["mcp"]["adr-kit"]["type"] == "local"
    assert config["mcp"]["adr-kit"]["command"][-2:] == ["--root", str(project)]
    assert str(ROOT / "skills") in config["skills"]["paths"]
    assert "user-owned.md" in config["instructions"]
    assert any(path.endswith("ADR-guide.md") for path in config["instructions"])
    assert len(config["command"]) == 17
    assert config["command"]["adr-kit-context"]["template"] == "user-owned-command"
    assert config["references"]["user-reference"] == "docs/context"
    assert Path(config["references"]["adr-decisions"]).parts[-2:] == ("docs", "adr")

    assert "chat.message" in result["hookNames"]
    assert "experimental.chat.system.transform" in result["hookNames"]
    assert "tool.execute.before" in result["hookNames"]
    assert "tool.execute.after" in result["hookNames"]
    assert result["env"]["env"]["ADR_KIT_ROOT"] == str(ROOT)
    assert "<adr-kit-instructions>" in "\n".join(result["system"]["system"])
    assert "ADR-001" in "\n".join(result["system"]["system"])
    assert "ADR-001" in "\n".join(result["compact"]["context"])
    assert "adr-kit MCP" in result["definition"]["description"]
    assert "ADR-001" in "\n".join(result["editSystem"]["system"])


def test_native_plugin_can_disable_registration_without_breaking_static_hooks(tmp_path):
    project = _project(tmp_path / "project")
    plugin_url = (ROOT / "opencode" / "plugin.ts").as_uri()
    script = f"""
const mod = await import({json.dumps(plugin_url)});
const hooks = await mod.default(
  {{ directory: {json.dumps(str(project))}, worktree: {json.dumps(str(project))} }},
  {{ root: {json.dumps(str(ROOT))}, python: {json.dumps(sys.executable)}, mcp: false, skills: false, commands: false, instructions: false, references: false, hooks: false }}
);
const config = {{}};
await hooks.config(config);
console.log(JSON.stringify({{ config, hookNames: Object.keys(hooks) }}));
"""
    harness = tmp_path / "opencode-plugin-options.mjs"
    harness.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [BUN, "run", str(harness)],
        cwd=project,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["config"] == {}
    assert "experimental.chat.system.transform" in payload["hookNames"]


def test_native_plugin_translates_automatic_grill_to_its_command_surface(tmp_path):
    project = _project(tmp_path / "project")
    now = datetime.now(timezone.utc)
    (project / "docs" / "adr" / ".adr-kit-readiness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=24)).isoformat(),
                "authoritative": False,
                "actions": [
                    {
                        "adr_id": "ADR-001",
                        "classification": "needs-human-input",
                        "command": "/adr-kit:grill ADR-001",
                        "reasons": ["open human questions"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _run(project, tmp_path, session_id=f"auto-grill-{tmp_path.name}")
    system = "\n".join(result["system"]["system"])

    assert "AUTO_GRILL_PENDING" in system
    assert "/adr-kit-grill ADR-001" in system
    assert "/adr-kit:grill ADR-001" not in system
