"""Every registered event, driven through the real entrypoint, on every client.

Three defects shipped in v0.44.0 that the existing hook tests could not see,
because each of them called into the hook's internals and so never exercised the
layer that was broken:

* `adr_pr_guard.py` was absent from the generated Codex and Copilot trees, so
  `hooks/adr-hook.py` raised `ModuleNotFoundError` at import and **every** event
  on those two clients exited 1 with no output;
* `plan-exit` was registered with `"command": "plan-exit"`, which reaches
  `normalize()` as the literal event name, compacts to `planexit`, misses
  `EVENT_ALIASES` and falls through to noop. Twenty-four tests passed over the
  dead path because `_envelope` passed `event=None` and let the payload win;
* the entrypoint printed through the platform's text layer, so on a default
  Windows console the frame came out as cp1252 and a title outside that page
  deleted the whole injection into the fail-open catch.

What they have in common is that the failing step is the dispatch, and the
existing suite tested everything on either side of it. This module drives the
process: the same command line the generated `hooks.json` names, the payload a
client would send, and an assertion on raw bytes.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((REPO_ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8"))

# Which hook tree answers for which client id. The two generated trees are the
# ones that were broken; testing only `hooks/` is what let that ship.
TREES = {
    "claude-code-cli": REPO_ROOT / "hooks",
    "codex-cli": REPO_ROOT / "codex" / "hooks",
    "github-copilot-cli": REPO_ROOT / "copilot" / "hooks",
}

# One payload per manifest event id, shaped like the client sends it. The
# `expect_output` flag says whether this fixture warrants a non-empty frame:
# `pr-create` is a gate that stays silent unless the branch violates something,
# and the two context-passing events carry nothing in a fresh session.
CASES = {
    "session-start": ({"hook_event_name": "SessionStart"}, True),
    "user-prompt-submit": (
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "update the retrieval and protocol handling in src",
        },
        True,
    ),
    "pre-tool-use": (
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/thing.py"},
        },
        True,
    ),
    "post-tool-use": (
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/thing.py"},
        },
        True,
    ),
    "plan-exit": (
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {"plan": "Replace the retrieval layer with a new store."},
        },
        True,
    ),
    "pr-create": (
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr create --title x --body y"},
        },
        False,
    ),
    "subagent-start": ({"hook_event_name": "SubagentStart"}, False),
    "pre-compact": ({"hook_event_name": "PreCompact"}, False),
}

# U+2192 and U+2265 are both outside cp1252. ADR-016's own title carries the
# first one, which is how the encoding defect was found rather than imagined.
AWKWARD_TITLE = "Serve Both Protocol Eras → One Process (≥ 2 clients)"


ADR_BODY = f"""---
id: "ADR-001"
title: "{AWKWARD_TITLE}"
status: "Accepted"
date: "2026-05-01"
binding: true
gate: null
context_scope: "global"
topics: ["retrieval", "protocol"]
components: ["src"]
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
---

# ADR-001 {AWKWARD_TITLE}

## Status

Accepted, 2026-05-01.

## Context

The retrieval layer in src/ has to answer both protocol eras.

## Decision

Serve both protocol eras from one process, reading src/ only.

## Alternatives Considered

- Two processes: rejected, because the era is a property of the frame.
- Refuse the older era: rejected, because clients in the wild still speak it.

## Consequences

**Positive:**
- One process to reason about.

**Negative:**
- The dispatch has to stay a pure function of the frame.

## Related Decisions

- None.

## References

- src/retrieval.py

## Enforcement

