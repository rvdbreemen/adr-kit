"""Bun harness for the native OMP extension (ADR-050).

The extension is driven through a stand-in for OMP's `ExtensionAPI`: the
harness records the handlers it registers, then calls them with the event and
context shapes OMP 18.12 passes, and prints what each handler returned.
"""

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
pytestmark = pytest.mark.skipif(BUN is None, reason="Bun is required for the OMP extension harness")

# Scoped to src/** so an edit alone brings it in, and frontmatter in block
# style so the index keeps its topics for prompt retrieval.
ADR = """---
id: "ADR-001"
title: "Use the governed source path"
status: "Accepted"
date: "2026-10-21"
binding: true
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "governed source path"
components:
  - "src"
context_scope: "selective"
format: "madr"
---

# ADR-001 Use the governed source path

## Status

Accepted, 2026-10-21.

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
  "forbid_pattern": [{"pattern": "UNGOVERNED", "path_glob": "src/**", "message": "Keep src governed (ADR-001)."}],
  "forbid_import": [],
  "require_pattern": []
}
```
"""


def _project(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-governed-source-path.md").write_text(ADR, encoding="utf-8")
    (adr_dir / ".adr-kit.json").write_text("{}\n", encoding="utf-8")
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


def _drive(project: Path, tmp_path: Path, steps: str, env: dict | None = None) -> dict:
    """Load the extension, run `steps` (JS using `call` and `out`), print `out`."""
    extension = (ROOT / "omp" / "extension.ts").as_uri()
    script = f"""
const handlers = {{}};
const pi = {{ on(event, handler) {{ (handlers[event] ||= []).push(handler); }}, setLabel() {{}} }};
const mod = await import({json.dumps(extension)});
mod.default(pi);
const cwd = {json.dumps(str(project))};
const main = {{ cwd, agent: {{ kind: "main" }}, sessionManager: {{ getSessionId: () => "omp-main" }} }};
const sub = {{ cwd, agent: {{ kind: "sub" }}, sessionManager: {{ getSessionId: () => "omp-sub" }} }};
async function call(event, payload, ctx = main) {{
  let result;
  for (const handler of handlers[event] || []) result = await handler(payload, ctx);
  return result ?? null;
}}
const out = {{ registered: Object.keys(handlers) }};
{steps}
out.adrKitRoot = process.env.ADR_KIT_ROOT ?? null;
console.log(JSON.stringify(out));
"""
    harness = tmp_path / "omp-extension-harness.mjs"
    harness.write_text(script, encoding="utf-8")
    run_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"ADR_KIT_ROOT", "ADR_KIT_HOST_CLIENT", "ADR_KIT_NO_LLM"}
    }
    run_env["ADR_KIT_PYTHON"] = sys.executable
    run_env.update(env or {})
    result = subprocess.run(
        [BUN, "run", str(harness)],
        cwd=project,
        env=run_env,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_a_prompt_brings_in_its_decisions_and_records_omp_as_the_judge_host(tmp_path):
    project = _project(tmp_path / "project")
    out = _drive(
        project,
        tmp_path,
        """
await call("session_start", { type: "session_start" });
out.start = await call("before_agent_start", {
  type: "before_agent_start",
  prompt: "Update the governed source path",
  systemPrompt: ["base prompt"],
});
""",
    )

    message = out["start"]["message"]
    assert message["display"] is False
    assert "<adr-kit-context>" in message["content"]
    assert "ADR-001" in message["content"]
    system = out["start"]["systemPrompt"]
    assert system[0] == "base prompt"
    assert "<adr-kit-instructions>" in system[-1]
    local = json.loads((project / "docs" / "adr" / ".adr-kit.local.json").read_text(encoding="utf-8"))
    assert local["judge"]["host_client"] == "omp-cli"
    # Skills resolve ${ADR_KIT_ROOT:-${CLAUDE_PLUGIN_ROOT}}; OMP provides neither.
    assert Path(out["adrKitRoot"]) == ROOT


def test_a_root_the_user_set_is_left_in_place(tmp_path):
    project = _project(tmp_path / "project")
    chosen = str(tmp_path / "elsewhere")

    out = _drive(project, tmp_path, "", env={"ADR_KIT_ROOT": chosen})

    assert out["adrKitRoot"] == chosen
    assert "tool_call" in out["registered"]


@pytest.mark.parametrize(
    "tool, tool_input",
    [
        ("edit", {"path": "src/thing.py"}),
        # A large write must still be judged: the hook drops input over 64 KiB,
        # so only the path may cross.
        ("write", {"path": "src/thing.py", "content": "x" * 100_000}),
        ("ast_edit", {"paths": ["src/thing.py", "src/other.py"]}),
    ],
)
def test_an_edit_brings_in_the_decisions_for_the_files_it_touches(tmp_path, tool, tool_input):
    project = _project(tmp_path / "project")
    payload = json.dumps({"toolName": tool, "input": tool_input})
    out = _drive(
        project,
        tmp_path,
        f"""
const payload = {payload};
out.before = await call("tool_call", {{ type: "tool_call", toolCallId: "1", ...payload }});
out.after = await call("tool_result", {{ type: "tool_result", toolCallId: "1", content: [], isError: false, ...payload }});
out.failed = await call("tool_result", {{ type: "tool_result", toolCallId: "2", content: [], isError: true, ...payload }});
""",
    )

    for moment in ("before", "after"):
        assert out[moment]["additionalContext"].startswith("<adr-kit-context>"), out
        assert "ADR-001" in out[moment]["additionalContext"], out
        assert "block" not in out[moment]
    assert out["failed"] is None


def test_a_hook_that_cannot_run_never_blocks_a_tool(tmp_path):
    project = _project(tmp_path / "project")
    out = _drive(
        project,
        tmp_path,
        """
out.shell = await call("tool_call", { type: "tool_call", toolCallId: "1", toolName: "bash", input: { command: "gh pr create" } });
out.edit = await call("tool_call", { type: "tool_call", toolCallId: "2", toolName: "edit", input: { path: "src/thing.py" } });
out.prompt = await call("before_agent_start", { type: "before_agent_start", prompt: "hello", systemPrompt: [] });
""",
        env={"ADR_KIT_PYTHON": str(tmp_path / "no-such-python")},
    )

    assert out["shell"] is None
    assert out["edit"] is None
    assert "message" not in out["prompt"]


def test_an_explicit_guard_deny_blocks_the_pull_request_command(tmp_path):
    project = _project(tmp_path / "project")
    # A runtime root whose hook answers like the shared guard does for a branch
    # that violates an Accepted ADR.
    fake = tmp_path / "fake-root"
    (fake / "bin").mkdir(parents=True)
    (fake / "bin" / "adr-mcp").write_text("", encoding="utf-8")
    (fake / "skills").mkdir()
    (fake / "hooks").mkdir()
    (fake / "hooks" / "adr-hook.py").write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "if 'gh pr create' in payload.get('tool_input', {}).get('command', ''):\n"
        "    print(json.dumps({'hookSpecificOutput': {'permissionDecision': 'deny',"
        " 'permissionDecisionReason': 'ADR-001 violated'}}))\n",
        encoding="utf-8",
    )
    out = _drive(
        project,
        tmp_path,
        """
out.pr = await call("tool_call", { type: "tool_call", toolCallId: "1", toolName: "bash", input: { command: "gh pr create --fill" } });
out.other = await call("tool_call", { type: "tool_call", toolCallId: "2", toolName: "bash", input: { command: "git status" } });
""",
        env={"ADR_KIT_ROOT": str(fake)},
    )

    assert out["pr"] == {"block": True, "reason": "ADR-001 violated"}
    assert out["other"] is None


