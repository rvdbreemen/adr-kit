"""End-to-end tests for bin/adr-mcp: the thin dual-era MCP stdio server.

Drives the server as a subprocess over stdin/stdout with newline-delimited
JSON-RPC 2.0 messages, mirroring how Claude Code, Codex, GitHub Copilot CLI,
or another stdio MCP client talks to a server. All messages for a scenario are written in
one batch and the responses are matched back by request id, which keeps the
tests deadlock-free without threads.

Two protocol eras share one process (ADR-016):

  * handshake era (2024-11-05 .. 2025-11-25) - reached through `initialize`;
  * modern era (2026-07-28) - reached through `server/discover` or the
    reserved `io.modelcontextprotocol/protocolVersion` key in `params._meta`.

Nothing here inspects the source: every era, negotiation and wire-shape
assertion is made against bytes that came back out of `serve()`.
"""
from __future__ import annotations

import json
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_MCP = REPO_ROOT / "bin" / "adr-mcp"

EXPECTED_TOOLS = {
    "adr_context",
    "adr_judge",
    "adr_status",
    "adr_quality",
    "adr_readiness",
    "adr_lint",
    "adr_related",
}

# Declaration order of TOOL_DEFINITIONS. ADR-016 requires tools/list to be
# deterministically ordered; this is the order it must keep. New tools are
# appended, never inserted (ADR-040): existing client positions stay stable.
EXPECTED_TOOL_ORDER = [
    "adr_context",
    "adr_judge",
    "adr_status",
    "adr_quality",
    "adr_readiness",
    "adr_lint",
    "adr_related",
]

# --- protocol registry, mirrored from ADR-016 rather than imported ----------
# Deliberately spelled out here: a test that imported the server's own tuples
# would confirm the server agrees with itself. These are the values the ADR
# fixes, so drift shows up as a test failure instead of a silent agreement.
HANDSHAKE_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
NEWEST_HANDSHAKE_VERSION = "2025-11-25"
MODERN_VERSION = "2026-07-28"

PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
LOG_LEVEL_KEY = "io.modelcontextprotocol/logLevel"

UNSUPPORTED_PROTOCOL_VERSION = -32022

# Every JSON-RPC error code this server is allowed to emit. ADR-016 Must Not:
# "The server must not emit -32020 or -32021, nor any undefined code in the
# spec-reserved -32020..-32099 range, and must not allocate new codes in the
# legacy -32000..-32019 range." Expressed as an allowlist so both halves of
# that sentence are covered by one assertion.
ALLOWED_ERROR_CODES = {
    -32700,  # parse error
    -32600,  # invalid request
    -32601,  # method not found
    -32602,  # invalid params
    -32603,  # internal error
    UNSUPPORTED_PROTOCOL_VERSION,
}

# Fields a legacy-routed result must never carry (ADR-016 Must Not).
MODERN_ONLY_RESULT_KEYS = ("resultType", "ttlMs", "cacheScope", "_meta")

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "0"},
    },
}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


ENFORCED_ADR = """\
# ADR-001 No Foo

## Status

Accepted, 2026-04-25.

## Context

Foo fragments the heap.

## Decision

Do not use Foo. Use Bar everywhere; Foo fragments the heap and the
allocator never recovers, so Bar is the only allocation primitive allowed.

## Alternatives Considered

- Use Foo: rejected, fragments the heap.
- Use Bar: accepted.

## Consequences

**Positive:**
- No Foo.

**Negative:**
- Need Bar.

## Related Decisions

- None.

## References

- ./bench/results.txt

## Enforcement

```json
{
  "forbid_pattern": [
    {"pattern": "\\\\bFoo\\\\b", "path_glob": "src/**/*.py", "message": "No Foo."}
  ]
}
```
"""

VIOLATING_DIFF = """\
diff --git a/src/app/main.py b/src/app/main.py
index 0000000..1111111 100644
--- a/src/app/main.py
+++ b/src/app/main.py
@@ -0,0 +1,2 @@
+from lib import Foo
+thing = Foo()
"""


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Fixture project: one Accepted ADR with a declarative Enforcement block."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-no-foo.md").write_text(
        textwrap.dedent(ENFORCED_ADR), encoding="utf-8"
    )
    return tmp_path


def run_session_lines(project_root: Path, messages: list, raw_lines: list = None):
    """Send messages (plus optional raw lines) and return (stdout_lines, stderr).

    The raw stdout lines, in order, unparsed. Tests that need byte-level or
    whole-stream assertions use this; run_session() buckets the same lines by
    request id. Input is closed after writing, so the server exits on EOF and
    everything can be read without threads.
    """
    lines = []
    for msg in messages:
        lines.append(json.dumps(msg))
        if raw_lines and len(lines) == 1:
            # Inject raw (possibly malformed) lines right after the first message.
            lines.extend(raw_lines)
    payload = "\n".join(lines) + "\n"
    proc = subprocess.run(
        [sys.executable, str(ADR_MCP), "--root", str(project_root)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()], proc.stderr


def run_session(project_root: Path, messages: list, raw_lines: list = None):
    """Send messages (plus optional raw lines) to the server, return
    (responses_by_id, id-less frames, stderr)."""
    lines, stderr = run_session_lines(project_root, messages, raw_lines)
    responses = {}
    parse_errors = []
    for line in lines:
        obj = json.loads(line)  # every stdout line must be valid JSON-RPC
        if obj.get("id") is None:
            parse_errors.append(obj)
        else:
            responses[obj["id"]] = obj
    return responses, parse_errors, stderr


def call(tool_name: str, arguments: dict, req_id: int) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def envelope(version: str = MODERN_VERSION, extra: dict = None) -> dict:
    """A conformant modern `params._meta`: both reserved keys present."""
    meta = {PROTOCOL_VERSION_KEY: version, CLIENT_CAPABILITIES_KEY: {}}
    if extra:
        meta.update(extra)
    return meta


def modern(
    method: str,
    req_id,
    params: dict = None,
    version: str = MODERN_VERSION,
    meta_extra: dict = None,
) -> dict:
    """A modern-era frame: the same request with the envelope stamped on it."""
    payload = dict(params or {})
    payload["_meta"] = envelope(version, meta_extra)
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": payload}


def modern_call(tool_name: str, arguments: dict, req_id) -> dict:
    return modern("tools/call", req_id, {"name": tool_name, "arguments": arguments})


def tool_text(response: dict) -> str:
    content = response["result"]["content"]
    assert len(content) == 1 and content[0]["type"] == "text"
    return content[0]["text"]


def assert_legacy_shape(result: dict, what: str) -> None:
    """A legacy-routed result carries none of the modern-era wire fields."""
    for key in MODERN_ONLY_RESULT_KEYS:
        assert key not in result, (
            f"{what}: legacy result must not carry {key!r} - CacheableResult and "
            "resultType do not exist in the handshake revisions (ADR-016 Must Not)"
        )


def assert_modern_shape(result: dict, what: str, cacheable: bool) -> None:
    """Every modern result: resultType + _meta.serverInfo; cache hints if cacheable."""
    assert result.get("resultType") == "complete", f"{what}: missing resultType"
    server_info = result.get("_meta", {}).get(SERVER_INFO_KEY)
    assert server_info is not None, f"{what}: missing _meta[{SERVER_INFO_KEY}]"
    assert server_info["name"] == "adr-kit"
    assert server_info["version"] != "0.0.0"
    if cacheable:
        assert isinstance(result["ttlMs"], int) and not isinstance(result["ttlMs"], bool), (
            f"{what}: ttlMs must be an int (schema.json says integer, schema.ts number)"
        )
        assert result["ttlMs"] >= 0
        assert result["cacheScope"] == "public", f"{what}: cacheScope must be 'public'"
    else:
        # CallToolResult extends Result, not CacheableResult (ADR-016 Must Not:
        # "tools/call results must not carry ttlMs or cacheScope").
        assert "ttlMs" not in result, f"{what}: tools/call must not carry ttlMs"
        assert "cacheScope" not in result, f"{what}: tools/call must not carry cacheScope"


# ---------------------------------------------------------------------------
# Handshake
# ---------------------------------------------------------------------------

def test_initialize_handshake(project: Path):
    responses, _, _ = run_session(project, [INITIALIZE, INITIALIZED])
    result = responses[1]["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["capabilities"] == {"tools": {}}
    assert result["serverInfo"]["name"] == "adr-kit"
    # Version must come from .claude-plugin/plugin.json (semver-ish, not 0.0.0).
    assert result["serverInfo"]["version"] != "0.0.0"
    assert result["serverInfo"]["version"].count(".") == 2
    assert_legacy_shape(result, "initialize")


@pytest.mark.parametrize(
    "manifest_relative",
    [Path(".codex-plugin/plugin.json"), Path("plugin.json")],
)
def test_packaged_client_manifest_version_fallbacks(
    tmp_path: Path, manifest_relative: Path
):
    package = tmp_path / "package"
    (package / "bin").mkdir(parents=True)
    shutil.copy2(ADR_MCP, package / "bin" / "adr-mcp")
    manifest = package / manifest_relative
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"version": "9.8.7"}', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(package / "bin" / "adr-mcp"), "--root", str(tmp_path)],
        input=json.dumps(INITIALIZE) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    response = json.loads(proc.stdout)
    assert response["result"]["serverInfo"]["version"] == "9.8.7"


def test_initialize_confirms_declared_protocol_version(project: Path):
    """A declared handshake version is confirmed, not echoed.

    Renamed from test_initialize_echoes_client_protocol_version: echoing is the
    defect ADR-016 removes, and on a *declared* version echo and confirmation
    are the same answer, so the old name asserted the wrong intent about a
    passing test. The undeclared-version cases below are what actually
    distinguish the two behaviours.
    """
    init = dict(INITIALIZE)
    init["params"] = dict(INITIALIZE["params"], protocolVersion="2024-11-05")
    responses, _, _ = run_session(project, [init])
    assert responses[1]["result"]["protocolVersion"] == "2024-11-05"


def test_ping(project: Path):
    ping = {"jsonrpc": "2.0", "id": 7, "method": "ping"}
    responses, _, _ = run_session(project, [INITIALIZE, INITIALIZED, ping])
    assert responses[7]["result"] == {}


# ---------------------------------------------------------------------------
# tools/list
# ---------------------------------------------------------------------------

def test_tools_list(project: Path):
    listing = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    responses, _, _ = run_session(project, [INITIALIZE, INITIALIZED, listing])
    tools = responses[2]["result"]["tools"]
    assert {t["name"] for t in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"
    # Deliberately thin: adr-suggest (LLM-only) is not exposed.
    assert "adr_suggest" not in {t["name"] for t in tools}
    context = next(tool for tool in tools if tool["name"] == "adr_context")
    properties = context["inputSchema"]["properties"]
    assert {
        "query",
        "limit",
        "paths",
        "components",
        "symbols",
        "topics",
        "statuses",
        "authorities",
        "include_history",
        "strict_index",
        "min_score",
        "project_root",
        "adr_dir",
    } <= set(properties)


# ---------------------------------------------------------------------------
# tools/call
# ---------------------------------------------------------------------------

def test_adr_status_returns_parseable_json(project: Path):
    responses, _, stderr = run_session(
        project, [INITIALIZE, INITIALIZED, call("adr_status", {}, 3)]
    )
    resp = responses[3]
    assert "error" not in resp
    assert resp["result"].get("isError") is not True
    status = json.loads(tool_text(resp))
    assert status["summary"]["total"] == 1
    assert status["summary"]["by_status"]["accepted"] == 1


def test_tool_call_can_override_plugin_cache_root(project: Path, tmp_path: Path):
    plugin_cache = tmp_path / "plugin-cache"
    plugin_cache.mkdir()
    responses, _, _ = run_session(
        plugin_cache,
        [
            INITIALIZE,
            INITIALIZED,
            call("adr_status", {"project_root": str(project)}, 15),
        ],
    )
    status = json.loads(tool_text(responses[15]))
    assert status["summary"]["total"] == 1


def test_adr_judge_flags_violating_diff(project: Path):
    responses, _, _ = run_session(
        project, [INITIALIZE, INITIALIZED, call("adr_judge", {"diff": VIOLATING_DIFF}, 4)]
    )
    resp = responses[4]
    assert resp["result"].get("isError") is not True
    payload = json.loads(tool_text(resp))
    assert payload["exit_code"] == 1
    assert payload["verdict"] == "violation"
    serialized = json.dumps(payload["result"])
    assert "ADR-001" in serialized


def test_adr_judge_passes_clean_diff(project: Path):
    clean_diff = VIOLATING_DIFF.replace("Foo", "Bar")
    responses, _, _ = run_session(
        project, [INITIALIZE, INITIALIZED, call("adr_judge", {"diff": clean_diff}, 5)]
    )
    payload = json.loads(tool_text(responses[5]))
    assert payload["exit_code"] == 0
    assert payload["verdict"] == "ok"


def test_adr_context_ranks_adrs(project: Path):
    responses, _, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED,
         call("adr_context", {"query": "heap allocation Foo", "limit": 3}, 6)],
    )
    resp = responses[6]
    assert resp["result"].get("isError") is not True
    # Output must at least be parseable JSON from adr-context --format json.
    json.loads(tool_text(resp))