```json
{{
  "forbid_pattern": [
    {{
      "pattern": "\\\\bpickle\\\\b",
      "path_glob": "src/**",
      "message": "The frame is parsed, never unpickled (ADR-001)."
    }}
  ],
  "forbid_import": [],
  "require_pattern": [],
  "llm_judge": false
}}
```
"""


@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    """A project shaped like a user's: real ADR markdown, index generated.

    A hand-written `ADR-INDEX.json` is not enough. `_query` asks the shared
    engine with `strict_index=True`, and an index with no markdown behind it is
    stale by definition, so every event would fail open to noop and the test
    would pass for the wrong reason - which is exactly the failure mode this
    module exists to catch.
    """
    root = tmp_path_factory.mktemp("hook-matrix")
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-serve-both-protocol-eras.md").write_text(ADR_BODY, encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("# governed by ADR-001\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-index"), str(adr_dir)],
        capture_output=True, check=True,
    )
    return root


def _run(tree: Path, client: str, command: str, payload: dict, workspace: Path):
    body = dict(payload)
    body["cwd"] = str(workspace)
    return subprocess.run(
        [sys.executable, str(tree / "adr-hook.py"), "--client", client, "--event", command],
        input=json.dumps(body).encode("utf-8"),
        capture_output=True,
    )


def _events():
    for event in MANIFEST["events"]:
        for client, native in event["clients"].items():
            if native is None:
                continue  # the client does not offer this moment; R17 allows that
            yield pytest.param(
                event["id"], event["command"], client,
                id=f"{event['id']}-{client}",
            )


@pytest.mark.parametrize(("event_id", "command", "client"), list(_events()))
def test_every_registered_event_dispatches_on_every_client(
    event_id, command, client, workspace
):
    """The entrypoint must not exit non-zero, and must not silently no-op.

    A hook that exits 1 is a broken import; a hook that exits 0 with no bytes
    where the fixture warrants output is a dispatch that fell through to noop.
    Both shipped, and neither was visible from inside the module.
    """
    payload, expect_output = CASES[event_id]

    result = _run(TREES[client], client, command, payload, workspace)

    assert result.returncode == 0, (
        f"{event_id} on {client} exited {result.returncode}: "
        f"{result.stderr.decode('utf-8', 'replace')[-400:]}"
    )
    if expect_output:
        assert result.stdout, (
            f"{event_id} on {client} produced no frame; the dispatch reached noop"
        )


@pytest.mark.parametrize("client", sorted(TREES))
def test_the_frame_is_utf8_bytes_whatever_the_console_encoding_is(client, workspace):
    """Assert on raw bytes: the defect was invisible in decoded text.

    `print()` on a default Windows console encodes cp1252, so an em dash left
    byte 0x97 in the stream - not valid UTF-8 - and a character cp1252 cannot
    represent raised `UnicodeEncodeError` into the fail-open catch, which
    returned zero bytes and exit 0.
    """
    payload, _ = CASES["user-prompt-submit"]

    result = _run(TREES[client], client, "user-prompt-submit", payload, workspace)

    assert result.stdout, "no frame to check"
    decoded = result.stdout.decode("utf-8")  # raises on the cp1252 regression
    assert "→" in decoded, "the awkward character did not survive the frame"
    assert json.loads(decoded.splitlines()[0])


@pytest.mark.parametrize(
    "tree", [pytest.param(path, id=client) for client, path in sorted(TREES.items())]
)
def test_the_native_host_is_opt_in_until_it_passes_parity(tree):
    """The dispatcher must not silently prefer the native binary.

    Rebuilt from current source and measured against the Python oracle on this
    repository, the Windows host returned one of four governing ADRs before an
    edit, four of five at prompt time, and nothing for ExitPlanMode. Because
    `run-hook.cmd` preferred it whenever it existed, a fix landing in Python
    changed nothing on the platform `clients/capabilities.json` marks
    release-required - which is how two of this release's defects stayed
    invisible. Restoring the preference is gated on the parity certification
    `hooks/native/README.md` describes, so this test guards the gate.
    """
    dispatcher = (tree / "run-hook.cmd").read_text(encoding="utf-8")

    for line in dispatcher.splitlines():
        stripped = line.strip()
        if stripped.startswith("REM") or stripped.startswith("#"):
            continue
        if "ADR_HOOK_NATIVE" in stripped and stripped.startswith("if "):
            assert "ADR_KIT_NATIVE_HOOK" in stripped, stripped
        if stripped.startswith("if ") and '"$NATIVE"' in stripped:
            assert "ADR_KIT_NATIVE_HOOK" in stripped, stripped


@pytest.mark.parametrize("client", ["codex-cli", "github-copilot-cli"])
def test_every_module_the_entrypoint_imports_exists_in_that_clients_tree(client):
    """The invariant, not the file list.

    Adding `adr_pr_guard.py` to `HOOK_RUNTIME_FILES` fixes one omission. This
    fails on the next one: the generated entrypoint may not import a sibling
    that the generated tree does not contain.
    """
    tree = TREES[client]
    source = (tree / "adr-hook.py").read_text(encoding="utf-8")

    missing = []
    for line in source.splitlines():
        if not line.startswith("from ") or " import " not in line:
            continue
        module = line.split()[1]
        if module.startswith(("_", ".")) or module == "__future__":
            continue
        candidate = tree / module.replace(".", "/")
        if candidate.with_suffix(".py").exists() or (candidate / "__init__.py").exists():
            continue
        if module in sys.stdlib_module_names:
            continue
        missing.append(module)

    assert not missing, f"{client} entrypoint imports {missing}, absent from {tree}"
