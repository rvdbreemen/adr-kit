"""End-to-end tests for bin/adr-mcp: the thin MCP stdio server.

Drives the server as a subprocess over stdin/stdout with newline-delimited
JSON-RPC 2.0 messages, mirroring how Claude Code, Codex, GitHub Copilot CLI,
or another stdio MCP client talks to a server. All messages for a scenario are written in
one batch and the responses are matched back by request id, which keeps the
tests deadlock-free without threads.
"""
from __future__ import annotations

import json
import importlib.machinery
import importlib.util
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
}

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


def run_session(project_root: Path, messages: list, raw_lines: list = None):
    """Send messages (plus optional raw lines) to the server, return
    (responses_by_id, stderr). Input is closed after writing, so the server
    exits on EOF and we can read everything without threads."""
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
    responses = {}
    parse_errors = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)  # every stdout line must be valid JSON-RPC
        if obj.get("id") is None:
            parse_errors.append(obj)
        else:
            responses[obj["id"]] = obj
    return responses, parse_errors, proc.stderr


def call(tool_name: str, arguments: dict, req_id: int) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def tool_text(response: dict) -> str:
    content = response["result"]["content"]
    assert len(content) == 1 and content[0]["type"] == "text"
    return content[0]["text"]


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


def test_initialize_echoes_client_protocol_version(project: Path):
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


# ---------------------------------------------------------------------------
# Gate adr-mcp-dual-era-v1 (ADR-016)
# ---------------------------------------------------------------------------
#
# ADR-016 is Accepted and binding, and names this gate. The gate is the
# evidence that the decision holds. Its full conformance suite is TASK-58.3;
# until TASK-58.1 and TASK-58.2 land, the requirements below are unmet by
# construction, so this test is registered as an expected failure rather than
# silently skipped. Deleting the xfail marker is how the gate goes live.

GATE_ADR_MCP_DUAL_ERA_V1 = "adr-mcp-dual-era-v1"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gate adr-mcp-dual-era-v1: dual-era support is not implemented yet "
        "(TASK-58.1 / TASK-58.2). Remove this marker when it is."
    ),
)
def test_gate_adr_mcp_dual_era_v1_server_discover(project: Path):
    """server/discover MUST be answered, not rejected as an unknown method."""
    discover = {
        "jsonrpc": "2.0",
        "id": 900,
        "method": "server/discover",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
    }
    responses, _, _ = run_session(project, [discover])
    result = responses[900].get("result")
    assert result is not None, "server/discover must return a result, not an error"
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28"]
    assert result["cacheScope"] == "public"
    assert isinstance(result["ttlMs"], int)
    assert "tools" in result["capabilities"]
    # Identity travels in _meta; DiscoverResult has no top-level serverInfo.
    assert "serverInfo" not in result
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "adr-kit"