def test_adr_context_cli_mcp_outcome_parity(project: Path):
    build = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-index"), "docs/adr"],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert build.returncode == 0, build.stderr
    arguments = {
        "query": "heap allocation Foo",
        "limit": 3,
        "paths": [r"src\app\main.py"],
        "statuses": ["Accepted"],
        "authorities": ["governing"],
        "strict_index": True,
    }
    responses, _, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED, call("adr_context", arguments, 19)],
    )
    mcp_payload = json.loads(tool_text(responses[19]))
    cli = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "bin" / "adr-context"),
            "--format",
            "json",
            "--adr-dir",
            str(project / "docs" / "adr"),
            "--limit",
            "3",
            "--path",
            r"src\app\main.py",
            "--status",
            "Accepted",
            "--authority",
            "governing",
            "--strict-index",
            "heap allocation Foo",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cli.returncode == 0, cli.stderr
    assert mcp_payload == json.loads(cli.stdout)
    assert all(item["source"] == "index-v2" for item in mcp_payload)
    assert all(item["engine"] == "index-first" for item in mcp_payload)


def test_adr_context_no_result_is_an_explicit_empty_array(project: Path):
    responses, _, _ = run_session(
        project,
        [
            INITIALIZE,
            INITIALIZED,
            call("adr_context", {"query": "quantum satellite telemetry"}, 20),
        ],
    )
    assert json.loads(tool_text(responses[20])) == []


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "x", "limit": 0},
        {"query": "x", "limit": 101},
        {"query": "x", "paths": "src/app.py"},
        {"query": "x", "components": [""]},
        {"query": "x", "statuses": ["Imaginary"]},
        {"query": "x", "authorities": ["binding"]},
        {"query": "x", "include_history": "yes"},
        {"query": "x", "min_score": 2},
        {"query": "x", "project_root": "relative-project"},
        {"query": "x", "adr_dir": "../outside"},
    ],
)
def test_adr_context_malformed_or_unsafe_inputs_are_tool_errors(
    project: Path, arguments
):
    responses, _, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED, call("adr_context", arguments, 21)],
    )
    assert responses[21]["result"]["isError"] is True


def test_adr_context_future_schema_strict_failure_is_explicit(project: Path):
    index_path = project / "docs" / "adr" / "ADR-INDEX.json"
    index_path.write_text(
        json.dumps({"schema_version": 99, "adrs": [], "relationships": []}),
        encoding="utf-8",
    )
    responses, _, _ = run_session(
        project,
        [
            INITIALIZE,
            INITIALIZED,
            call(
                "adr_context",
                {"query": "Foo", "strict_index": True},
                22,
            ),
        ],
    )
    result = responses[22]["result"]
    assert result["isError"] is True
    assert "unsupported" in tool_text(responses[22])


def test_adr_context_timeout_is_explicit_and_bounded(project: Path, monkeypatch):
    loader = importlib.machinery.SourceFileLoader("adr_mcp_timeout", str(ADR_MCP))
    spec = importlib.util.spec_from_loader("adr_mcp_timeout", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(["adr-context"], module.CLI_TIMEOUT_S)

    monkeypatch.setattr(module, "run_cli", timed_out)
    result = module.handle_tools_call(
        {"name": "adr_context", "arguments": {"query": "Foo"}},
        project,
        project / "docs" / "adr",
    )

    assert result["isError"] is True
    assert f"timed out after {module.CLI_TIMEOUT_S}s" in result["content"][0]["text"]


def test_adr_quality_single_and_all(project: Path):
    responses, _, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED,
         call("adr_quality", {"adr_id": "ADR-001"}, 8),
         call("adr_quality", {}, 9)],
    )
    single = json.loads(tool_text(responses[8]))
    assert single["file"] == "ADR-001-no-foo.md"
    assert "grade" in single
    everything = json.loads(tool_text(responses[9]))
    assert len(everything["adrs"]) == 1


def test_adr_quality_unknown_id_is_tool_error(project: Path):
    responses, _, _ = run_session(
        project, [INITIALIZE, INITIALIZED, call("adr_quality", {"adr_id": "ADR-999"}, 10)]
    )
    assert responses[10]["result"]["isError"] is True


def test_adr_readiness_is_key_free_and_read_only(project: Path):
    adr = project / "docs" / "adr" / "ADR-001-no-foo.md"
    before = adr.read_bytes()
    responses, _, _ = run_session(
        project,
        [
            INITIALIZE,
            INITIALIZED,
            call(
                "adr_readiness",
                {"adr_id": "ADR-001", "today": "2026-07-20"},
                16,
            ),
        ],
    )

    payload = json.loads(tool_text(responses[16]))
    assert payload["schema_version"] == 1
    assert payload["adrs"][0]["adr_id"] == "ADR-001"
    assert payload["adrs"][0]["classification"] == "accepted"
    assert adr.read_bytes() == before


