"""Deterministic, bounded ADR hook core. Read-only except for one narrow write.

This file was read-only, and said so here, until ADR-021. It now regenerates a
stale generated index on `session-start` and `user-prompt-submit` -- and only
those two, under a lock, only when the projected cost fits the event's declared
budget, and only ever writing the generated index artefacts. Everything else
still reads.

The exception is stated at the top rather than left to be discovered because the
read-only property is what makes this file safe to reason about: an edit-tier
hook fires before every single write a user makes, and a surprise write there is
not a thing anyone should have to find by grepping. See `refresh_index`.
"""

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
# spec.md R5 asks for five relevant ADRs at the moment work begins. This was 3,
# and the documented knob (context.default_limit) never reached the hook, so a
# user who set 5 still got 3. Both are fixed: the default is five, and the
# project setting wins when it is present.
DEFAULT_MAX_RESULTS = 5
MAX_RESULTS = DEFAULT_MAX_RESULTS
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
PLAN_EXIT_TOOLS = {"exitplanmode", "exitplan", "planexit"}

# Events this hook accepts and deliberately answers with nothing. Silence here
# is a decision, not an oversight, so each entry carries its reason: a future
# reader deciding whether to wire one of these up should inherit the argument
# rather than re-derive it.
NOOP_EVENTS = {
    # The three end-of-work events. "Work finished -- were decisions made?" is a
    # real question and this is where it would live, but answering it honestly
    # means reading a whole session, which wants a model. Every hook here is
    # deterministic, model-free and inside a 2 s budget (ADR-015); spending at
    # session end would make this the first hook that costs money, on an event
    # the user cannot see fire. Recorded as a deliberate silence in ADR-019.
    "stop",
    "subagentstop",
    "sessionend",
    # Not about the work at all. A permission dialog and a notification are UI
    # moments; injecting ADR context into either would put architectural text
    # where the user is answering an unrelated question.
    "permissionrequest",
    "notification",
    # The user stopped the agent. Adding output to an interrupt is the one time
    # nobody wants more text.
    "interrupt",
    # Compaction context is injected at PreCompact, while the transcript still
    # exists. Afterwards there is nothing left to carry forward, so a second
    # injection would be new context rather than preserved context.
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


def _project_config(workspace: Path) -> dict[str, Any]:
    """The project config, or an empty one. Never raises; never blocks a hook."""
    try:
        raw = json.loads(
            (workspace / "docs" / "adr" / ".adr-kit.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _switched_off(workspace: Path, block: str) -> bool:
    """Honour `inject.enabled` and `watch.enabled` from the project config.

    Both keys shipped in `schemas/adr-kit-config.schema.json` describing exactly
    this behaviour -- "when false, the PreToolUse injector never emits context
    and the hook is a no-op for this project" -- and neither was read by anything
    a hook reaches. `inject.enabled` had one reader, `bin/adr-watch`, which no
    client's `hooks.json` invokes. So a user who turned injection off was told
    the hook was now a no-op, and the injection kept firing.

    `guardian.enabled` has worked this way since v0.18, so the pattern is the
    kit's own rather than a new invention. Only an explicit `false` switches a
    tier off: a missing key, a missing file and a malformed file all mean on,
    because a settings surface must not be able to silence governance by being
    unreadable.
    """
    block_config = _project_config(workspace).get(block)
    if not isinstance(block_config, dict):
        return False
    return block_config.get("enabled") is False


def _configured_limit(workspace: Path) -> int:
    """context.default_limit when set, else the default. Bounded and fail-soft.

    Read here rather than threaded through, because the hook is the one caller
    that used to ignore it. The bound keeps a typo from turning one prompt into
    a context flood.
    """
    value = (_project_config(workspace).get("context") or {}).get("default_limit")
    if isinstance(value, int) and 1 <= value <= 20:
        return value
    return DEFAULT_MAX_RESULTS

# Only these two may write. They carry a 500 ms budget; the edit-tier events
# carry far less and cannot hold a render at any realistic ADR count (ADR-021).
REFRESHING_EVENTS = {"SessionStart", "UserPromptSubmit"}

STALE_INDEX_MESSAGE = (
    "The generated ADR index is stale, so ADR context is unavailable for this "
    "step. Run `bin/adr-index docs/adr` to regenerate it."
)


def index_is_stale(workspace: Path) -> bool:
    """Cheap precondition, ~2.8 ms measured, not a certification.

    `index_probably_fresh` is an mtime comparison and says so in its own
    docstring. Used here to avoid work, never to certify a result -- the caller
    treats a false negative as "read what is there", which is what it would have
    done anyway.
    """
    index = _index_path(workspace)
    if index is None:
        return False
    try:
        from adr_index_core import index_probably_fresh

        return not index_probably_fresh(index.parent)
    except (ImportError, OSError, ValueError):
        return False


def refresh_index(workspace: Path, event: str) -> str:
    """Regenerate a stale index in place, when this event may and can afford it.

    Returns "" when nothing needed doing or the regeneration succeeded, and the
    staleness message otherwise. The message matters more than the write: an
    agent that gets silence from a stale index cannot tell it from "no ADR was
    relevant", and that silence is the defect ADR-021 exists to remove.

    Every failure path here returns the message rather than raising. This runs
    inside a fail-open hook, and a governance tool that breaks a session is
    worse than one that asks for a command to be run.
    """
    if not index_is_stale(workspace):
        return ""
    if event not in REFRESHING_EVENTS:
        # The edit tier reads only. Rendering there would put a write on the
        # path taken before every single edit.
        return STALE_INDEX_MESSAGE

    index = _index_path(workspace)
    if index is None:
        return STALE_INDEX_MESSAGE
    adr_dir = index.parent

    try:
        from adr_index_core import projected_render_ms, regenerate_index
    except ImportError:
        return STALE_INDEX_MESSAGE

    budget_ms = _event_budget_ms(event)
    projected = projected_render_ms(adr_dir)
    if projected > budget_ms:
        # A large ADR set degrades to a nudge rather than to a timeout. The
        # client kills the hook at its own bound, and a process killed mid-write
        # is worse than one that never started.
        return STALE_INDEX_MESSAGE

    lock = adr_dir / ".adr-index.lock"
    try:
        # O_EXCL is the whole lock: whoever creates the file owns the render.
        handle = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # Another session is rendering. Read what is there and continue -- ADR-021
        # forbids waiting, because the loser would spend a budget it cannot
        # recover on work someone else is already doing.
        return STALE_INDEX_MESSAGE
    except OSError:
        return STALE_INDEX_MESSAGE

    try:
        os.close(handle)
        regenerate_index(adr_dir)
        return ""
    except (OSError, ValueError, KeyError, TypeError):
        return STALE_INDEX_MESSAGE
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _event_budget_ms(event: str) -> float:
    """This event's declared budget, from the manifest the client enforces.

    Read rather than hardcoded for the same reason the pull-request guard reads
    its own: whoever changes the manifest changes this, and the two cannot drift
    into disagreeing.
    """
    manifest = Path(__file__).resolve().parent / "manifest.json"
    wanted = {"SessionStart": "session-start", "UserPromptSubmit": "user-prompt-submit"}
    try:
        events = json.loads(manifest.read_text(encoding="utf-8"))["events"]
        return float(
            next(
                entry["latency"]["p50_ms"]
                for entry in events
                if entry.get("id") == wanted.get(event)
            )
        )
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return 400.0


def _query(
    workspace: Path,
    query: str,
    *,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """Rank the ADRs for this query, lexically over the generated index.

    This file must not be able to reach a model or the network -- a test
    asserts that by walking its imports (ADR-036 retired the one exception
    ADR-020 had carved out for query embedding).
    """
    index = _index_path(workspace)
    if index is None:
        return []
    limit = _configured_limit(workspace)
    try:
        outcome = query_adr_context(
            query,
            index.parent,
            limit=limit,
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
    ][:limit]


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


def _plan_text(envelope: Envelope) -> str:
    """The plan a plan-exit tool call carries, bounded like every other input."""
    raw = _first(envelope.tool_input, "plan", "content", "text", "summary")
    return (_bounded_text(raw, MAX_CONTEXT_CHARS) or "").strip()


#: Both lists must hit on one line before it counts as a candidate. Verb-only
#: matches every imperative bullet in any plan; noun-only matches prose that
#: merely mentions the architecture. Precision is the constraint: a nudge that
#: names noise teaches the reader to skip the nudge (spec B1: deterministic,
#: injection-only; the model reading the context does the actual judging).
_DECISION_VERBS = re.compile(
    r"(?i)\b(add|adopt|introduce|switch|migrate|replace|choose|pick|drop|"
    r"remove|rewrite|standardi[sz]e|upgrade|consolidate|split|pin|use)\b"
)
_DECISION_NOUNS = re.compile(
    r"(?i)\b(dependenc\w+|librar\w+|framework|database|storage|cache|queue|"
    r"protocol|api|interface|contract|schema|auth\w*|encryption|format|"
    r"service|endpoint|runtime|package|backend|index|pipeline|architecture)\b"
)


def _plan_decision_candidates(plan: str, limit: int = 5) -> list[str]:
    """Decision-shaped lines in the plan, found deterministically.

    Named so the question below lands on something concrete: "does this plan
    decide anything?" is easy to wave past, "this line looks like a decision"
    is not. Bounded because the sixth candidate adds noise, not signal.
    """
    found: list[str] = []
    for raw in plan.splitlines():
        line = raw.strip().lstrip("-*#0123456789. ").strip()
        if not line or len(line) > 240:
            continue
        if _DECISION_VERBS.search(line) and _DECISION_NOUNS.search(line):
            found.append(line)
            if len(found) >= limit:
                break
    return found


def _plan_decision_prompt(client: str) -> str:
    """Ask the question this moment exists for.

    Deliberately a question and not a gate. A hook that blocked here would teach
    people to write an empty ADR to get past it, which is the failure mode that
    produced six rule-less Enforcement blocks in this very repository.
    """
    return (
        "Before leaving plan mode: does this plan make an architectural decision "
        "no ADR records yet? A new dependency, an interface or contract change, a "
        "shift in a non-functional requirement, or a new pattern all qualify. If "
        "so, write it now with " + _client_grill(client, "") + " while the "
        "reasoning is still in front of you; afterwards it becomes justification."
    )

def evaluate(envelope: Envelope) -> tuple[str, str]:
    """Refresh a stale index where the budget allows, then render the context.

    An agent that writes docs/adr/ADR-NNN.md directly -- the common case in a
    harness -- leaves the generated index stale. `query_adr_context` then raises
    IndexQueryError, `_query` swallows it into an empty list, and ADR injection
    goes dark for the rest of the session with no message at all. Silence is the
    defect ADR-021 exists to remove: an empty answer reads exactly like "no ADR
    was relevant".

    Wrapped rather than inlined so every return path in the renderer carries the
    notice. Missing one of them would reproduce the silence on exactly the
    branch nobody thought about.
    """
    try:
        notice = refresh_index(envelope.workspace, envelope.event)
    except Exception:  # noqa: BLE001 -- fail-open is this file's contract
        notice = STALE_INDEX_MESSAGE

    context, kind = _evaluate_context(envelope)
    if not notice:
        return context, kind
    if not context:
        return notice, "stale-index"
    return "\n\n".join((notice, context))[:MAX_CONTEXT_CHARS], kind


def _evaluate_context(envelope: Envelope) -> tuple[str, str]:
    """Render the context for this moment."""
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
        if envelope.event == "PreToolUse" and tool in PLAN_EXIT_TOOLS:
            # Leaving plan mode: the plan is complete and no code exists yet.
            # Cheapest moment to notice a missing decision, and the only one
            # where the answer can still shape the implementation instead of
            # justifying it afterwards. Same contract as every other hook:
            # deterministic, injection-only, model-free, never blocking.
            plan = _plan_text(envelope)
            if not plan:
                return "", "noop"
            selected = _query(envelope.workspace, plan)
            governing = [item for item in selected if item.get("status") == "Accepted"]
            advisory = [item for item in selected if item.get("status") == "Proposed"]
            candidates = _plan_decision_candidates(plan)
            named = (
                "Decision-shaped lines in this plan - each either falls under "
                "an ADR above or needs a new one:\n"
                + "\n".join(f"- {line}" for line in candidates)
                if candidates
                else ""
            )
            parts = [
                part
                for part in (
                    _render(governing, "ADRs that govern this plan:"),
                    _render(advisory, "Advisory Proposed ADRs for this plan:"),
                    named,
                    _plan_decision_prompt(envelope.client),
                )
                if part
            ]
            joined = "\n".join(parts)[:MAX_CONTEXT_CHARS]
            return (joined, "plan-exit") if parts else ("", "noop")
        if tool not in WRITE_TOOLS:
            return "", "noop"
        # The edit tier is switchable per project, which is what the config
        # schema has claimed since it shipped. PreToolUse is `inject`, PostToolUse
        # is `watch`; they are separate because a team may want the pre-edit
        # constraint without the post-edit backstop, or the reverse.
        if _switched_off(
            envelope.workspace,
            "inject" if envelope.event == "PreToolUse" else "watch",
        ):
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
