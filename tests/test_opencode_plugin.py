"""Bun smoke tests for the native OpenCode plugin adapter."""

from __future__ import annotations

import json
import os
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


def _project(tmp_path: Path, adr: str = ADR) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-governed-source-path.md").write_text(adr, encoding="utf-8")
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


# ADR's frontmatter lists are flow style, which the index drops (adr-lint
# rejects them), and its Enforcement block scopes nothing. An edit alone
# retrieves nothing from it: the smoke above sees ADR-001 after its edit only
# because the prompt put it there. This ADR is scoped to src/**, so only the
# edit can bring it in.
SCOPED_ADR = ADR.replace(
    '"forbid_pattern": []',
    '"forbid_pattern": [{"pattern": "UNGOVERNED", "path_glob": "src/**", '
    '"message": "Keep src governed (ADR-001)."}]',
)
PATCH = "\n".join(
    ["*** Begin Patch", "*** Update File: src/thing.py", "@@",
     "-# governed", "+# still governed", "*** End Patch"]
)


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("edit", {"filePath": "src/thing.py"}),
        # OpenCode 1.19.0 edits through apply_patch, with the patch in
        # args.patchText and no file path, whenever its write tool is off (DEF-38).
        ("apply_patch", {"patchText": PATCH}),
    ],
)
def test_native_plugin_brings_in_the_decisions_for_the_file_an_edit_touches(
    tmp_path, tool, args
):
    project = _project(tmp_path / "project", SCOPED_ADR)
    plugin_url = (ROOT / "opencode" / "plugin.ts").as_uri()
    script = f"""
const mod = await import({json.dumps(plugin_url)});
const hooks = await mod.default(
  {{ directory: {json.dumps(str(project))}, worktree: {json.dumps(str(project))} }},
  {{ root: {json.dumps(str(ROOT))}, python: {json.dumps(sys.executable)} }}
);
const args = {json.dumps(args)};
await hooks["tool.execute.before"]({{ tool: {json.dumps(tool)}, sessionID: "before" }}, {{ args }});
await hooks["tool.execute.after"]({{ tool: {json.dumps(tool)}, sessionID: "after", args }});
const before = {{ system: [] }};
await hooks["experimental.chat.system.transform"]({{ sessionID: "before" }}, before);
const after = {{ system: [] }};
await hooks["experimental.chat.system.transform"]({{ sessionID: "after" }}, after);
console.log(JSON.stringify({{ before, after }}));
"""
    harness = tmp_path / "opencode-plugin-edit.mjs"
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
    for session in ("before", "after"):
        system = "\n".join(payload[session]["system"])
        assert "<adr-kit-context>" in system and "ADR-001" in system, session


def _run_plugin(project: Path, tmp_path: Path, options: dict, env: dict) -> dict:
    """Load the plugin, register its config, and make one edit."""
    plugin_url = (ROOT / "opencode" / "plugin.ts").as_uri()
    script = f"""
const mod = await import({json.dumps(plugin_url)});
const hooks = await mod.default(
  {{ directory: {json.dumps(str(project))}, worktree: {json.dumps(str(project))} }},
  {json.dumps({"root": str(ROOT), **options})}
);
const config = {{}};
await hooks.config(config);
await hooks["tool.execute.before"](
  {{ tool: "edit", sessionID: "interpreter" }}, {{ args: {{ filePath: "src/thing.py" }} }}
);
const system = {{ system: [] }};
await hooks["experimental.chat.system.transform"]({{ sessionID: "interpreter" }}, system);
console.log(JSON.stringify({{ command: config.mcp["adr-kit"].command, system }}));
"""
    harness = tmp_path / "opencode-plugin-interpreter.mjs"
    harness.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [BUN, "run", str(harness)],
        cwd=project,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


# macOS and most Linux distributions ship python3 and no python, and the python3
# of macOS's Command Line Tools is 3.9 (DEF-35). The stand-in for a too-old
# interpreter fails the version probe the way 3.9 would.
@pytest.mark.skipif(os.name == "nt", reason="builds a POSIX PATH from symlinks")
@pytest.mark.parametrize(
    ("present", "expected"),
    [
        ({"python3": "current"}, "python3"),
        ({"python": "current"}, "python"),
        ({"python3": "too-old", "python": "current"}, "python"),
    ],
    ids=["python3-only", "python-only", "python3-too-old"],
)
def test_native_plugin_finds_an_interpreter_that_runs_the_kit(tmp_path, present, expected):
    project = _project(tmp_path / "project", SCOPED_ADR)
    path = tmp_path / "path"
    path.mkdir()
    for name, kind in present.items():
        if kind == "current":
            (path / name).symlink_to(sys.executable)
        else:
            (path / name).write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            (path / name).chmod(0o755)
    env = {key: value for key, value in os.environ.items() if key != "ADR_KIT_PYTHON"}
    env["PATH"] = str(path)

    payload = _run_plugin(project, tmp_path, {}, env)

    assert Path(payload["command"][0]).name == expected
    assert "ADR-001" in "\n".join(payload["system"]["system"]), "the edit hook did not run"


def test_native_plugin_takes_adr_kit_python_before_its_python_option(tmp_path):
    project = _project(tmp_path / "project", SCOPED_ADR)
    env = {**os.environ, "ADR_KIT_PYTHON": sys.executable}

    payload = _run_plugin(project, tmp_path, {"python": str(tmp_path / "missing")}, env)

    assert payload["command"][0] == sys.executable