def test_adr_readiness_all_proposed_and_cli_parity(project: Path):
    adr = project / "docs" / "adr" / "ADR-001-no-foo.md"
    text = adr.read_text(encoding="utf-8")
    adr.write_text(
        text.replace("status: Accepted", "status: Proposed").replace(
            "Accepted, 2026-01-01", "Proposed, 2026-01-01"
        ),
        encoding="utf-8",
    )
    responses, _, _ = run_session(
        project,
        [
            INITIALIZE,
            INITIALIZED,
            call(
                "adr_readiness",
                {"all_proposed": True, "today": "2026-07-20"},
                17,
            ),
        ],
    )
    mcp_payload = json.loads(tool_text(responses[17]))
    cli = subprocess.run(
        [
            sys.executable,
            str(ADR_MCP.parent / "adr-readiness"),
            "--all-proposed",
            "--repo-root",
            str(project),
            "--today",
            "2026-07-20",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cli.returncode == 0, cli.stderr
    assert mcp_payload == json.loads(cli.stdout)


@pytest.mark.parametrize(
    "arguments",
    [
        {"adr_id": 1},
        {"all_proposed": "yes"},
        {"base": "main"},
        {"today": ""},
        {"project_root": "missing-workspace"},
    ],
)
def test_adr_readiness_malformed_inputs_are_tool_errors(project: Path, arguments):
    responses, _, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED, call("adr_readiness", arguments, 18)],
    )
    assert responses[18]["result"]["isError"] is True


def test_unknown_tool_is_invalid_params(project: Path):
    responses, _, _ = run_session(
        project, [INITIALIZE, INITIALIZED, call("adr_everything", {}, 11)]
    )
    assert responses[11]["error"]["code"] == -32602


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

def test_unknown_method_returns_method_not_found(project: Path):
    unknown = {"jsonrpc": "2.0", "id": 12, "method": "resources/list"}
    responses, _, _ = run_session(project, [INITIALIZE, INITIALIZED, unknown])
    assert responses[12]["error"]["code"] == -32601


def test_adr_lint_reports_verdict_and_stays_read_only(project: Path):
    """adr_lint wraps rc 0/1 as a verdict (ADR-040) and mutates nothing."""
    before = sorted(p.name for p in (project / "docs" / "adr").iterdir())
    responses, _, _ = run_session(
        project,
        [
            INITIALIZE,
            INITIALIZED,
            call("adr_lint", {}, 15),
            call("adr_lint", {"strict": True}, 16),
        ],
    )
    for req_id in (15, 16):
        result = responses[req_id]["result"]
        assert not result.get("isError", False)
        payload = json.loads(result["content"][0]["text"])
        assert payload["exit_code"] in (0, 1)
        assert payload["verdict"] in ("ok", "findings")
        assert payload["result"]["summary"]["total"] == 1
    strict_payload = json.loads(responses[16]["result"]["content"][0]["text"])
    assert strict_payload["result"]["strict_mode"] is True
    after = sorted(p.name for p in (project / "docs" / "adr").iterdir())
    assert before == after


def test_adr_lint_rejects_non_boolean_strict(project: Path):
    responses, _, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED, call("adr_lint", {"strict": "yes"}, 17)],
    )
    result = responses[17]["result"]
    assert result["isError"] is True
    assert "'strict' must be a boolean" in result["content"][0]["text"]


def test_adr_related_returns_edges_for_one_adr(project: Path):
    responses, _, _ = run_session(
        project,
        [
            INITIALIZE,
            INITIALIZED,
            call("adr_related", {"adr_id": "ADR-001"}, 18),
            call("adr_related", {"adr_id": "ADR-999"}, 19),
            call("adr_related", {}, 20),
        ],
    )
    ok = responses[18]["result"]
    assert not ok.get("isError", False)
    payload = json.loads(ok["content"][0]["text"])
    assert payload["adr"]["adr_id"] == "ADR-001"
    assert "outbound" in payload and "inbound" in payload
    # Unknown id is a CLI usage error (exit 2) surfaced as a tool error.
    unknown = responses[19]["result"]
    assert unknown["isError"] is True
    missing = responses[20]["result"]
    assert missing["isError"] is True
    assert "'adr_id' must be a non-empty string" in missing["content"][0]["text"]


def test_malformed_json_line_does_not_kill_server(project: Path):
    ping = {"jsonrpc": "2.0", "id": 13, "method": "ping"}
    responses, parse_errors, _ = run_session(
        project,
        [INITIALIZE, INITIALIZED, ping],
        raw_lines=["this is not json {{{", '"just a string"'],
    )
    # The server reported the bad lines...
    codes = [e["error"]["code"] for e in parse_errors]
    assert -32700 in codes  # malformed line
    assert -32600 in codes  # valid JSON but not a request object
    # ...and kept serving afterwards.
    assert responses[13]["result"] == {}


def test_unknown_notification_is_silently_ignored(project: Path):
    note = {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {}}
    ping = {"jsonrpc": "2.0", "id": 14, "method": "ping"}
    responses, parse_errors, _ = run_session(project, [INITIALIZE, note, ping])
    assert not parse_errors
    assert set(responses) == {1, 14}


# ===========================================================================
# Gate adr-mcp-dual-era-v1 (ADR-016)
# ===========================================================================
#
# ADR-016 is Accepted and binding, and names this gate. Everything from here
# down IS the gate: the conformance suite that TASK-58.3 owes the decision,
# driving both eras through serve() as real newline-delimited JSON-RPC.
#
# It was registered as a single xfail(strict=True) placeholder when the ADR
# was accepted ahead of the implementation. TASK-58.1 and TASK-58.2 landed the
# implementation and the marker is gone: the gate is live, and every positive
# obligation of the Decision Contract is asserted below against emitted bytes.
# Nothing here reads bin/adr-mcp's source - a source grep would false-positive
# on the comment at bin/adr-mcp:685-689, which names -32020 and -32021 precisely
# to explain why they are unreachable.

GATE_ADR_MCP_DUAL_ERA_V1 = "adr-mcp-dual-era-v1"


# ---------------------------------------------------------------------------
# Era routing (ADR-016: era is a pure function of the frame; no era lock)
# ---------------------------------------------------------------------------

def test_era_routing_is_a_pure_function_of_each_frame(project: Path):
    """All five routing cases, in one ordered session on one stdin.

    Ordering is the point: frames 4 and 5 arrive *after* frames that would
    have set an era lock, and must still be routed on their own content. ADR-016
    Must Not: "No request carrying the io.modelcontextprotocol/protocolVersion
    sentinel may be answered under legacy semantics, whatever arrived earlier on
    the same stdin. There is no era lock and no connection-scoped era state."
    """
    frames = [
        # 1. modern envelope -> modern.
        modern("tools/list", 201),
        # 2. a bare _meta carrying only progressToken -> legacy. A bare _meta is
        #    no evidence: legacy requests already put progressToken there.
        {
            "jsonrpc": "2.0",
            "id": 202,
            "method": "tools/list",
            "params": {"_meta": {"progressToken": "abc"}},
        },
        # 3. initialize -> legacy even with the envelope stamped on it, because
        #    initialize does not exist at 2026-07-28, so an envelope on it is a
        #    client defect rather than an era signal.
        {
            "jsonrpc": "2.0",
            "id": 203,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "_meta": envelope(),
            },
        },
        # 4. a modern frame AFTER a legacy initialize still routes modern.
        #    This is the no-era-lock property and the one most likely to regress.
        modern("tools/list", 204),
        # 5. a bare frame after modern frames still routes legacy: byte-identical
        #    frames always get the same answer, whatever preceded them.
        {"jsonrpc": "2.0", "id": 205, "method": "tools/list"},
    ]
    responses, _, _ = run_session(project, frames)

    assert_modern_shape(responses[201]["result"], "modern tools/list", cacheable=True)
    assert_legacy_shape(responses[202]["result"], "_meta with only progressToken")
    assert responses[203]["result"]["protocolVersion"] == "2025-06-18"
    assert_legacy_shape(responses[203]["result"], "initialize with an envelope")
    assert_modern_shape(
        responses[204]["result"], "modern frame after legacy initialize", cacheable=True
    )
    assert_legacy_shape(responses[205]["result"], "bare frame after a modern frame")
    # Same request, two eras, decided only by the frame itself.
    assert responses[204]["result"]["tools"] == responses[205]["result"]["tools"]


def test_server_discover_routes_modern_as_the_very_first_frame(project: Path):
    """server/discover routes modern with no prior message of any kind.

    The stdio backward-compatibility probe is the first thing a dual-era client
    sends; there is no handshake in front of it to establish anything.
    """
    responses, _, _ = run_session(project, [modern("server/discover", 210)])
    assert "error" not in responses[210], responses[210]
    assert_modern_shape(responses[210]["result"], "server/discover", cacheable=True)


# ---------------------------------------------------------------------------
# Version negotiation
# ---------------------------------------------------------------------------

def test_initialize_confirms_every_declared_handshake_version(project: Path):
    """All four handshake revisions are reachable and confirmed verbatim."""
    frames = [
        {
            "jsonrpc": "2.0",
            "id": version,
            "method": "initialize",
            "params": {"protocolVersion": version, "capabilities": {}},
        }
        for version in HANDSHAKE_VERSIONS
    ]
    responses, _, _ = run_session(project, frames)
    for version in HANDSHAKE_VERSIONS:
        assert responses[version]["result"]["protocolVersion"] == version


