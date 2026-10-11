"""A default install turns the LLM layers on and asks once (TASK-233, ADR-049).

The common install route (a client's own plugin install) never runs the
installer that used to record the judge's host client, so the LLM layers stayed
silently off. The session hook now records the client the session runs in, and
the next prompt asks the user, once, whether to keep the layers on.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from adr_hook_core import evaluate, parse_payload  # noqa: E402

# Gate adr-llm-default-on-v1 (ADR-049)
GATE_ADR_LLM_DEFAULT_ON_V1 = "adr-llm-default-on-v1"

LOCAL = ".adr-kit.local.json"


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "docs" / "adr").mkdir(parents=True)
    (project / ".git").mkdir()
    return project


def _local(project: Path) -> dict:
    path = project / "docs" / "adr" / LOCAL
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _event(project: Path, client: str, event: str, prompt: str | None = None):
    payload = {"cwd": str(project), "hook_event_name": event}
    if prompt is not None:
        payload["prompt"] = prompt
    envelope = parse_payload(json.dumps(payload).encode(), client)
    assert envelope is not None
    return evaluate(envelope)


def test_session_start_records_the_client_the_session_runs_in(tmp_path):
    for client in ("claude-code-cli", "codex-cli", "github-copilot-cli"):
        project = _project(tmp_path / client)
        _event(project, client, "SessionStart")
        assert _local(project)["judge"]["host_client"] == client


def test_the_exclude_entry_keeps_the_file_out_of_git(tmp_path):
    project = _project(tmp_path)
    _event(project, "claude-code-cli", "SessionStart")
    exclude = (project / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert "docs/adr/.adr-kit.local.json" in exclude.splitlines()


def test_an_existing_choice_is_never_replaced(tmp_path):
    project = _project(tmp_path)
    (project / "docs" / "adr" / LOCAL).write_text(
        json.dumps({"judge": {"host_client": "codex-cli"}}), encoding="utf-8"
    )
    _event(project, "claude-code-cli", "SessionStart")
    assert _local(project)["judge"]["host_client"] == "codex-cli"


def test_nothing_is_recorded_when_the_judge_pass_is_switched_off(tmp_path):
    for where in (".adr-kit.json", LOCAL):
        project = _project(tmp_path / where.strip("."))
        (project / "docs" / "adr" / where).write_text(
            json.dumps({"judge": {"llm_enabled": False}}), encoding="utf-8"
        )
        _event(project, "claude-code-cli", "SessionStart")
        assert "host_client" not in (_local(project).get("judge") or {})


def test_a_client_without_a_host_command_records_nothing(tmp_path):
    project = _project(tmp_path)
    _event(project, "some-other-cli", "SessionStart")
    assert "host_client" not in (_local(project).get("judge") or {})


def test_no_adr_directory_means_nothing_is_written(tmp_path):
    project = tmp_path / "plain"
    project.mkdir()
    _event(project, "claude-code-cli", "SessionStart")
    assert not (project / "docs").exists()


def test_an_unreadable_local_file_is_left_alone(tmp_path):
    project = _project(tmp_path)
    (project / "docs" / "adr" / LOCAL).write_text("{not json", encoding="utf-8")
    context, _ = _event(project, "claude-code-cli", "SessionStart")
    assert (project / "docs" / "adr" / LOCAL).read_text(encoding="utf-8") == "{not json"


def test_the_first_prompt_records_too_for_clients_without_session_start(tmp_path):
    project = _project(tmp_path)
    _event(project, "codex-cli", "UserPromptSubmit", prompt="add a cache")
    assert _local(project)["judge"]["host_client"] == "codex-cli"


def test_the_next_prompt_asks_once_and_names_the_switches(tmp_path):
    project = _project(tmp_path)
    _event(project, "claude-code-cli", "SessionStart")
    context, _ = _event(project, "claude-code-cli", "UserPromptSubmit", prompt="add a cache")
    assert "keep them on" in context
    for switch in ("judge.llm_enabled", "suggest.enabled", "guardian.llm_enabled", "llm.confirmed"):
        assert switch in context
    assert "--local" in context
    # Asked once per day: the next prompt in the same window stays quiet.
    again, _ = _event(project, "claude-code-cli", "UserPromptSubmit", prompt="and tests")
    assert "keep them on" not in again


def test_an_unanswered_question_is_asked_again_after_the_cooldown(tmp_path):
    project = _project(tmp_path)
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    (project / "docs" / "adr" / LOCAL).write_text(
        json.dumps({"judge": {"host_client": "claude-code-cli"}, "llm": {"asked_at": stale}}),
        encoding="utf-8",
    )
    context, _ = _event(project, "claude-code-cli", "UserPromptSubmit", prompt="next task")
    assert "keep them on" in context


def test_a_confirmed_answer_ends_the_question(tmp_path):
    project = _project(tmp_path)
    (project / "docs" / "adr" / LOCAL).write_text(
        json.dumps({"judge": {"host_client": "claude-code-cli"}, "llm": {"confirmed": "2026-10-06"}}),
        encoding="utf-8",
    )
    context, _ = _event(project, "claude-code-cli", "UserPromptSubmit", prompt="next task")
    assert "keep them on" not in context


def test_the_kill_switch_suppresses_the_question(tmp_path, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.setenv("ADR_KIT_NO_LLM", "1")
    context, _ = _event(project, "claude-code-cli", "UserPromptSubmit", prompt="next task")
    assert "keep them on" not in context


def test_opencode_records_its_own_host_not_claude(tmp_path, monkeypatch):
    """OpenCode's plugin renders as claude-code-cli but names its own host.

    Before TASK-233 an OpenCode user would have had `claude -p` recorded as
    the judge's host. The plugin now sets ADR_KIT_HOST_CLIENT=opencode-cli.
    """
    project = _project(tmp_path)
    monkeypatch.setenv("ADR_KIT_HOST_CLIENT", "opencode-cli")
    _event(project, "claude-code-cli", "UserPromptSubmit", prompt="first message")
    assert _local(project)["judge"]["host_client"] == "opencode-cli"


def test_the_opencode_plugin_names_its_own_host():
    plugin = (ROOT / "opencode" / "plugin.ts").read_text(encoding="utf-8")
    assert 'ADR_KIT_HOST_CLIENT: "opencode-cli"' in plugin
