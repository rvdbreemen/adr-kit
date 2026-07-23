"""Deterministic, bounded, read-only ADR hook core."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import tempfile
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_BIN_DIR = Path(__file__).resolve().parents[1] / "bin"
if str(_BIN_DIR) not in sys.path:
    sys.path.insert(0, str(_BIN_DIR))

from adr_query import IndexQueryError, query_adr_context

MAX_INPUT_BYTES = 64 * 1024
MAX_PARENT_CHARS = 8 * 1024
MAX_CONTEXT_CHARS = 4 * 1024
MAX_RESULTS = 3
QUEUE_CACHE_NAME = ".adr-kit-readiness.json"
QUEUE_MAX_BYTES = 256 * 1024
WRITE_TOOLS = {
    "edit",
    "multiedit",
    "write",
    "applypatch",
    "create",
    "notebookedit",
}
NOOP_EVENTS = {
    "stop",
    "subagentstop",
    "sessionend",
    "permissionrequest",
    "notification",
    "interrupt",
    "postcompact",
}
EVENT_ALIASES = {
    "sessionstart": "SessionStart",
    "userpromptsubmit": "UserPromptSubmit",
    "userpromptsubmitted": "UserPromptSubmit",
    "pretooluse": "PreToolUse",
    "posttooluse": "PostToolUse",
    "subagentstart": "SubagentStart",
    "precompact": "PreCompact",
    "stop": "Stop",
    "subagentstop": "SubagentStop",
    "sessionend": "SessionEnd",
    "permissionrequest": "PermissionRequest",
    "notification": "Notification",
    "interrupt": "Interrupt",
    "postcompact": "PostCompact",
}


@dataclass(frozen=True)
class Envelope:
    client: str
    client_version: str | None
    event: str
    session_id: str | None
    agent_id: str | None
    workspace: Path
    tool_name: str | None
    tool_input: dict[str, Any]
    prompt: str | None
    parent_context: str | None


def _bounded_text(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    return value[:limit]


def _first(payload: dict, *keys: str) -> object:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def normalize(payload: dict[str, Any], client: str, event: str | None) -> Envelope:
    native = event or _first(payload, "hook_event_name", "hookEventName", "event")
    compact = re.sub(r"[^a-z]", "", str(native or "").lower())
    normalized_event = EVENT_ALIASES.get(compact, str(native or "Unknown"))
    workspace_raw = _first(payload, "cwd", "workspace", "workspace_root")
    workspace = Path(str(workspace_raw or Path.cwd())).expanduser().resolve()
    tool_input = _first(payload, "tool_input", "toolInput", "tool")
    if not isinstance(tool_input, dict):
        tool_input = {}
    tool_name = _bounded_text(
        _first(payload, "tool_name", "toolName", "tool_name_normalized"), 80
    )
    prompt = _bounded_text(
        _first(payload, "prompt", "user_prompt", "userPrompt"), MAX_INPUT_BYTES // 2
    )
    parent = _bounded_text(
        _first(payload, "parent_context", "parentContext", "adr_context"),
        MAX_PARENT_CHARS,
    )
    return Envelope(
        client=client,
        client_version=_bounded_text(
            _first(payload, "client_version", "version"), 80
        ),
        event=normalized_event,
        session_id=_bounded_text(
            _first(payload, "session_id", "sessionId"), 160
        ),
        agent_id=_bounded_text(
            _first(payload, "agent_id", "agentId", "subagent_id"), 160
        ),
        workspace=workspace,
        tool_name=tool_name,
        tool_input=tool_input,
        prompt=prompt,
        parent_context=parent,
    )


def parse_payload(raw: bytes, client: str, event: str | None = None) -> Envelope | None:
    if len(raw) > MAX_INPUT_BYTES:
        return None
    try:
        payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("adr_kit_disabled") is True:
        return None
    return normalize(payload, client, event)


def duplicate_event(envelope: Envelope) -> bool:
    """Best-effort cross-process dedupe in OS temp; failures stay fail-open."""
    if not envelope.session_id:
        return False
    path_value = _first(
        envelope.tool_input, "file_path", "filePath", "path", "notebook_path"
    )
    signature = json.dumps(
        [
            envelope.event,
            envelope.tool_name,
            path_value,
            envelope.prompt,
            envelope.agent_id,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    safe_session = re.sub(r"[^A-Za-z0-9._-]", "_", envelope.session_id)[:80]
    state = Path(tempfile.gettempdir()) / f"adr-kit-hook-{safe_session}.seen"
    try:
        if state.is_file() and state.read_text(encoding="utf-8") == signature:
            return True
        temporary = state.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(signature, encoding="utf-8")
        os.replace(temporary, state)
    except OSError:
        return False
    return False


def _index_path(workspace: Path) -> Path | None:
    candidates = (
        workspace / "docs" / "adr" / "ADR-INDEX.json",
        workspace / "adr" / "ADR-INDEX.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_index_records(workspace: Path) -> list[dict[str, Any]]:
    path = _index_path(workspace)
    if path is None or path.stat().st_size > 2 * 1024 * 1024:
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    records = payload.get("adrs", []) if isinstance(payload, dict) else []
    return [item for item in records if isinstance(item, dict)]


def load_records(workspace: Path) -> list[dict[str, Any]]:
    return [
        item for item in load_index_records(workspace) if item.get("status") == "Accepted"
    ]


def load_queue_context(workspace: Path) -> str:
    """Read the prepared Proposed queue only; missing/stale/corrupt fails open."""
    path = workspace / "docs" / "adr" / QUEUE_CACHE_NAME
    try:
        if not path.is_file() or path.stat().st_size > QUEUE_MAX_BYTES:
            return ""
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            return ""
        from datetime import datetime, timezone

        expires_at = datetime.fromisoformat(str(payload["expires_at"]))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires_at.astimezone(timezone.utc):
            return ""
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return ""
    lines = ["Proposed ADR decision queue (derived, non-authoritative):"]
    count = 0
    for item in payload.get("actions", []):
        if not isinstance(item, dict):
            continue
        adr_id = str(item.get("adr_id", ""))
        command = str(item.get("command", ""))
        if not re.fullmatch(r"ADR-\d{3,4}", adr_id):
            continue
        if command != f"/adr-kit:grill {adr_id}":
            continue
        reasons = [
            re.sub(r"[\r\n]+", " ", str(reason))[:160]
            for reason in item.get("reasons", [])
            if str(reason)
        ][:2]
        lines.append(f"- {adr_id}: {', '.join(reasons)} -> {command}")
        count += 1
        if count == MAX_RESULTS:
            break
    return "\n".join(lines)[:MAX_CONTEXT_CHARS] if count else ""


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9._/-]{2,}", text.lower())
        if token not in {"the", "and", "for", "with", "from", "this", "that"}
    }


def _record_text(record: dict[str, Any]) -> str:
    scope = record.get("scope", {})
    globs = scope.get("path_globs", []) if isinstance(scope, dict) else []
    return " ".join(
        [
            str(record.get("id", "")),
            str(record.get("title", "")),
            str(record.get("decision_summary", "")),
            " ".join(str(value) for value in globs),
        ]
    )


def rank(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    scored = []
    for record in records:
        overlap = len(query_tokens & _tokens(_record_text(record)))
        scored.append((overlap, str(record.get("id", "")), record))
    scored.sort(key=lambda item: (-item[0], item[1]))
    positive = [record for score, _id, record in scored if score > 0]
    return (positive or [item[2] for item in scored])[:MAX_RESULTS]


def _query(
    workspace: Path,
    query: str,
    *,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """Use the shared index-first outcome contract and fail open on any fault."""
    index = _index_path(workspace)
    if index is None:
        return []
    try:
        outcome = query_adr_context(
            query,
            index.parent,
            limit=MAX_RESULTS,
            strict_index=True,
            include_history=False,
            statuses=("Accepted", "Proposed"),
            paths=(path,) if path else (),
        )
    except (IndexQueryError, OSError, UnicodeError, ValueError):
        return []
    return [
        item
        for item in outcome["results"]
        if item.get("status") in {"Accepted", "Proposed"}
    ][:MAX_RESULTS]


def _safe_edit_path(envelope: Envelope) -> Path | None:
    value = _first(
        envelope.tool_input, "file_path", "filePath", "path", "notebook_path"
    )
    if not isinstance(value, str) or len(value) > 4096:
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = envelope.workspace / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(envelope.workspace)
    except ValueError:
        return None
    return resolved


def _matching_path_records(
    records: list[dict[str, Any]], workspace: Path, path: Path
) -> list[dict[str, Any]]:
    relative = path.relative_to(workspace).as_posix()
    matches = []
    for record in records:
        scope = record.get("scope", {})
        globs = scope.get("path_globs", []) if isinstance(scope, dict) else []
        if any(fnmatch.fnmatchcase(relative, str(pattern)) for pattern in globs):
            matches.append(record)
    return matches or rank(records, relative)


def _render(records: list[dict[str, Any]], heading: str) -> str:
    if not records:
        return ""
    lines = [heading]
    for record in records[:MAX_RESULTS]:
        raw_path = str(record.get("path", ""))
        source = f"docs/adr/{Path(raw_path).name}"
        adr_id = record.get("id") or record.get("adr_id")
        lines.append(
            f"- {adr_id}: {record.get('title')} — "
            f"{record.get('decision_summary')} (source: {source})"
        )
    return "\n".join(lines)[:MAX_CONTEXT_CHARS]


def _client_grill(client: str, arguments: str) -> str:
    prefix = {
        "claude-code-cli": "/adr-kit:grill",
        "codex-cli": "$adr-kit:grill",
        "github-copilot-cli": "adr-kit:grill",
    }.get(client, "adr-kit:grill")
    return f"{prefix} {arguments}"


def _safe_source_argument(path: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9_./\\ -]{1,4096}", path):
        return None
    return '"' + path.replace("\\", "/").replace('"', '\\"') + '"'


def _proposed_advisory(
    proposed: list[dict[str, Any]],
    relative: str,
    client: str,
) -> str:
    linked = []
    for record in proposed:
        metadata = record.get("metadata", {})
        verified = metadata.get("verified_in", []) if isinstance(metadata, dict) else []
        scope = record.get("scope", {})
        globs = scope.get("path_globs", []) if isinstance(scope, dict) else []
        if any(
            fnmatch.fnmatchcase(relative.casefold(), str(value).casefold())
            or relative.casefold() == str(value).replace("\\", "/").casefold()
            for value in list(verified) + list(globs)
        ):
            linked.append(record)
    lines = []
    for record in sorted(linked, key=lambda item: str(item.get("id", "")))[:MAX_RESULTS]:
        adr_id = str(record.get("id", ""))
        if re.fullmatch(r"ADR-\d{3,4}", adr_id):
            lines.append(
                f"Proposed ADR implementation link: {adr_id} -> "
                f"{_client_grill(client, adr_id)}"
            )
    if not lines and re.search(
        r"(^|/)(?:architecture|infra(?:structure)?|migrations?|schemas?|"
        r"api|contracts?|config|deploy|security)(?:/|[-_.])|"
        r"(^|/)(?:dockerfile|compose\.ya?ml|pyproject\.toml|package\.json|"
        r"Cargo\.toml|go\.mod)$",
        relative,
        re.IGNORECASE,
    ):
        quoted = _safe_source_argument(relative)
        if quoted:
            lines.append(
                "Possible durable architecture decision -> "
                + _client_grill(client, f"--source {quoted}")
            )
    return "\n".join(lines)[:MAX_CONTEXT_CHARS]


def evaluate(envelope: Envelope) -> tuple[str, str]:
    compact_event = re.sub(r"[^a-z]", "", envelope.event.lower())
    if compact_event in NOOP_EVENTS:
        return "", "noop"
    if envelope.event == "SubagentStart":
        context = (envelope.parent_context or "")[:MAX_CONTEXT_CHARS]
        return (context, "subagent") if context else ("", "noop")
    if envelope.event == "PreCompact":
        context = (envelope.parent_context or "")[:MAX_CONTEXT_CHARS]
        return (context, "compact") if context else ("", "noop")
    all_records = load_index_records(envelope.workspace)
    records = [item for item in all_records if item.get("status") == "Accepted"]
    proposed = [item for item in all_records if item.get("status") == "Proposed"]
    if envelope.event == "SessionStart":
        global_records = sorted(
            (
                item
                for item in records
                if item.get("context_scope") == "global"
            ),
            key=lambda item: str(item.get("id", "")),
        )
        parts = [
            part
            for part in (
                _render(
                    global_records[:MAX_RESULTS],
                    "Global Accepted ADR orientation:",
                ),
                load_queue_context(envelope.workspace),
            )
            if part
        ]
        return ("\n\n".join(parts)[:MAX_CONTEXT_CHARS], "session") if parts else ("", "noop")
    if not records and envelope.event not in {"PreToolUse", "PostToolUse"}:
        return "", "noop"
    if envelope.event == "UserPromptSubmit":
        selected = _query(envelope.workspace, envelope.prompt or "")
        governing = [item for item in selected if item.get("status") == "Accepted"]
        advisory = [item for item in selected if item.get("status") == "Proposed"]
        parts = [
            part
            for part in (
                _render(governing, "Governing Accepted ADRs relevant to this prompt:"),
                _render(advisory, "Advisory Proposed ADRs relevant to this prompt:"),
            )
            if part
        ]
        return ("\n".join(parts)[:MAX_CONTEXT_CHARS], "prompt") if parts else ("", "noop")
    if envelope.event in {"PreToolUse", "PostToolUse"}:
        tool = (envelope.tool_name or "").lower().replace("_", "")
        if tool not in WRITE_TOOLS:
            return "", "noop"
        path = _safe_edit_path(envelope)
        if path is None:
            return "", "noop"
        relative = path.relative_to(envelope.workspace).as_posix()
        selected = _query(envelope.workspace, relative, path=relative)
        governing = [item for item in selected if item.get("status") == "Accepted"]
        advisory = [item for item in selected if item.get("status") == "Proposed"]
        heading = (
            "Governing Accepted ADRs before this edit:"
            if envelope.event == "PreToolUse"
            else "Post-edit ADR backstop; verify this change against:"
        )
        context_parts = [
            part
            for part in (
                _render(governing, heading),
                _render(advisory, "Advisory Proposed ADRs for this edit:"),
                _proposed_advisory(
                    proposed, relative, envelope.client
                ),
            )
            if part
        ]
        return "\n".join(context_parts)[:MAX_CONTEXT_CHARS], (
            "pre-edit" if envelope.event == "PreToolUse" else "post-edit"
        )
    return "", "noop"