def test_a_subagent_and_a_compaction_carry_the_main_session_context(tmp_path):
    project = _project(tmp_path / "project")
    out = _drive(
        project,
        tmp_path,
        """
await call("before_agent_start", { type: "before_agent_start", prompt: "Update the governed source path", systemPrompt: [] });
out.child = await call("before_agent_start", { type: "before_agent_start", prompt: "subtask", systemPrompt: [] }, sub);
out.childAgain = await call("before_agent_start", { type: "before_agent_start", prompt: "next", systemPrompt: [] }, sub);
out.compact = await call("session.compacting", { sessionId: "omp-main", messages: [] });
""",
    )

    assert "ADR-001" in out["child"]["message"]["content"]
    assert "message" not in out["childAgain"]
    assert "ADR-001" in "\n".join(out["compact"]["context"])


def test_an_automatic_grill_handoff_names_the_omp_skill(tmp_path):
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
    out = _drive(
        project,
        tmp_path,
        f"""
out.start = await call("before_agent_start", {{ type: "before_agent_start", prompt: "carry on", systemPrompt: [] }},
  {{ ...main, sessionManager: {{ getSessionId: () => {json.dumps("grill-" + tmp_path.name)} }} }});
""",
    )

    content = out["start"]["message"]["content"]
    assert "AUTO_GRILL_PENDING" in content
    assert "/skill:grill ADR-001" in content
    assert "/adr-kit:grill" not in content
