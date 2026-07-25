"""Normalized hook protocol, client adapters, and fail-open behavior."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
NATIVE = HOOKS / "bin" / "windows-x64" / "adr-hook.exe"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from adapters import ADAPTERS
from adr_hook_core import (
    MAX_CONTEXT_CHARS,
    MAX_INPUT_BYTES,
    evaluate,
    parse_payload,
)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "Project with spaces \u2603"
    adr = project / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-INDEX.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "adrs": [
                    {
                        "id": "ADR-001",
                        "title": "Use bounded hooks",
                        "path": "ADR-001-hooks.md",
                        "format": "madr",
                        "status": "Accepted",
                        "date": "2026-07-23",
                        "decision_summary": "Hook work must remain deterministic and fail open.",
                        "scope": {"path_globs": ["src/hooks/**"]},
                        "metadata": {},
                        "context_scope": "global",
                        "topics": ["deterministic lifecycle hooks"],
                        "aliases": [],
                        "components": ["hook runtime"],
                        "symbols": [],
                        "decision_contract": {},
                    },
                    {
                        "id": "ADR-002",
                        "title": "Use SQLite",
                        "path": "ADR-002-storage.md",
                        "format": "madr",
                        "status": "Accepted",
                        "date": "2026-07-23",
                        "decision_summary": "Store durable records in SQLite.",
                        "scope": {"path_globs": ["src/store/**"]},
                        "metadata": {},
                        "context_scope": "selective",
                        "topics": ["sqlite storage"],
                        "aliases": [],
                        "components": ["storage"],
                        "symbols": [],
                        "decision_contract": {},
                    },
                    {
                        "id": "ADR-003",
                        "title": "Candidate lifecycle hooks",
                        "path": "ADR-003-proposal.md",
                        "format": "madr",
                        "status": "Proposed",
                        "date": "2026-07-23",
                        "decision_summary": "Candidate deterministic lifecycle hook behavior.",
                        "scope": {"path_globs": ["**"]},
                        "metadata": {},
                        "context_scope": "selective",
                        "topics": ["deterministic lifecycle hooks"],
                        "aliases": [],
                        "components": ["hook runtime"],
                        "symbols": [],
                        "decision_contract": {},
                    },
                ],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )
    return project


@pytest.mark.parametrize(
    ("native", "expected"),
    [
        ("SessionStart", "SessionStart"),
        ("sessionStart", "SessionStart"),
        ("userPromptSubmitted", "UserPromptSubmit"),
        ("PreToolUse", "PreToolUse"),
    ],
)
def test_native_event_naming_is_normalized(tmp_path, native, expected):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps({"cwd": str(project), "hookEventName": native}).encode(),
        "github-copilot-cli",
    )
    assert envelope is not None
    assert envelope.event == expected


def test_prompt_ranking_is_deterministic_bounded_and_source_linked(tmp_path):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Implement deterministic lifecycle hooks",
            }
        ).encode(),
        "codex-cli",
    )
    assert envelope
    first = evaluate(envelope)
    second = evaluate(envelope)
    assert first == second
    assert first[1] == "prompt"
    assert "ADR-001" in first[0]
    assert "Governing Accepted" in first[0]
    assert "ADR-003" in first[0]
    assert "Advisory Proposed" in first[0]
    assert "source: docs/adr/ADR-001-hooks.md" in first[0]
    assert len(first[0]) <= MAX_CONTEXT_CHARS


@pytest.mark.parametrize("tool", ["Edit", "MultiEdit", "Write", "apply_patch"])
def test_pre_edit_filters_write_aliases_and_resolves_safe_paths(tmp_path, tool):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": {"file_path": "src/hooks/runtime.py"},
            }
        ).encode(),
        "claude-code-cli",
    )
    assert envelope
    context, kind = evaluate(envelope)
    assert kind == "pre-edit"
    assert "ADR-001" in context
    assert "ADR-002" not in context

    hostile = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": {"file_path": "../outside.py"},
            }
        ).encode(),
        "claude-code-cli",
    )
    assert hostile and evaluate(hostile) == ("", "noop")


def test_copilot_uses_post_edit_backstop_not_false_pre_context(tmp_path):
    project = _project(tmp_path)
    base = {
        "cwd": str(project),
        "toolName": "Edit",
        "toolInput": {"filePath": "src/hooks/runtime.py"},
    }
    pre = parse_payload(
        json.dumps({**base, "hookEventName": "PreToolUse"}).encode(),
        "github-copilot-cli",
    )
    post = parse_payload(
        json.dumps({**base, "hookEventName": "PostToolUse"}).encode(),
        "github-copilot-cli",
    )
    assert pre and post
    pre_context, pre_kind = evaluate(pre)
    post_context, post_kind = evaluate(post)
    assert ADAPTERS["github-copilot-cli"]("PreToolUse", pre_context, pre_kind) == {}
    assert "additionalContext" in ADAPTERS["github-copilot-cli"](
        "PostToolUse", post_context, post_kind
    )


def test_subagent_and_precompact_preserve_only_selected_parent_context(tmp_path):
    project = _project(tmp_path)
    parent = "parent ADR bundle " * 1000
    subagent = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "SubagentStart",
                "parent_context": parent,
            }
        ).encode(),
        "codex-cli",
    )
    compact = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PreCompact",
                "parent_context": parent,
            }
        ).encode(),
        "codex-cli",
    )
    assert subagent and compact
    assert evaluate(subagent)[0] == parent[:MAX_CONTEXT_CHARS]
    assert evaluate(compact)[0] == parent[:MAX_CONTEXT_CHARS]

    empty = parse_payload(
        json.dumps(
            {"cwd": str(project), "hook_event_name": "PreCompact"}
        ).encode(),
        "codex-cli",
    )
    assert empty and evaluate(empty) == ("", "noop")


def test_session_orientation_uses_only_explicit_global_accepted_adrs(tmp_path):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps(
            {"cwd": str(project), "hook_event_name": "SessionStart"}
        ).encode(),
        "codex-cli",
    )
    assert envelope
    context, kind = evaluate(envelope)
    assert kind == "session"
    assert "ADR-001" in context
    assert "ADR-002" not in context
    assert "ADR-003" not in context


@pytest.mark.parametrize(
    "event",
    ["Stop", "SubagentStop", "SessionEnd", "PermissionRequest", "Notification", "Interrupt", "Unknown"],
)
def test_unsupported_and_terminal_events_are_successful_noops(tmp_path, event):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps({"cwd": str(project), "hook_event_name": event}).encode(),
        "claude-code-cli",
    )
    assert envelope and evaluate(envelope) == ("", "noop")


def test_malformed_oversized_and_disabled_payloads_fail_open(tmp_path):
    assert parse_payload(b"{", "codex-cli") is None
    assert parse_payload(b"x" * (MAX_INPUT_BYTES + 1), "codex-cli") is None
    assert parse_payload(
        b'{"adr_kit_disabled":true}', "codex-cli"
    ) is None
    result = subprocess.run(
        [
            sys.executable,
            str(HOOKS / "adr-hook.py"),
            "--client",
            "codex-cli",
        ],
        input="{",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.skipif(sys.platform != "win32" or not NATIVE.is_file(), reason="Windows native hook host")
def test_native_host_matches_session_prompt_and_edit_outcomes(tmp_path):
    project = _project(tmp_path)
    cases = [
        (
            "SessionStart",
            {"cwd": str(project), "hook_event_name": "SessionStart"},
            "ADR-001",
        ),
        (
            "UserPromptSubmit",
            {
                "cwd": str(project),
                "hook_event_name": "UserPromptSubmit",
                "prompt": "deterministic hooks",
            },
            "ADR-001",
        ),
        (
            "PreToolUse",
            {
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "src/hooks/native.rs"},
            },
            "ADR-001",
        ),
    ]
    for event, payload, expected in cases:
        envelope = parse_payload(
            json.dumps(payload).encode(),
            "claude-code-cli",
            event,
        )
        assert envelope
        python_context, _ = evaluate(envelope)
        result = subprocess.run(
            [
                str(NATIVE),
                "--client",
                "claude-code-cli",
                "--event",
                event,
            ],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
        )
        assert result.returncode == 0
        response = json.loads(result.stdout)
        native_context = response["hookSpecificOutput"]["additionalContext"]
        assert expected in native_context
        assert set(re.findall(r"ADR-\d{3,4}", native_context)) == set(
            re.findall(r"ADR-\d{3,4}", python_context)
        )
        if event == "SessionStart":
            assert "ADR-002" not in native_context
        if event in {"UserPromptSubmit", "PreToolUse"}:
            assert "Governing Accepted" in native_context
            assert "Advisory Proposed" in native_context


@pytest.mark.parametrize("native", [False, True])
def test_duplicate_event_is_a_successful_noop(tmp_path, native):
    if native and (sys.platform != "win32" or not NATIVE.is_file()):
        pytest.skip("Windows native hook host")
    project = _project(tmp_path)
    payload = json.dumps(
        {
            "cwd": str(project),
            "hook_event_name": "SessionStart",
            "session_id": f"duplicate-{uuid.uuid4()}",
        }
    )
    command = (
        [str(NATIVE), "--client", "codex-cli", "--event", "SessionStart"]
        if native
        else
        [
            sys.executable,
            str(HOOKS / "adr-hook.py"),
            "--client",
            "codex-cli",
            "--event",
            "SessionStart",
        ]
    )
    first = subprocess.run(
        command, input=payload, text=True, capture_output=True, check=False
    )
    second = subprocess.run(
        command, input=payload, text=True, capture_output=True, check=False
    )
    assert first.returncode == second.returncode == 0
    assert first.stdout
    assert second.stdout == ""