@pytest.mark.parametrize(
    "params, why",
    [
        ({"capabilities": {}}, "absent protocolVersion"),
        ({"protocolVersion": "not-a-version"}, "nonsense string"),
        ({"protocolVersion": MODERN_VERSION}, "modern-era version on initialize"),
        ({"protocolVersion": 20261028}, "non-string version"),
    ],
)
def test_initialize_counter_offers_instead_of_erroring(project: Path, params, why):
    """Anything outside the handshake set is counter-offered, never rejected.

    ADR-016 Must Not: "-32022 must not appear in a response to initialize."
    The handshake revisions mandate a counter-offer ("Otherwise, the server MUST
    respond with another protocol version it supports"), so an error there would
    be a regression for exactly the old clients the legacy surface exists for.

    The non-string case is included deliberately: on the *modern* surface a
    non-string version is -32602 (a shape defect), but the legacy surface has
    one rule with no exceptions, and a counter-offer is a valid answer to a
    malformed request that an old client can act on.
    """
    frame = {"jsonrpc": "2.0", "id": 220, "method": "initialize", "params": params}
    responses, _, _ = run_session(project, [frame])
    response = responses[220]
    assert "error" not in response, f"{why}: initialize must not error - {response}"
    assert response["result"]["protocolVersion"] == NEWEST_HANDSHAKE_VERSION, why
    assert_legacy_shape(response["result"], f"initialize ({why})")


def test_modern_unsupported_version_is_32022_with_an_era_scoped_supported_list(
    project: Path,
):
    """A modern-routed request naming a non-modern version gets -32022 + data.

    data.supported is era-scoped: only MODERN_PROTOCOL_VERSIONS, because a
    handshake revision cannot be reached through a modern envelope.
    """
    frames = [
        modern("tools/list", 230, version="2025-06-18"),
        modern("server/discover", 231, version="1999-01-01"),
    ]
    responses, _, _ = run_session(project, frames)
    for req_id, requested in ((230, "2025-06-18"), (231, "1999-01-01")):
        error = responses[req_id]["error"]
        assert error["code"] == UNSUPPORTED_PROTOCOL_VERSION
        assert error["data"] == {
            "supported": [MODERN_VERSION],
            "requested": requested,
        }
        assert "result" not in responses[req_id]


def test_modern_non_string_version_is_invalid_params(project: Path):
    """-32602, not -32022: a shape defect, not a negotiation failure.

    -32022 is the one code auto-negotiating clients do not fall back from, so
    it must not be spent on a malformed field.
    """
    frame = {
        "jsonrpc": "2.0",
        "id": 240,
        "method": "tools/list",
        "params": {
            "_meta": {PROTOCOL_VERSION_KEY: 20260728, CLIENT_CAPABILITIES_KEY: {}}
        },
    }
    responses, _, _ = run_session(project, [frame])
    error = responses[240]["error"]
    assert error["code"] == -32602
    assert PROTOCOL_VERSION_KEY in error["message"]


@pytest.mark.parametrize(
    "meta, missing",
    [
        ({PROTOCOL_VERSION_KEY: MODERN_VERSION}, CLIENT_CAPABILITIES_KEY),
        (None, PROTOCOL_VERSION_KEY),
    ],
)
def test_modern_incomplete_envelope_is_invalid_params(project: Path, meta, missing):
    """A modern-routed frame missing a required reserved key names it in -32602.

    The second case is server/discover with no _meta at all: it routes modern on
    its method name, then fails envelope validation. ADR-016 decides that
    precedence explicitly - the two error paths take precedence over the result.
    """
    method = "tools/list" if meta else "server/discover"
    params = {"_meta": meta} if meta else {}
    frame = {"jsonrpc": "2.0", "id": 250, "method": method, "params": params}
    responses, _, _ = run_session(project, [frame])
    error = responses[250]["error"]
    assert error["code"] == -32602
    assert missing in error["message"]


