from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from test_adr_readiness import _write_adr

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))

from adr_hook_core import (  # noqa: E402
    _prompt_candidates_context,
    evaluate,
    load_auto_grill_context,
    parse_payload,
)


def _write_queue(project: Path, actions: list[dict]) -> None:
    adr_dir = project / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    (adr_dir / ".adr-kit-readiness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=24)).isoformat(),
                "authoritative": False,
                "actions": actions,
            }
        ),
        encoding="utf-8",
    )


def _action(
    adr_id: str = "ADR-001",
    *,
    classification: str = "needs-human-input",
    reasons: list[str] | None = None,
) -> dict:
    return {
        "adr_id": adr_id,
        "classification": classification,
        "command": f"/adr-kit:grill {adr_id}",
        "reasons": reasons or ["open human questions"],
    }


def test_prompt_hands_the_first_human_action_to_each_client(tmp_path):
    _write_queue(
        tmp_path,
        [_action("ADR-007", reasons=["active implementation link", "age 1 days"])],
    )

    assert "AUTO_GRILL_PENDING" in load_auto_grill_context(tmp_path, "claude-code-cli")
    assert "/adr-kit:grill ADR-007" in load_auto_grill_context(
        tmp_path, "claude-code-cli"
    )
    assert "$adr-kit:grill ADR-007" in load_auto_grill_context(tmp_path, "codex-cli")
    assert "adr-kit:grill ADR-007" in load_auto_grill_context(
        tmp_path, "github-copilot-cli"
    )


def test_mechanical_queue_items_are_skipped_until_human_work_is_ready(tmp_path):
    _write_queue(
        tmp_path,
        [
            _action("ADR-001", classification="needs-mechanical-fix"),
            _action("ADR-002", classification="ready-for-confirmation"),
        ],
    )

    context = load_auto_grill_context(tmp_path, "codex-cli")
    assert "ADR-002" in context
    assert "ADR-001" not in context


def test_one_automatic_handoff_is_emitted_per_session(tmp_path):
    _write_queue(tmp_path, [_action("ADR-003")])

    first = load_auto_grill_context(tmp_path, "claude-code-cli", "session-once")
    second = load_auto_grill_context(tmp_path, "claude-code-cli", "session-once")

    assert "AUTO_GRILL_PENDING" in first
    assert second == ""


def test_auto_handoff_honours_project_and_environment_opt_out(tmp_path, monkeypatch):
    _write_queue(tmp_path, [_action()])
    config = tmp_path / "docs" / "adr" / ".adr-kit.json"
    config.write_text(json.dumps({"grill": {"auto_start": False}}), encoding="utf-8")

    assert load_auto_grill_context(tmp_path, "claude-code-cli") == ""

    config.write_text(json.dumps({"grill": {"auto_start": True}}), encoding="utf-8")
    monkeypatch.setenv("ADR_KIT_AUTO_GRILL_DISABLE", "1")
    assert load_auto_grill_context(tmp_path, "claude-code-cli") == ""


def test_user_prompt_injects_auto_handoff_but_session_start_does_not(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, open_questions="- [ ] Who owns the decision?")
    subprocess.run(
        [sys.executable, str(ROOT / "bin" / "adr-index"), str(adr_dir)],
        check=True,
        capture_output=True,
    )
    _write_queue(tmp_path, [_action()])

    prompt = parse_payload(
        json.dumps(
            {
                "cwd": str(tmp_path),
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session-1",
                "prompt": "continue the implementation",
            }
        ).encode(),
        "codex-cli",
    )
    session = parse_payload(
        json.dumps(
            {
                "cwd": str(tmp_path),
                "hook_event_name": "SessionStart",
                "session_id": "session-1",
            }
        ).encode(),
        "codex-cli",
    )
    assert prompt is not None and session is not None

    prompt_context, prompt_kind = evaluate(prompt)
    session_context, session_kind = evaluate(session)

    assert prompt_kind == "prompt"
    assert "AUTO_GRILL_PENDING" in prompt_context
    assert "$adr-kit:grill ADR-001" in prompt_context
    assert session_kind == "session"
    assert "AUTO_GRILL_PENDING" not in session_context


def test_prompt_context_keeps_selection_instruction_after_auto_handoff():
    context = _prompt_candidates_context(
        ["Accepted ADR candidates for this prompt:\n- ADR-001"],
        "AUTO_GRILL_PENDING: start /adr-kit:grill ADR-002",
    )

    assert len(context) <= 4096
    assert context.startswith("AUTO_GRILL_PENDING")
    assert context.endswith(
        "These are retrieval candidates, not confirmed matches: apply "
        "the ones that actually govern this work and ignore the rest."
    )


@pytest.mark.skipif(
    sys.platform != "win32"
    or not (ROOT / "hooks" / "bin" / "windows-x64" / "adr-hook.exe").is_file(),
    reason="Windows native hook host",
)
def test_native_prompt_handoff_matches_the_python_contract(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, open_questions="- [ ] Who owns the decision?")
    subprocess.run(
        [sys.executable, str(ROOT / "bin" / "adr-index"), str(adr_dir)],
        check=True,
        capture_output=True,
    )
    _write_queue(tmp_path, [_action()])
    result = subprocess.run(
        [
            str(ROOT / "hooks" / "bin" / "windows-x64" / "adr-hook.exe"),
            "--client",
            "codex-cli",
            "--event",
            "UserPromptSubmit",
        ],
        input=json.dumps(
            {
                "cwd": str(tmp_path),
                "session_id": f"native-auto-grill-{os.getpid()}-{tmp_path.name}",
                "prompt": "continue",
            }
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert "AUTO_GRILL_PENDING" in result.stdout
    assert "$adr-kit:grill ADR-001" in result.stdout