def test_enveloped_ping_is_method_not_found_but_version_errors_come_first(
    project: Path,
):
    """The open question: what does an enveloped `ping` return?

    Two answers, decided by which frame it is:

    * conformant envelope -> -32601. ADR-016 Exceptions: "`ping` remains
      implemented for legacy clients although revision 2026-07-28 removes it.
      It is reachable on a modern-routed request ... and the answer there is
      -32601, with no result stamping, because there is no result to stamp."
    * unsupported version in that envelope -> -32022, NOT -32601. ADR-016's
      Decision Contract Must is unqualified by method: "A modern-routed request
      declaring a version outside MODERN_PROTOCOL_VERSIONS is answered -32022
      ..., including when the method is server/discover" - `including` reads as
      emphasis on the hardest case, not as a restriction to it. The
      Confirmation bullet "An enveloped ping -> -32601" sits in a list where
      every other bullet names its envelope defect explicitly, so it describes
      the conformant-envelope case.

    The implementation is right, and -32022 is also the more actionable of the
    two: -32601 would tell a 2025-06-18 client that `ping` does not exist, when
    what is actually true is that its version cannot be spoken through an
    envelope. -32022 hands it a `supported` list to retry against.
    """
    frames = [
        modern("ping", 260),
        modern("ping", 261, version="2025-06-18"),
    ]
    responses, _, _ = run_session(project, frames)

    assert responses[260]["error"]["code"] == -32601
    assert "ping" in responses[260]["error"]["message"]
    # No result stamping on an error: there is no result to stamp.
    assert "result" not in responses[260]
    assert "data" not in responses[260]["error"]

    assert responses[261]["error"]["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert responses[261]["error"]["data"]["requested"] == "2025-06-18"


# ---------------------------------------------------------------------------
# Modern wire contract
# ---------------------------------------------------------------------------

def test_modern_result_shapes_per_method(project: Path):
    """resultType, _meta.serverInfo everywhere; cache hints only where cacheable."""
    frames = [
        modern("server/discover", 300),
        modern("tools/list", 301),
        modern_call("adr_status", {}, 302),
        modern("tools/list", 303),
    ]
    responses, _, _ = run_session(project, frames)

    discover = responses[300]["result"]
    assert_modern_shape(discover, "server/discover", cacheable=True)
    assert discover["supportedVersions"] == [MODERN_VERSION], (
        "supportedVersions is era-scoped: modern versions only (ADR-016)"
    )
    assert discover["capabilities"] == {"tools": {}}
    assert isinstance(discover["instructions"], str) and discover["instructions"]
    # DiscoverResult has neither field this revision; identity travels in _meta.
    assert "serverInfo" not in discover
    assert "protocolVersion" not in discover

    listing = responses[301]["result"]
    assert_modern_shape(listing, "modern tools/list", cacheable=True)
    assert [tool["name"] for tool in listing["tools"]] == EXPECTED_TOOL_ORDER

    called = responses[302]["result"]
    assert_modern_shape(called, "modern tools/call", cacheable=False)
    assert called["content"][0]["type"] == "text"
    assert json.loads(called["content"][0]["text"])["summary"]["total"] == 1

    # Deterministic ordering SHOULD: two listings, one order.
    assert responses[303]["result"]["tools"] == listing["tools"]


def test_modern_tool_failure_is_is_error_inside_a_complete_result(project: Path):
    """A tool-internal failure stays a result; an unknown tool name stays an error.

    ADR-016: "Tool-internal failures stay isError: true inside a
    resultType: 'complete' result; an unknown tool name stays a JSON-RPC error."
    """
    frames = [
        modern_call("adr_quality", {"adr_id": "ADR-999"}, 310),
        modern_call("adr_everything", {}, 311),
    ]
    responses, _, _ = run_session(project, frames)

    failed = responses[310]["result"]
    assert failed["isError"] is True
    assert_modern_shape(failed, "failing modern tools/call", cacheable=False)

    assert "result" not in responses[311]
    assert responses[311]["error"]["code"] == -32602
    assert "adr_everything" in responses[311]["error"]["message"]


# ---------------------------------------------------------------------------
# Legacy golden regression
# ---------------------------------------------------------------------------
#
# Byte-for-byte capture of what a handshake-era client received from the
# PRE-CHANGE server, so the dual-era work cannot silently alter it. Captured by
# driving the same frames through `git show 7d067a2:bin/adr-mcp` (v0.42.0, the
# last commit before TASK-58.1) against this same `project` fixture, then
# substituting the two environment-dependent values below.
#
# To regenerate after a deliberate change: run this test, take the `actual`
# line from the failure, and paste it in - but first make sure the change is
# deliberate, because that is the whole point of this test.
#
# Two placeholders, and no others:
#   {project} - the tmp_path fixture root, in every spelling the payloads use
#               (posix, native, and JSON-escaped native).
#   {version} - the server version read from .claude-plugin/plugin.json, which
#               moves with every release.
#
# One stored value is not a verbatim capture: adr-status's retrieval.index_error
# quoted the capture machine's native path, which normalised_status_payload()
# replaces on both sides before comparing, so it is stored as
# <captured-native-path> rather than leaking one developer's home directory.

GOLDEN_INITIALIZE_ID = 1
GOLDEN_STATUS_ID = 6

# The adr_lint (id 9) and adr_related (id 10) frames were captured when
# ADR-040 admitted those tools; they are additions to the surface, not
# alterations of any pre-change byte. Their payloads quote native OS paths
# (adr-lint's `target`/`repo_root`, adr-related's `path`), so like adr_status
# they are compared as JSON with separators normalised, never as bytes.
GOLDEN_LINT_ID = 9
GOLDEN_RELATED_ID = 10

# The adr_readiness frame (id 8) was regenerated once, for TASK-82. Readiness
# used to compute "quality" from three booleans; it now reads the weighted
# four-gate scorer, and the object carries `source`, `threshold` and
# `below_threshold` so a reader can tell a real score from the structural
# fallback. That is a deliberate change to what clients receive, which is
# exactly what this golden exists to make impossible by accident: it was
# updated on purpose, in the commit that changed the payload, and never as a
# way to make a failing test pass.

LEGACY_GOLDEN = r"""
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "adr-kit", "version": "{version}"}}}
{"jsonrpc": "2.0", "id": 2, "result": {}}
{"jsonrpc": "2.0", "id": 3, "result": {"tools": [{"name": "adr_context", "description": "Find the Architecture Decision Records most relevant to a task through the local generated index. Deterministic, key-free, and read-only; returns authority-labelled explained matches as JSON. The bounded subprocess timeout is 60 seconds.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Task description or question to rank ADRs against."}, "limit": {"type": "integer", "description": "Maximum number of ADRs to return.", "minimum": 1, "maximum": 100}, "paths": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 240}, "maxItems": 32, "description": "Target or changed paths used for Enforcement scope matching."}, "components": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 240}, "maxItems": 32}, "symbols": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 240}, "maxItems": 32}, "topics": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 240}, "maxItems": 32}, "statuses": {"type": "array", "items": {"type": "string", "enum": ["Accepted", "Proposed", "Superseded", "Rejected", "Deprecated", "Amended", "Unknown"]}, "uniqueItems": true, "maxItems": 7, "description": "Optional lifecycle-status filter."}, "authorities": {"type": "array", "items": {"type": "string", "enum": ["governing", "advisory", "historical"]}, "uniqueItems": true, "maxItems": 3, "description": "Optional authority filter."}, "include_history": {"type": "boolean", "description": "Permit historical ADRs; false by default."}, "strict_index": {"type": "boolean", "description": "Fail instead of using Markdown fallback."}, "min_score": {"type": "number", "minimum": 0, "maximum": 1}, "project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}, "required": ["query"]}}, {"name": "adr_judge", "description": "Judge a unified diff against the Enforcement blocks of Accepted ADRs (declarative pass only, no LLM, key-free). Returns findings and the adr-judge exit status (0 = clean, 1 = violations).", "inputSchema": {"type": "object", "properties": {"diff": {"type": "string", "description": "Unified diff text (e.g. output of git diff --cached)."}, "project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}, "required": ["diff"]}}, {"name": "adr_status", "description": "ADR repository health dashboard: totals, status breakdown, enforcement health, retirement candidates. Returns JSON.", "inputSchema": {"type": "object", "properties": {"project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}}}, {"name": "adr_quality", "description": "Score ADRs on quality via 4 gates (0.0-1.0 each, grade A-D). Pass adr_id (e.g. 'ADR-001' or '1') for one ADR; omit it to score every ADR in the repository. Returns JSON.", "inputSchema": {"type": "object", "properties": {"adr_id": {"type": "string", "description": "ADR identifier such as 'ADR-001', '001' or '1'. Omit to score all ADRs."}, "project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}}}, {"name": "adr_readiness", "description": "Inspect ADR lifecycle readiness and explicit implementation links. Read-only, deterministic, key-free, and incapable of accepting ADRs.", "inputSchema": {"type": "object", "properties": {"adr_id": {"type": "string", "description": "Optional ADR identifier such as ADR-011."}, "all_proposed": {"type": "boolean", "description": "Return every Proposed ADR."}, "base": {"type": "string", "description": "Optional git base ref; requires head."}, "head": {"type": "string", "description": "Optional git head ref; requires base."}, "today": {"type": "string", "description": "Optional deterministic YYYY-MM-DD evaluation date."}, "project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}}}, {"name": "adr_lint", "description": "Lint the ADR set against the deterministic verification gates. Read-only, key-free. Returns the adr-lint JSON report and exit status (0 = clean, 1 = failing findings).", "inputSchema": {"type": "object", "properties": {"strict": {"type": "boolean", "description": "CI governance mode: enable the schema gate and make findings FAIL. False by default."}, "project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}}}, {"name": "adr_related", "description": "Show the dependency graph (inbound + outbound edges) for one ADR: related decisions, supersession links, mentions, and dangling references. Read-only, deterministic. Returns JSON.", "inputSchema": {"type": "object", "properties": {"adr_id": {"type": "string", "description": "ADR identifier such as 'ADR-007', 'adr-7' or '7'."}, "project_root": {"type": "string", "description": "Absolute path to the active project. Use this for plugin-provided servers whose process starts in a plugin cache."}, "adr_dir": {"type": "string", "description": "Optional ADR directory. Relative paths are resolved from project_root."}}, "required": ["adr_id"]}}]}}
{"jsonrpc": "2.0", "id": 4, "result": {"content": [{"type": "text", "text": "[\n  {\n    \"adr_id\": \"ADR-001\",\n    \"title\": \"No Foo\",\n    \"path\": \"{project}/docs/adr/ADR-001-no-foo.md\",\n    \"status\": \"Accepted\",\n    \"is_accepted\": true,\n    \"authority\": \"governing\",\n    \"role\": \"primary\",\n    \"format\": \"canonical\",\n    \"decision_summary\": \"Do not use Foo.\",\n    \"scope\": [\n      \"src/**/*.py\"\n    ],\n    \"related_ids\": [],\n    \"metadata\": {\n      \"binding\": false,\n      \"gate\": null,\n      \"documents_shipped\": false,\n      \"verified_in\": [],\n      \"supersedes\": [],\n      \"superseded_by\": null\n    },\n    \"topics\": [],\n    \"aliases\": [],\n    \"components\": [],\n    \"symbols\": [],\n    \"context_scope\": \"selective\",\n    \"decision_contract\": {\n      \"must\": [],\n      \"must_not\": [],\n      \"exceptions\": [],\n      \"verification\": []\n    },\n    \"score\": 0.2,\n    \"signals\": {\n      \"title\": 0.2\n    },\n    \"matches\": [\n      {\n        \"field\": \"title\",\n        \"values\": [\n          \"No Foo\"\n        ]\n      }\n    ],\n    \"source\": \"markdown-fallback\",\n    \"engine\": \"markdown-fallback\",\n    \"schema_version\": 2,\n    \"redirected_from\": null\n  }\n]"}]}}
{"jsonrpc": "2.0", "id": 5, "result": {"content": [{"type": "text", "text": "{\n  \"exit_code\": 1,\n  \"verdict\": \"violation\",\n  \"result\": {\n    \"summary\": {\n      \"adrs_checked\": 1,\n      \"violations\": 2,\n      \"advisories\": 0\n    },\n    \"findings\": [\n      {\n        \"adr\": \"ADR-001\",\n        \"rule\": \"forbid_pattern\",\n        \"pattern\": \"\\\\bFoo\\\\b\",\n        \"path\": \"src/app/main.py\",\n        \"line\": 1,\n        \"snippet\": \"from lib import Foo\",\n        \"message\": \"No Foo.\",\n        \"severity\": \"violation\"\n      },\n      {\n        \"adr\": \"ADR-001\",\n        \"rule\": \"forbid_pattern\",\n        \"pattern\": \"\\\\bFoo\\\\b\",\n        \"path\": \"src/app/main.py\",\n        \"line\": 2,\n        \"snippet\": \"thing = Foo()\",\n        \"message\": \"No Foo.\",\n        \"severity\": \"violation\"\n      }\n    ]\n  }\n}"}]}}
{"jsonrpc": "2.0", "id": 6, "result": {"content": [{"type": "text", "text": "{\n  \"summary\": {\n    \"total\": 1,\n    \"by_status\": {\n      \"deprecated\": 0,\n      \"accepted\": 1,\n      \"proposed\": 0,\n      \"amended\": 0,\n      \"superseded\": 0,\n      \"unknown\": 0\n    },\n    \"health_pct\": 100.0,\n    \"avg_age_days\": 96.0,\n    \"with_enforcement\": 1,\n    \"enforcement_valid_pct\": 100.0,\n    \"coverage_pct\": 100.0,\n    \"llm_judge_pct\": 0.0,\n    \"accepted_declarative\": 1,\n    \"accepted_manual_review\": 0,\n    \"accepted_no_enforcement\": 0\n  },\n  \"adrs\": [\n    {\n      \"adr_id\": \"ADR-001\",\n      \"status\": \"Accepted\",\n      \"date\": \"2026-04-25\",\n      \"age_days\": 96,\n      \"has_enforcement\": true,\n      \"enforcement_valid\": true,\n      \"enforcement_types\": [\n        \"forbid_pattern\"\n      ],\n      \"title\": \"No Foo\"\n    }\n  ],\n  \"retirement_candidates\": [],\n  \"retrieval\": {\n    \"status\": \"degraded\",\n    \"source\": null,\n    \"schema_version\": null,\n    \"probe_file\": \"{project}/docs/adr/adr-context-probes.json\",\n    \"index_error\": \"generated ADR graph is missing: <captured-native-path>\",\n    \"metadata_mode\": \"advisory\",\n    \"metadata_findings\": [],\n    \"probes\": {\n      \"configured\": false,\n      \"summary\": {\n        \"total\": 0,\n        \"pass\": 0,\n        \"fail\": 0\n      },\n      \"results\": []\n    }\n  }\n}"}]}}
{"jsonrpc": "2.0", "id": 7, "result": {"content": [{"type": "text", "text": "{\n  \"adr_id\": \"ADR-001\",\n  \"overall\": 0.84,\n  \"grade\": \"B\",\n  \"gates\": {\n    \"completeness\": {\n      \"score\": 1.0,\n      \"issues\": [],\n      \"checks\": {\n        \"section_status\": true,\n        \"section_context\": true,\n        \"section_decision\": true,\n        \"section_alternatives_considered\": true,\n        \"section_consequences\": true,\n        \"section_related_decisions\": true,\n        \"section_references\": true,\n        \"decision_length_ok\": true,\n        \"alternatives_count_ok\": true,\n        \"consequences_not_empty\": true\n      }\n    },\n    \"evidence\": {\n      \"score\": 0.4,\n      \"issues\": [\n        {\n          \"code\": \"NO_MEASUREMENTS\",\n          \"detail\": \"\",\n          \"severity\": \"low\",\n          \"message\": \"No quantitative measurements found (e.g., '50 ms', '10 MB', '30%')\"\n        },\n        {\n          \"code\": \"NO_EXTERNAL_LINK\",\n          \"detail\": \"\",\n          \"severity\": \"low\",\n          \"message\": \"No external links found in the document; add https:// references\"\n        },\n        {\n          \"code\": \"NO_FILE_LINE_REF\",\n          \"detail\": \"\",\n          \"severity\": \"low\",\n          \"message\": \"No file:line references found (e.g., 'src/main.py:42')\"\n        }\n      ],\n      \"checks\": {\n        \"references_present\": true,\n        \"metrics_present\": false,\n        \"external_link_present\": false,\n        \"file_line_reference_present\": false\n      }\n    },\n    \"clarity\": {\n      \"score\": 0.8,\n      \"issues\": [\n        {\n          \"code\": \"CONTEXT_TOO_SHORT\",\n          \"detail\": \"23\",\n          \"severity\": \"medium\",\n          \"message\": \"Context section too short (23 chars, minimum 50)\"\n        }\n      ],\n      \"checks\": {\n        \"no_vague_language\": true,\n        \"has_title\": true,\n        \"acronyms_defined\": true,\n        \"context_sufficient\": false\n      }\n    },\n    \"consistency\": {\n      \"score\": 1.0,\n      \"issues\": [],\n      \"checks\": {\n        \"related_decisions_present\": true,\n        \"referenced_adrs_exist\": true,\n        \"valid_status\": true\n      }\n    }\n  },\n  \"issues\": [\n    {\n      \"code\": \"CONTEXT_TOO_SHORT\",\n      \"detail\": \"23\",\n      \"severity\": \"medium\",\n      \"message\": \"Context section too short (23 chars, minimum 50)\"\n    },\n    {\n      \"code\": \"NO_MEASUREMENTS\",\n      \"detail\": \"\",\n      \"severity\": \"low\",\n      \"message\": \"No quantitative measurements found (e.g., '50 ms', '10 MB', '30%')\"\n    },\n    {\n      \"code\": \"NO_EXTERNAL_LINK\",\n      \"detail\": \"\",\n      \"severity\": \"low\",\n      \"message\": \"No external links found in the document; add https:// references\"\n    },\n    {\n      \"code\": \"NO_FILE_LINE_REF\",\n      \"detail\": \"\",\n      \"severity\": \"low\",\n      \"message\": \"No file:line references found (e.g., 'src/main.py:42')\"\n    }\n  ],\n  \"recommendations\": [\n    \"Expand ## Context to > 50 chars; explain the problem and constraints\",\n    \"Add measurements to ## Consequences (e.g., '50 ms', '10 MB', '30%')\",\n    \"Add at least one https:// link in ## References\",\n    \"Add a file:line reference (e.g., 'src/main.py:42') in ## References\"\n  ],\n  \"file\": \"ADR-001-no-foo.md\"\n}"}]}}
{"jsonrpc": "2.0", "id": 8, "result": {"content": [{"type": "text", "text": "{\n  \"adr_dir\": \"docs/adr\",\n  \"adrs\": [\n    {\n      \"adr_id\": \"ADR-001\",\n      \"classification\": \"accepted\",\n      \"documents_shipped\": false,\n      \"evaluated_on\": \"2026-07-20\",\n      \"format\": \"canonical\",\n      \"human_decisions\": [],\n      \"human_findings\": [],\n      \"implementation_link\": {\n        \"blocking_proposed\": false,\n        \"changed_paths\": [],\n        \"evidence\": [],\n        \"implemented\": false,\n        \"linked\": false\n      },\n      \"mechanical_actions\": [],\n      \"mechanical_findings\": [],\n      \"next_command\": null,\n      \"open_questions\": [],\n      \"path\": \"ADR-001-no-foo.md\",\n      \"quality\": {\n        \"below_threshold\": false,\n        \"checks\": {\n          \"decision\": true,\n          \"evidence\": false,\n          \"open_questions_resolved\": true\n        },\n        \"score\": 0.84,\n        \"source\": \"adr-quality\",\n        \"threshold\": 0.7\n      },\n      \"related_adrs\": [],\n      \"status\": \"Accepted\",\n      \"title\": \"No Foo\",\n      \"verified_in\": []\n    }\n  ],\n  \"advisories\": [],\n  \"evaluated_on\": \"2026-07-20\",\n  \"schema_version\": 1,\n  \"summary\": {\n    \"advisory_count\": 0,\n    \"blocking_count\": 0,\n    \"blocking_proposed\": [],\n    \"total\": 1\n  }\n}"}]}}
{"jsonrpc": "2.0", "id": 9, "result": {"content": [{"type": "text", "text": "{\n  \"exit_code\": 0,\n  \"verdict\": \"ok\",\n  \"result\": {\n    \"target\": \"{project}/docs/adr\",\n    \"config_path\": null,\n    \"config_summary\": {\n      \"template.profile\": \"madr\",\n      \"context.retrieval_completeness\": \"advisory\"\n    },\n    \"strict_from_override\": null,\n    \"strict_mode\": false,\n    \"repo_root\": \"{project}\",\n    \"gates_enabled\": [\n      \"audit\",\n      \"completeness\",\n      \"consistency\"\n    ],\n    \"summary\": {\n      \"pass\": 1,\n      \"advisory\": 0,\n      \"fail\": 0,\n      \"skipped\": 0,\n      \"total\": 1\n    },\n    \"files\": [\n      {\n        \"file\": \"ADR-001-no-foo.md\",\n        \"adr_num\": 1,\n        \"bucket\": \"PASS\",\n        \"findings\": [],\n        \"migration_notice\": {\n          \"file\": \"{project}/docs/adr/ADR-001-no-foo.md\",\n          \"detected_format\": \"canonical\",\n          \"supported\": true,\n          \"metadata_change\": true,\n          \"metadata_issues\": [],\n          \"missing_sections\": [],\n          \"rename_to\": null,\n          \"writes_automatically\": false,\n          \"action\": \"deterministic-preview\",\n          \"deterministic\": true,\n          \"message\": \"Detected supported canonical ADR; canonical metadata can be added deterministically.\",\n          \"preview_command\": \"<command>\",\n          \"apply_command\": \"<command>\",\n          \"guided_command\": null\n        }\n      }\n    ],\n    \"migration_notices\": [\n      {\n        \"file\": \"{project}/docs/adr/ADR-001-no-foo.md\",\n        \"detected_format\": \"canonical\",\n        \"supported\": true,\n        \"metadata_change\": true,\n        \"metadata_issues\": [],\n        \"missing_sections\": [],\n        \"rename_to\": null,\n        \"writes_automatically\": false,\n        \"action\": \"deterministic-preview\",\n        \"deterministic\": true,\n        \"message\": \"Detected supported canonical ADR; canonical metadata can be added deterministically.\",\n        \"preview_command\": \"<command>\",\n        \"apply_command\": \"<command>\",\n        \"guided_command\": null\n      }\n    ],\n    \"exit_code\": 0\n  }\n}"}]}}
{"jsonrpc": "2.0", "id": 10, "result": {"content": [{"type": "text", "text": "{\n  \"adr\": {\n    \"adr_id\": \"ADR-001\",\n    \"title\": \"No Foo\",\n    \"status\": \"Accepted\",\n    \"path\": \"{project}/docs/adr/ADR-001-no-foo.md\"\n  },\n  \"outbound\": [],\n  \"inbound\": [],\n  \"dangling\": []\n}"}]}}
"""

LEGACY_GOLDEN_FRAMES = [
    INITIALIZE,
    INITIALIZED,
    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    call("adr_context", {"query": "heap allocation Foo", "limit": 3}, 4),
    call("adr_judge", {"diff": VIOLATING_DIFF}, 5),
    call("adr_status", {}, GOLDEN_STATUS_ID),
    call("adr_quality", {"adr_id": "ADR-001"}, 7),
    call("adr_readiness", {"adr_id": "ADR-001", "today": "2026-07-20"}, 8),
    call("adr_lint", {}, GOLDEN_LINT_ID),
    call("adr_related", {"adr_id": "ADR-001"}, GOLDEN_RELATED_ID),
]


def golden_lines() -> dict:
    return {
        json.loads(line)["id"]: line
        for line in LEGACY_GOLDEN.strip().splitlines()
        if line.strip()
    }


def server_version() -> str:
    manifest = REPO_ROOT / ".claude-plugin" / "plugin.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


def placeholderise(line: str, project: Path, version: str) -> str:
    """Replace the two environment-dependent values with their placeholders.

    Applied to the ACTUAL line, never to the golden: a tmp path that survives
    substitution then shows up in the diff instead of being papered over.
    Payloads spell the project root three ways - adr-context posix-normalises,
    adr-status quotes the native path, and the native path is JSON-escaped once
    by the tool payload and again by the JSON-RPC envelope.
    """
    variants = {str(project), str(project.resolve())}
    variants |= {v.replace("\\", "/") for v in list(variants)}
    variants |= {v.replace("\\", "\\\\") for v in list(variants)}
    variants |= {v.replace("\\", "\\\\\\\\") for v in list(variants)}
    for variant in sorted(variants, key=len, reverse=True):
        line = line.replace(variant, "{project}")
    return line.replace(version, "{version}")


def normalised_status_payload(text: str) -> dict:
    """adr-status is the one payload that cannot be compared as bytes.

    Three reasons, all proven rather than assumed by re-running the pre-change
    server twice against the same fixture:

    1. `summary.by_status` key order varied between processes (set iteration
       order), so two runs of the SAME binary already differed byte-wise.
       FIXED by TASK-66 -- the keys are sorted at construction. This function
       never normalised it (dict equality ignores key order), so the fix
       removes a reason without changing a line of code here.
    2. `summary.avg_age_days` and `adrs[].age_days` are computed from today's
       real date against the fixture ADR's Status date, so a byte golden would
       go stale overnight.
    3. `retrieval.index_error` quotes a native OS path, so its separators
       differ between Windows and Linux CI. `retrieval.probe_file` is an
       absolute resolved path for the same reason, and survives only because
       `placeholderise` substitutes the project root out of it.

    Reasons 2 and 3 are left standing deliberately (bin/adr-status's module
    docstring records why), so this frame cannot be tightened to a byte
    comparison. Everything else in the payload is compared exactly.
    """
    payload = json.loads(text)
    summary = payload.get("summary", {})
    if "avg_age_days" in summary:
        summary["avg_age_days"] = "<date-derived>"
    for adr in payload.get("adrs", []):
        if "age_days" in adr:
            adr["age_days"] = "<date-derived>"
    retrieval = payload.get("retrieval", {})
    if "index_error" in retrieval:
        retrieval["index_error"] = "<native-path>"
    return payload


def normalised_path_payload(text: str):
    """Parse a payload and normalise OS path separators in every string.

    adr_lint and adr_related quote native paths (lint's `target` and
    `repo_root`, related's `path`), so their golden frames cannot be compared
    as bytes across Windows and POSIX. Migration-notice command fields embed
    the absolute path of the adr-kit checkout that ran the capture, so they
    are masked entirely. Both sides of the comparison pass through this, so a
    genuine payload change still fails the test.
    """
    masked_keys = {"preview_command", "apply_command", "guided_command"}

    def walk(value, key=None):
        if isinstance(value, str):
            if key in masked_keys:
                return "<command>"
            return value.replace("\\", "/")
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {k: walk(item, k) for k, item in value.items()}
        return value

    return walk(json.loads(text))


def test_legacy_wire_output_is_byte_identical_to_the_pre_change_server(project: Path):
    """initialize, ping, tools/list and all seven tools/call shapes, unchanged.

    This is the guard that serving a second era did not alter one byte of what
    today's clients receive. ADR-016 Must Not: "No legacy-routed result may
    carry resultType, _meta.serverInfo, ttlMs or cacheScope."
    """
    lines, _ = run_session_lines(project, LEGACY_GOLDEN_FRAMES)
    golden = golden_lines()
    version = server_version()
    actual = {json.loads(line)["id"]: line for line in lines}

    assert sorted(actual) == sorted(golden), "one response line per request, no extras"

    for req_id in sorted(golden):
        got = placeholderise(actual[req_id], project, version)
        want = golden[req_id]
        if req_id == GOLDEN_STATUS_ID:
            got_obj, want_obj = json.loads(got), json.loads(want)
            assert list(got_obj) == list(want_obj), "adr_status JSON-RPC frame changed"
            assert list(got_obj["result"]) == list(want_obj["result"]), (
                "adr_status envelope changed: legacy results carry `content` only"
            )
            got_payload = normalised_status_payload(
                got_obj["result"]["content"][0]["text"]
            )
            want_payload = normalised_status_payload(
                want_obj["result"]["content"][0]["text"]
            )
            assert got_payload == want_payload, (
                "adr_status payload changed (both sides carry the three "
                "documented normalisations)"
            )
            continue
        if req_id in (GOLDEN_LINT_ID, GOLDEN_RELATED_ID):
            got_obj, want_obj = json.loads(got), json.loads(want)
            assert list(got_obj) == list(want_obj), "JSON-RPC frame changed"
            assert list(got_obj["result"]) == list(want_obj["result"]), (
                "envelope changed: legacy results carry `content` only"
            )
            got_payload = normalised_path_payload(
                got_obj["result"]["content"][0]["text"]
            )
            want_payload = normalised_path_payload(
                want_obj["result"]["content"][0]["text"]
            )
            assert got_payload == want_payload, (
                f"payload changed for request {req_id} (path separators "
                "normalised on both sides)"
            )
            continue
        assert got == want, f"legacy wire output changed for request {req_id}"


def test_legacy_golden_covers_the_whole_legacy_surface():
    """The golden is only a guard if it actually covers every legacy method."""
    golden = golden_lines()
    assert len(golden) == 10
    methods = {frame["method"] for frame in LEGACY_GOLDEN_FRAMES if "id" in frame}
    assert methods == {"initialize", "ping", "tools/list", "tools/call"}
    tools = {
        frame["params"]["name"]
        for frame in LEGACY_GOLDEN_FRAMES
        if frame.get("method") == "tools/call"
    }
    assert tools == EXPECTED_TOOLS
    # The version-bearing frame really does exercise the placeholder.
    assert "{version}" in golden[GOLDEN_INITIALIZE_ID]


# ---------------------------------------------------------------------------
# Dual-era robustness
# ---------------------------------------------------------------------------

def test_unknown_method_and_notifications_are_handled_in_both_eras(project: Path):
    """-32601 for an unknown method in either era; every notification dropped."""
    frames = [
        {"jsonrpc": "2.0", "id": 400, "method": "resources/list"},
        modern("resources/list", 401),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
        {"jsonrpc": "2.0", "method": "notifications/progress", "params": {"_meta": envelope()}},
        {"jsonrpc": "2.0", "method": "notifications/invented-by-a-client"},
        {"jsonrpc": "2.0", "id": 402, "method": "ping"},
    ]
    responses, parse_errors, _ = run_session(project, frames)
    assert responses[400]["error"]["code"] == -32601
    assert responses[401]["error"]["code"] == -32601
    assert not parse_errors
    # Exactly three replies: notifications produce nothing at all, in both eras.
    assert set(responses) == {400, 401, 402}
    assert responses[402]["result"] == {}


def test_out_of_scope_client_fields_are_tolerated_not_rejected(project: Path):
    """MRTR and logLevel are out of scope, which means ignored - not refused.

    ADR-016 explicitly scopes out MRTR (`inputResponses`, `requestState`) and
    `io.modelcontextprotocol/logLevel`: "It must nonetheless tolerate a client
    that sends them."
    """
    modern_frame = modern(
        "tools/list",
        410,
        {"inputResponses": [], "requestState": "opaque-blob"},
        meta_extra={LOG_LEVEL_KEY: "debug", "progressToken": 7},
    )
    legacy_frame = {
        "jsonrpc": "2.0",
        "id": 411,
        "method": "tools/list",
        "params": {
            "inputResponses": [],
            "requestState": "opaque-blob",
            "_meta": {LOG_LEVEL_KEY: "debug", "progressToken": 7},
        },
    }
    responses, _, _ = run_session(project, [modern_frame, legacy_frame])

    assert_modern_shape(responses[410]["result"], "modern + MRTR fields", cacheable=True)
    assert len(responses[410]["result"]["tools"]) == len(EXPECTED_TOOLS)
    # logLevel alone is not the version sentinel, so this one stays legacy.
    assert_legacy_shape(responses[411]["result"], "legacy + MRTR fields")


def test_malformed_json_does_not_kill_a_dual_era_session(project: Path):
    """A bad line costs one -32700 and nothing else, with modern frames on both sides."""
    lines, _ = run_session_lines(
        project,
        [modern("tools/list", 420), modern("server/discover", 421)],
        raw_lines=["}{ not json", "[1, 2, 3]"],
    )
    frames = [json.loads(line) for line in lines]
    by_id = {frame["id"]: frame for frame in frames if frame.get("id") is not None}
    assert {frame["error"]["code"] for frame in frames if frame.get("id") is None} == {
        -32700,
        -32600,
    }
    assert_modern_shape(by_id[420]["result"], "tools/list after a bad line", cacheable=True)
    assert_modern_shape(by_id[421]["result"], "discover after a bad line", cacheable=True)


def test_no_response_ever_carries_a_forbidden_error_code(project: Path):
    """Asserted on emitted frames, not on file text.

    A grep for "-32020" would false-positive on the comment at
    bin/adr-mcp:685-689, which names both codes precisely to record why they
    are unreachable. So this drives every error path the server has and reads
    the codes off the wire, including the id-less parse-error frames that
    run_session() buckets separately.
    """
    frames = [
        {"jsonrpc": "2.0", "id": 500, "method": "resources/list"},
        modern("resources/list", 501),
        modern("ping", 502),
        modern("tools/list", 503, version="2025-06-18"),
        modern("server/discover", 504, version="nonsense"),
        {"jsonrpc": "2.0", "id": 505, "method": "server/discover"},
        {
            "jsonrpc": "2.0",
            "id": 506,
            "method": "tools/list",
            "params": {"_meta": {PROTOCOL_VERSION_KEY: 1, CLIENT_CAPABILITIES_KEY: {}}},
        },
        {"jsonrpc": "2.0", "id": 507, "method": "tools/list", "params": {"_meta": {PROTOCOL_VERSION_KEY: MODERN_VERSION}}},
        call("adr_everything", {}, 508),
        modern_call("adr_everything", {}, 509),
        {"jsonrpc": "2.0", "id": 510},
        {"jsonrpc": "2.0", "id": 511, "method": 42},
        modern_call("adr_quality", {"adr_id": "ADR-999"}, 512),
        # An unhashable tool name raises inside handle_tools_call before the
        # handler's own guard, so it reaches dispatch's catch-all: the only
        # frame in this battery that produces -32603, in either era.
        {
            "jsonrpc": "2.0",
            "id": 513,
            "method": "tools/call",
            "params": {"name": ["adr_status"], "arguments": {}},
        },
        modern("tools/call", 514, {"name": {"nested": 1}, "arguments": {}}),
        # Malformed arguments stay a tool error, not a JSON-RPC error.
        call("adr_status", "not-an-object", 515),
        {"jsonrpc": "2.0", "id": 516, "method": "ping"},
    ]
    lines, _ = run_session_lines(
        project, frames, raw_lines=["definitely not json", "12345"]
    )
    frames = [json.loads(line) for line in lines]
    codes = [frame["error"]["code"] for frame in frames if "error" in frame]
    assert codes, "the battery must actually produce errors"
    forbidden = sorted({code for code in codes if code not in ALLOWED_ERROR_CODES})
    assert not forbidden, (
        f"forbidden JSON-RPC error codes emitted: {forbidden}. ADR-016 Must Not: "
        "no -32020, no -32021, no undefined code in -32020..-32099, and no new "
        "code in the legacy -32000..-32019 range."
    )
    # Every code in the allowlist is observed, so the allowlist is a statement
    # about frames that were actually emitted rather than about codes nobody
    # reached: an unobserved entry would weaken the assertion above silently.
    assert set(codes) == ALLOWED_ERROR_CODES, (
        f"battery no longer reaches every allowed code: missing "
        f"{sorted(ALLOWED_ERROR_CODES - set(codes))}"
    )
    # ...and the loop survived all of it.
    by_id = {frame["id"]: frame for frame in frames if frame.get("id") is not None}
    assert by_id[516]["result"] == {}
    assert by_id[515]["result"]["isError"] is True


# ===========================================================================
# TASK-69: stdio transport encoding (UTF-8 + LF), independent of host locale
# ===========================================================================
#
# The MCP stdio transport mandates UTF-8 and newline-delimited framing. Python
# opens std streams in text mode using the platform default, so on a cp1252
# host the server emitted the cp1252 byte 0x97 for U+2014 (invalid UTF-8),
# raised UnicodeEncodeError on U+2192 (turning a tool result into -32603), and
# translated the trailing "\n" to "\r\n".
#
# Two things make these tests bite where the rest of this file cannot:
#
#   1. They read raw BYTES. Every other helper here drives the server with
#      text=True, encoding="utf-8", which *imposes* the correct encoding on the
#      child and hides the defect completely.
#   2. They force PYTHONIOENCODING=cp1252 on the child rather than merely
#      unsetting it. Unsetting reproduces the bug only on a cp1252 host, so the
#      test would be dead weight on Linux CI, where the default is already
#      UTF-8. Forcing a hostile encoding makes the assertion meaningful on
#      every platform: the server must override it.
#
# The fixture ADR carries characters chosen for two distinct failure modes:
# U+2014 maps to a single cp1252 byte (silent corruption), while U+2192 has no
# cp1252 mapping at all (hard encode error).

NON_ASCII_ADR = """\
# ADR-001 Café Encoding — Naïve Approach → Rejected

## Status

Accepted, 2026-04-25.

## Context

The naïve approach — decoding with the platform default — corrupts data.
Round-trip: bytes → text → bytes.

## Decision

Do not use Foo. Encode everything as UTF-8; the naïve platform default
mangles any character outside the host's codepage.

## Alternatives Considered

- Platform default: rejected — mangles U+2014 and U+2192.
- UTF-8: accepted.

## Consequences

**Positive:**
- Correct round-trip for é, ü, —, →.

**Negative:**
- Must pin the encoding explicitly.

## Related Decisions

- None.

## References

- ./bench/résultats.txt
"""


def _run_session_bytes(project_root: Path, messages: list, child_encoding: str):
    """Drive the server with a hostile locale and return raw stdout bytes.

    Deliberately no text=True and no encoding=: the bytes on the wire are the
    thing under test, so nothing may decode them on our behalf.
    """
    payload = ("\n".join(json.dumps(m) for m in messages) + "\n").encode("utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = child_encoding
    proc = subprocess.run(
        [sys.executable, str(ADR_MCP), "--root", str(project_root)],
        input=payload,
        capture_output=True,
        env=env,
        timeout=120,
    )
    return proc.stdout, proc.stderr


@pytest.fixture()
def non_ascii_project(tmp_path: Path) -> Path:
    """A project whose ADR content is not representable in cp1252."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-cafe-encoding.md").write_text(
        textwrap.dedent(NON_ASCII_ADR), encoding="utf-8"
    )
    return tmp_path


def test_frames_are_utf8_and_lf_terminated_under_a_hostile_locale(non_ascii_project):
    """Every frame decodes as UTF-8 and ends with a bare LF, not CRLF."""
    stdout, _stderr = _run_session_bytes(
        non_ascii_project,
        [INITIALIZE, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}],
        child_encoding="cp1252",
    )

    stdout.decode("utf-8")  # raises UnicodeDecodeError if the wire is not UTF-8

    assert b"\r\n" not in stdout, (
        "frames must be LF-terminated; found CRLF, which means text-mode "
        "newline translation is still active"
    )
    assert stdout.count(b"\n") == 2, "expected exactly two newline-framed replies"


def test_non_ascii_stdin_is_decoded_as_utf8_not_the_host_codepage(non_ascii_project):
    """The read side is pinned too, proven by echoing the input back.

    An unknown tool name is echoed verbatim in the error message, which
    makes it the one place a client-supplied string provably survives the
    round trip. Without the stdin pin, Python decodes our UTF-8 bytes as
    cp1252: the JSON still parses (those bytes are all valid cp1252), so
    nothing raises -- the name is simply, silently, the wrong string. That
    is the failure mode worth a test, because no error ever surfaces it.
    """
    name = "adr_café_—"
    stdout, _stderr = _run_session_bytes(
        non_ascii_project,
        [
            INITIALIZE,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": {}},
            },
        ],
        child_encoding="cp1252",
    )
    replies = {
        json.loads(line)["id"]: json.loads(line)
        for line in stdout.decode("utf-8").splitlines()
        if line.strip()
    }
    message = replies[2]["error"]["message"]
    assert name in message, (
        f"tool name was mangled in transit: {message!r}"
    )


def test_non_ascii_adr_content_survives_the_round_trip(non_ascii_project):
    """ADR characters reach the wire intact, as UTF-8 bytes.

    The title carries U+2014 (a single byte in cp1252, so it corrupts silently)
    and U+2192 (no cp1252 mapping at all, so it raised UnicodeEncodeError).
    Asserting on the raw bytes is what makes this meaningful: a decoded-string
    assertion would pass even if the server wrote the wrong bytes, because the
    test would have picked the encoding itself.

    adr_status is used rather than adr_context because it reports on every ADR,
    so the assertion does not hinge on a relevance score.
    """
    stdout, _stderr = _run_session_bytes(
        non_ascii_project,
        [
            INITIALIZE,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "adr_status", "arguments": {}},
            },
        ],
        child_encoding="cp1252",
    )
    stdout.decode("utf-8")
    assert bytes([0x97]) not in stdout, (
        "U+2014 leaked onto the wire as the cp1252 byte 0x97"
    )
    assert "�".encode("utf-8") not in stdout, "content was replaced with U+FFFD"

    replies = {
        json.loads(line)["id"]: json.loads(line)
        for line in stdout.decode("utf-8").splitlines()
        if line.strip()
    }
    assert "error" not in replies[2], replies[2].get("error")
    body = json.dumps(replies[2], ensure_ascii=False)
    assert "Café Encoding — Naïve Approach → Rejected" in body, (
        f"the ADR title did not survive intact: {body[:400]}"
    )
