# Agent and Client Integration

## Overview

- **Name**: Agent and Client Integration (`agent-integration`)
- **Description**: Every path by which an LLM agent or CLI client reaches the adr-kit engine. Four
  distinct mechanisms, deliberately separate: a hand-rolled **MCP stdio server** the agent calls on
  purpose; a **lifecycle-hook runtime** that pushes ADR context into the session unasked; an
  **instruction layer** of skills, prompts and one subagent that tells the agent which deterministic
  CLI to run and when; and a **capability registry plus desired-state installer** that makes the
  first three exist on a machine and records honestly what each client cannot do.
- **Type**: Integration and distribution layer — an MCP service, a hook runtime, a declarative
  registry, an installer library, and a prose instruction corpus. It owns no ADR semantics; every
  path here terminates in a `bin/` CLI.
- **Technology**: Python 3.10+ (stdlib only; zero third-party runtime packages), Rust (one committed
  `windows-x64` native hook host, `std` only), one polyglot `cmd.exe`/POSIX-`sh` script, JSON-RPC 2.0
  over stdio, JSON file contracts, and 64 Markdown + 1 YAML files of model-facing prose.

### One-sentence shape per path

| Path | Direction | Shape |
|---|---|---|
| MCP | pull | `stdin line -> dispatch() -> subprocess(sys.executable, bin/<cli>) -> stdout line` |
| Hooks | push | `client event -> run-hook.cmd -> native or Python host -> ADR-INDEX.json -> one JSON line` |
| Skills / prompts | instruct | `slash command -> SKILL.md prose -> agent runs bin/<cli> with the documented flags` |
| Installer | provision | `detect -> plan -> prepare per-user payload -> smoke-test -> native plugin manager under a lock` |

---

## Purpose

adr-kit's decision semantics live in `bin/` and its libraries. This component exists so that three
CLI coding agents with genuinely different hook models, plugin managers and output formats all reach
those same semantics — and so that an agent about to edit a file already has the governing Accepted
ADRs in its context rather than having to think to ask.

It solves four problems:

1. **Machine-readable access without a key.** The MCP server exposes retrieval, judging, health,
   quality and readiness as five read-only tools. No `mcp` SDK, no network, no credential, no LLM
   path. `adr-suggest` is deliberately *not* exposed because its value is LLM-only.
2. **Context arrival before the mistake.** The hooks implement ADR-004's session, prompt, edit and
   subagent/compact injection tiers. Every path exits 0 and prints nothing rather than blocking.
3. **Same outcome, three clients.** `clients/capabilities.json` declares the seven required outcomes
   and the per-client event mappings; where a client genuinely cannot do something (Copilot has no
   pre-edit hook) the gap is a *registered degradation* with a named fixture, not silence.
4. **Instructions that make deterministic tooling fire at the right moment.** The 15 skills carry the
   reasoning — the four verification gates, the nine anti-rationalisation guards, the immutability
   rule — that no CLI flag can encode.

**The boundary that defines this component**: nothing in it enforces. ADR-004 puts blocking
authority solely in `bin/adr-judge` at pre-commit (component `bin-cli-enforcement`). Every mechanism
here is advisory and fail-open, and that posture is structural rather than incidental —
[`hooks/adr-hook.py:36`](../hooks/adr-hook.py) catches `BaseException` (including
`KeyboardInterrupt` and `SystemExit`) and returns 0, with an inline comment recording why. Do not
narrow it to `except Exception`.

### Governing ADRs

Verified against each record's frontmatter and `## Enforcement` block. Only two mechanically-enforced
rules exist across this entire component; everything else is prose governance.

| ADR | Strength here | What it binds |
|---|---|---|
| **ADR-011** — deterministic readiness, human-gated grilling | **Mechanically enforced, twice.** `require_pattern "adr_readiness"` with `path_glob: bin/adr-mcp` ("MCP must expose deterministic readiness without lifecycle mutation") and `require_pattern "grill"` with `path_glob: clients/workflows.json`. | The `adr_readiness` tool must stay present and read-only; the `grill` workflow must stay in the catalog. |
| **ADR-010** — certify three native CLI clients through one outcome contract | **Enforced on the schema, not the data.** Both `require_pattern` rules glob `schemas/client-capabilities.schema.json`. | The closed three-client roster, the seven required outcomes, the documented-degradation rule, the 300/400-line module budgets, "equal outcomes not identical event names". |
| **ADR-004** — layered ADR context injection | Prose-governing. Enforcement block present but empty. | The four injection tiers the hooks implement, the `PreToolUse` `Edit\|MultiEdit\|Write` matcher, bounded injected content, and the single fail-closed pre-commit floor. Names the MCP `adr_context` tool as the key-free exposure of the task tier. |
| **ADR-014** — generated ADR graph as the selective-context query engine | Component-level claim, no `path_glob` here. `binding: true`, gate `index-first-retrieval`; `verified_in` names `hooks/adr_hook_core.py`, `components[]` includes `adr-mcp`. | Hook and query hot paths stay local, deterministic, bounded, stdlib-first, model-free, key-free. No service, database, embedding model or LLM in the hook path. |
| **ADR-015** — two-second deterministic latency budget as a fixture contract | Prose-governing the hook half only; its `path_glob` is `tests/fixtures/cli/latency-corpus.json`. | Every deterministic CLI *or hook* path keeps p50/p95/hard budgets in a committed fixture with measured evidence. The hook corpus (`tests/fixtures/hooks/reference-corpus.json`, method `adr-kit-hook-latency-v1`) satisfies this; **`bin/adr-mcp` has no entry in either corpus**. |
| **ADR-006** — prepare platform-local marketplaces for native installs | Prose-governing `payload.py` and `native.py`; Enforcement block empty. | Validate source, copy to a versioned per-user directory, patch only the copy, prove MCP `initialize`+`tools/list` before touching a client marketplace, isolate failures per client. |
| **ADR-005** — selectable ADR body profiles | Prose-governing the profile handling in `skills/migrate` and `skills/adr`; its `path_glob` is `schemas/adr-kit-config.schema.json`. | `adr profiles --format json` discovery before scaffolding; accept only a returned `available: true` id. |

**ADR-012 does not govern this component.** Verified: its text contains zero occurrences of "hook"
and its decision is release version-consistency across marketplace manifests.

**ADR-016 exists but does not govern yet.** A drafted record,
`docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md`, is
`status: "Proposed"`, dated 2026-07-29, and **untracked in git** (`git status` reports `??`). It is
the decision TASK-58's AC #12 required and which the Code-phase MCP document correctly reported as
not existing. Its Enforcement block already names `bin/adr-mcp` directly — `require_pattern` for
`MODERN_PROTOCOL_VERSIONS`, `UNSUPPORTED_PROTOCOL_VERSION` and `server/discover`, `forbid_import` on
`^\s*(?:import|from)\s+(?:mcp|mcp_types|…)` (the rejected official SDK), and a `forbid_pattern` on
the current verbatim protocol-echo expression. Because `bin/adr-judge` reads the Enforcement block of
**Accepted** ADRs only, none of that is applied today. Treat it as a drafted intent, not a constraint.

---

## Software Features

### MCP surface

| Feature | Description |
|---|---|
| Hand-rolled stdio MCP server | 763 lines, newline-delimited JSON-RPC 2.0, no `Content-Length` framing, no `mcp` SDK, no `pydantic`. Four methods: `initialize`, `ping`, `tools/list`, `tools/call`. |
| Five read-only tools | `adr_context`, `adr_judge`, `adr_status`, `adr_quality`, `adr_readiness`. Each is a subprocess call into a sibling `bin/` CLI via `sys.executable`. No tool can mutate ADR lifecycle state. |
| Key-free by construction | `adr_judge` omits `--llm` *and* injects `ADR_KIT_NO_LLM=1` into the child environment; `adr-suggest` is excluded from the tool set on purpose. Belt and braces — but see the notable finding: neither is machine-checked. |
| Per-call workspace override with containment | Every tool accepts optional `project_root` (must be absolute and exist) and `adr_dir`; `_call_paths` asserts `adr_dir.relative_to(root)` so an untrusted argument cannot point outside the project. |
| Bounded argument validation | `limit` 1–100, six list options capped at 32 items × 240 chars, `statuses`/`authorities` enum-checked, `min_score` clamped to 0–1, `base`/`head` must be supplied together. |
| Crash isolation | Zero import-level coupling to the shared `bin/adr_*.py` modules — the only `bin/` entry point in the repository that reaches its siblings purely by subprocess. Buys exact CLI/MCP outcome parity at the cost of one interpreter startup per call. |

### Hook runtime

| Feature | Description |
|---|---|
| Polyglot single-file dispatcher | `hooks/run-hook.cmd` is simultaneously valid batch and valid `sh`. Line 1 `: << 'CMDBLOCK'` makes `sh` discard the whole batch half as a here-document; `cmd.exe` runs the batch half and exits before reaching the shell half. |
| Fastest-host selection | Platform native binary → `$ADR_KIT_PYTHON` → the install-time-substituted `__ADR_KIT_PYTHON__` pin → `python3`/`python`/`py -3` → exit 0 having done nothing. |
| One normalized envelope | `hooks/adr_hook_core.py` maps any client's snake_case/camelCase payload onto a frozen `Envelope` dataclass, resolving 14 event aliases and 10 aliased key families. |
| Four ADR-004 injection tiers | `SessionStart` (global-scope Accepted ADRs + readiness queue), `UserPromptSubmit` (query by prompt), `PreToolUse`/`PostToolUse` (governing ADRs for the edit path), `SubagentStart`/`PreCompact` (bounded parent-context relay, no index read). |
| Bounded everything | 64 KiB stdin (read as `64*1024+1` so overflow is *detectable*, not silently truncated), 4 KiB injected context, 8 KiB parent context, 3 results, 2 MiB index cap, 256 KiB queue cap. |
| Index-first retrieval | `_query` calls `query_adr_context(..., strict_index=True)` — use the generated graph or nothing, never parse Markdown on the hot path (ADR-014). |
| Cross-process dedupe | A canonical signature written to `<tempdir>/adr-kit-hook-<session>.seen` via write-temp-then-`os.replace`; any `OSError` returns `False`, so dedupe failure never suppresses context. |
| Per-invocation kill switch | `adr_kit_disabled: true` in the payload → immediate silent noop in both hosts. |
| Path-traversal and injection guards | `_safe_edit_path` returns `None` when `resolved.relative_to(workspace)` raises; `_safe_source_argument` allowlists `[A-Za-z0-9_./\\ -]{1,4096}` before a path is interpolated into a suggested command; a queue entry is honoured only if `command` equals exactly `/adr-kit:grill <ADR-\d{3,4}>`. |
| Native hot-path host | `hooks/native/adr-hook.rs` (630 lines) reimplements the protocol dependency-free: hand-rolled JSON scanner, glob matcher, FNV-1a dedupe, own weighted ranking. Committed as a 248,832-byte `windows-x64` binary. |
| Honest latency measurement | `hook_benchmark.measure` includes process startup, gives each sample a unique `agent_id` so dedupe cannot fake a fast noop, and counts a timeout in `timeout_count` while still appending its elapsed time so percentiles inflate rather than lie. |

### Instruction layer

| Feature | Description |
|---|---|
| 15 canonical rich skills | Hand-authored `SKILL.md` files, 3,730 lines, the `canonical-rich` corpus for `claude-code-cli`. Carry the four verification gates, nine anti-rationalisation guards, the immutability rule, the migrate patterns A–H, and a lint severity decision tree written as a Graphviz `digraph`. |
| Frontmatter as an enforced contract | `disable-model-invocation: true` on 8 of 15 makes them user-only; `allowed-tools` is the host-enforced allowlist; `argument-hint` is the documented positional contract. |
| One authoring subagent | `agents/adr-generator.md`, `tools: Read, Write, Edit, Glob, Grep, Bash`, `model: sonnet`, reached by name through the Claude Code `Task` tool. Six skills declare `Task` and may delegate. |
| Three shared instruction documents | `instructions/ADR-guide.md`, `adr.coding.md`, `adr.review.md` — copied byte-for-byte into `codex/instructions/` and `copilot/instructions/` (only `ADR-guide.md` gets a provenance line). |
| 45 generated prompt stubs | Three per-client corpora of 15, produced by `render_prompt(workflow, label, client_id) -> bytes`. Byte-identical modulo the client id in the line-1 provenance comment and the label in line 4 — verified by diff. |

### Installer and capability registry

| Feature | Description |
|---|---|
| Read-only detection | `detect_clients` resolves each bare client id on `PATH`, runs `--version`, and requires the spec's `version_marker` case-insensitively in stdout+stderr. Never writes, never invokes a plugin manager. Both `which` and `runner` are injectable. |
| Immutable desired-state plan | Every dataclass is `frozen=True`. `build_plan` derives `current_state`/`desired_state` per client and sets `requires_confirmation` on a major-version change. `--plan` renders it without touching anything. |
| Four-gate source validation | Every required file present; every required JSON parses; `repository` equals exactly `https://github.com/rvdbreemen/adr-kit.git`; all five version sites agree. |
| Ownership-marked payload preparation | Builds into `<version>.tmp`, copies the allowlisted public payload, patches *only the copy*, restores Unix exec bits, writes `.adr-kit-prepared-source.json` with a `payload_sha256`, re-validates, then `target -> .old` and `.tmp -> target`. The marker's presence is the **only** thing authorizing deletion or replacement of a directory. |
| Real smoke tests before activation | `validate_prepared_mcp` drives an actual JSON-RPC handshake against the prepared server; `validate_prepared_hooks` runs `run-hook.cmd session-start` and requires exit 0 plus valid JSON on any non-empty stdout. |
| Per-client lock, evidence and rollback | `client_lock` (`O_CREAT\|O_EXCL`, 15-minute staleness) wraps `apply()` then `validate()`; on any `BaseException` it rolls back and writes `<state_root>/evidence/<client>-last-transaction.json` with `healthy`/`rolled-back`/`failed`. |
| CRLF-stable content hashing | `payload_digest` normalizes `\r\n` to `\n` before hashing and hook wrappers are written with `newline="\n"`, so a Windows and a Unix checkout of the same release produce the same digest. |
| Declared degradations with fixtures | Three entries in `clients/exceptions.json`, each bound to a fixture whose `exception_id` must match; a degradation cannot be claimed in prose without a committed fixture behind it. |

---

## Code Elements

| Code document | Role in this component |
|---|---|
| [`c4-code-bin-cli-mcp.md`](c4-code-bin-cli-mcp.md) | The **pull** path: `bin/adr-mcp`, a single-file stdio MCP server wrapping five sibling CLIs as read-only tools. |
| [`c4-code-hooks.md`](c4-code-hooks.md) | The **push** path: dispatcher, shared normalize/retrieve/evaluate core, three per-client adapters, native Rust host, latency harness. |
| [`c4-code-agent-surface.md`](c4-code-agent-surface.md) | The **instruction** path: 15 skills, 1 subagent, 3 shared instruction documents, 45 generated prompt stubs. Zero executable code. |
| [`c4-code-clients-installer.md`](c4-code-clients-installer.md) | The **provisioning** path plus the honesty ledger: the three-client capability/workflow/exception registry and the seven-module desired-state installer library. |

---

## Interfaces

### 1. MCP stdio server — `bin/adr-mcp`

**Protocol**: newline-delimited JSON-RPC 2.0 on stdin/stdout. One message per line, one response line
per request, strictly serialised. Startup banner on stderr.

**CLI**: `adr-mcp [--root DIR] [--adr-dir DIR]`. Root resolution: `--root` > `PROJECT_ROOT` env >
`os.getcwd()`. Exit 0 on EOF or `KeyboardInterrupt`; exit 2 only when the resolved root is not a
directory. Never exits non-zero for a tool or protocol failure.

| Method | Behaviour |
|---|---|
| `initialize` | `{protocolVersion, capabilities: {tools: {}}, serverInfo: {name: "adr-kit", version}}`. **Echoes the client's requested `protocolVersion` verbatim.** |
| `ping` | `{}` |
| `tools/list` | `{tools: [...5...]}` in literal `TOOL_DEFINITIONS` order. No pagination cursor, no `ttlMs`/`cacheScope`. |
| `tools/call` | MCP content result, or a *successful* result carrying `isError: true`. |
| `notifications/*` | Silently dropped, no reply — including `notifications/cancelled`. |
| anything else, incl. `server/discover` | `-32601 Method not found` |

| Tool | Required / optional arguments | Delegates to (subprocess, `cwd=root`) |
|---|---|---|
| `adr_context` | **`query`**; `limit` 1–100; `paths`/`components`/`symbols`/`topics` (≤32 × ≤240 chars); `statuses`, `authorities` (enums); `include_history`, `strict_index`; `min_score` 0–1 | `bin/adr-context --format json --adr-dir …` |
| `adr_judge` | **`diff`** (unified diff on stdin) | `bin/adr-judge --diff - --snapshot diff --json`, env `ADR_KIT_NO_LLM=1` |
| `adr_status` | none | `bin/adr-status --format json` |
| `adr_quality` | `adr_id` | `bin/adr-quality --format json <file>`, **one process per ADR file** |
| `adr_readiness` | `adr_id`, `all_proposed`, `base`+`head` (together), `today` | `bin/adr-readiness --format json --repo-root … --adr-dir …` |

All five additionally accept the workspace pair `project_root` (absolute) and `adr_dir` (must resolve
inside `project_root`).

**Two-layer error model — the single most likely integration mistake.** Malformed frames and
unroutable methods are real JSON-RPC errors (`-32700`, `-32600`, `-32601`, `-32602`, `-32603`). *Every
tool failure* — bad argument type, non-zero CLI exit, missing ADR directory, the 60-second
`CLI_TIMEOUT_S` — is a **successful** result with `isError: true`. And `adr_judge` exit code 1
(violations found) is **not** an error: it returns `{"exit_code": 1, "verdict": "violation",
"result": {...}}`. Only exit 2 becomes `isError`. `adr_quality` is polymorphic: a bare report when
`adr_id` was given, `{"adrs": [...]}` when omitted.

### 2. MCP client wiring — JSON file contract

Three near-identical files, differing only in how the plugin root is expressed. `validate_manifests`
([`scripts/client_generation_artifacts.py:137-142`](../scripts/client_generation_artifacts.py))
requires `mcpServers["adr-kit"]` in all three.

| File | `command` | `args` | `cwd` |
|---|---|---|---|
| [`.mcp.json`](../.mcp.json) | `python` | `${CLAUDE_PLUGIN_ROOT}/bin/adr-mcp` | unset |
| [`codex/.mcp.json`](../codex/.mcp.json) | `python` | `./bin/adr-mcp` | `.` |
| [`copilot/.mcp.json`](../copilot/.mcp.json) | `python` | `${PLUGIN_ROOT}/bin/adr-mcp` | `.` |

### 3. Lifecycle hook registration — JSON file contract, three shapes

Generated from [`hooks/manifest.json`](../hooks/manifest.json) by `native_hook_config(manifest,
client_id)`. **This settles the question the Code phase left open**: Claude Code's registration is
*convention discovery* of `hooks/hooks.json` at the plugin root, and the generator actively forbids
the alternative — `validate_manifests` raises `GenerationError("Claude must use plugin-root
hooks/hooks.json")` if a `hooks` key appears in `.claude-plugin/plugin.json`
([`scripts/client_generation_artifacts.py:120-125`](../scripts/client_generation_artifacts.py)).
Codex and Copilot must declare their paths as exact strings, also generator-checked.

| Client | Registration file | Manifest declaration | Schema |
|---|---|---|---|
| `claude-code-cli` | `hooks/hooks.json` | **none** — `hooks` key forbidden | Nested `{hooks: {Event: [{hooks: [{type, command, timeout}], matcher?}]}}`, `${CLAUDE_PLUGIN_ROOT}`, 6 events |
| `codex-cli` | `codex/hooks/hooks.json` | `"hooks": "./hooks/hooks.json"` | Same nesting plus `commandWindows` with `%PLUGIN_ROOT%`, 6 events |
| `github-copilot-cli` | `copilot/hooks.json` (client **root**) | `"hooks": "hooks.json"` | Flat lowerCamel `{version: 1, hooks: {sessionStart: [{type, bash, powershell, cwd, timeoutSec}]}}`, **3 events** |

Six canonical events with their committed budgets:

| Event id | Matcher | Runner timeout | p50 / p95 / hard (ms) | Copilot |
|---|---|---|---|---|
| `session-start` | — | 5 s | 50 / 150 / 500 | `sessionStart` |
| `user-prompt-submit` | — | 5 s | 75 / 250 / 500 | `userPromptSubmitted` |
| `pre-tool-use` | `Edit\|MultiEdit\|Write` | 1 s | 25 / 50 / 100 | **null** |
| `post-tool-use` | `Edit\|MultiEdit\|Write` | 1 s | 25 / 50 / 100 | `postToolUse` |
| `subagent-start` | — | 1 s | 30 / 100 / 250 | **null** |
| `pre-compact` | — | 1 s | 30 / 100 / 500 | **null** |

**Copilot bypasses the polyglot dispatcher entirely.** Its `bash` branch runs `python3
"${PLUGIN_ROOT}/hooks/adr-hook.py" … || true` directly and its `powershell` branch re-implements
native-first host selection inline (`if (Test-Path $native) { & $native … } else { Get-Command
python … }; exit 0`). Verified in `_copilot_hook_config`
([`scripts/client_generation_artifacts.py:181-206`](../scripts/client_generation_artifacts.py)):
`run-hook.cmd` appears in neither branch. So `run-hook.cmd`'s host-selection ladder — the
`$ADR_KIT_PYTHON` override, the `__ADR_KIT_PYTHON__` install-time pin, the `py -3` fallback — governs
Claude and Codex only. Copilot gets a hardcoded `python3` on POSIX and no honouring of the
install-time interpreter pin.

### 4. Hook dispatcher and host CLIs

```
run-hook.cmd <event> [client]        # POSITIONAL, event first; client defaults to claude-code-cli
adr-hook.py --client {claude-code-cli,codex-cli,github-copilot-cli} [--event <EventName>]
adr-hook.exe --client <id> [--event <EventName>]
```

`--client` is required and enum-validated in the Python host — the *only* path in the whole hook
cluster that can exit non-zero, because argparse rejects it outside the `try`. The native host
silently exits 0 instead. Neither host supports `--flag=value`. Unknown extra flags are tolerated
(`parse_known_args`).

### 5. Hook stdin/stdout JSON contract

**In**: one JSON object, ≤ 65,536 bytes. Aliased key families: event
(`hook_event_name`/`hookEventName`/`event`), workspace (`cwd`/`workspace`/`workspace_root`), tool name
(`tool_name`/`toolName`/`tool_name_normalized`), tool input (`tool_input`/`toolInput`/`tool`), edit
path (`file_path`/`filePath`/`path`/`notebook_path`), prompt (`prompt`/`user_prompt`/`userPrompt`),
parent context (`parent_context`/`parentContext`/`adr_context`), session, agent, version. Kill switch:
`adr_kit_disabled: true`.

**Out**: zero or one line of compact JSON (`separators=(",",":")`, `ensure_ascii=False`).

| Client | Shape |
|---|---|
| `claude-code-cli` | `{"suppressOutput":true,"hookSpecificOutput":{"hookEventName":…,"additionalContext":…}}` |
| `codex-cli` | `{"hookSpecificOutput":{…}}` — same nesting, no `suppressOutput` |
| `github-copilot-cli` | `{"additionalContext":…}` flat, **and `{}` when `kind == "pre-edit"`** |

Copilot's pre-edit suppression is the registered ADR-010 degradation
`copilot-pretool-context-limit` — emitting pre-edit context to a client with no pre-edit hook would
be a false promise. The docstring calls the `postToolUse` mapping "an honest post-edit backstop".

**Exit code: always 0**, asserted at four independent levels (`except BaseException` in Python,
`Option`-returning `run()` in Rust, `exit /b 0` / `|| true` on every dispatcher branch, and two
dedicated protocol tests).

### 6. Guardian SessionStart entry — the second, independent injection producer

[`templates/cc-settings/guardian-hook-entry.json`](../templates/cc-settings/guardian-hook-entry.json)
is a JSON snippet installed under `hooks.SessionStart[0].hooks[]` in a project's
`.claude/settings.json`. Its `command` resolves the plugin root with `ls -d
~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1`, then tries
`python3`/`python`/`py`, then runs `bin/adr-guardian check`, `timeout: 10`, ending in `|| true`.

This is a genuinely separate mechanism from the plugin-level hook. Zero files under `hooks/` reference
`adr-guardian`, and `bin/adr-guardian` is not in `HOOK_RUNTIME_FILES`. One session can therefore
receive two independently-produced `SessionStart` context blocks: the plugin hook's ADR context via
`adr_hook_core`, and the `[adr-guardian]` health nudge via the project settings entry. The entry
declares `"_remove_marker": "adr-guardian-session-start"` as its uninstall handle — for which a
repo-wide grep finds **no reader** outside the generated mirrors.

### 7. Skill, prompt and subagent invocation

| Client | Invocation template | Skill mode | Skill root |
|---|---|---|---|
| `claude-code-cli` | `/adr-kit:{workflow}` | `canonical-rich` | `skills/` (hand-authored) |
| `codex-cli` | `$adr-kit:{workflow}` | `generated` | `codex/skills/` |
| `github-copilot-cli` | `adr-kit:{workflow}` | `generated` | `copilot/skills/` |

Fifteen workflow ids, identical across all three: `adr`, `context`, `grill`, `guardian`, `init`,
`install-hooks`, `judge`, `lint`, `migrate`, `related`, `retire`, `review`, `setup`, `supersede`,
`upgrade`. Every skill takes `$ARGUMENTS` as one positional string; `argument-hint` is the contract
(e.g. `grill` accepts exactly one of `ADR-NNN | --pr N | --range BASE...HEAD | --source PATH |
--revalidate ADR-NNN | --all-proposed`; `guardian` accepts `cheap|llm|all`; `install-hooks` accepts
only `--uninstall`).

**Subagent**: `agents/adr-generator.md`, reached by the name `adr-generator` through the Claude Code
`Task` tool. Six skills declare `Task` and may delegate: `guardian`, `init`, `judge`, `review`,
`supersede`, `upgrade`.

The skills' real interface to the engine is the set of `bin/` invocations their bodies instruct the
agent to run — `bin/adr accept ADR-NNN`, `bin/adr-context --format json --limit 5 "<topic>"`,
`bin/adr-judge --snapshot staged --llm --json`, `bin/adr-guardian stamp cheap --violations N …`,
`bin/adr-readiness --format json`, `bin/adr-migrate --plan docs/adr/`, and so on.

### 8. Capability registry — JSON file contracts

| File | Contract |
|---|---|
| [`clients/capabilities.json`](../clients/capabilities.json) | `$schema: ../schemas/client-capabilities.schema.json`, `schema_version: 1`. Five blocks: `program_scope` (three `first_class_clients`, `future_epic: "TASK-43"`), `ownership` (canonical / generated / hand_authored_validated), `settings` (`precedence: ["project","global","detected-default"]`), `clients` (seven `required_outcomes`, `event_mappings`, `degradations`, `probes`, `settings_keys`), `certification` (`windows_native_required: true`, `all_clients_block_release: true`). |
| [`clients/workflows.json`](../clients/workflows.json) | `schema_version: 1`. Per-client `label`/`skill_mode`/`skill_root`/`prompt_root`/`invocation`, plus 15 workflows each with `id`, `title`, `description`, `mutates`, ordered `procedure[]`. The single source for every generated skill and prompt. |
| [`clients/exceptions.json`](../clients/exceptions.json) + `clients/fixtures/*.json` | Three degradations, each with `fixture`, `rationale`, `user_effect`; the fixture's `exception_id` must equal the registry id. |

The seven required outcomes: `workflow-discovery`, `task-context`, `edit-governance`, `mcp`,
`pre-commit`, `lifecycle`, `doctor`.

### 9. Installer library — Python import surface (no CLI of its own)

`from clients.installer import CLIENT_IDS, SPECS, ClientSpec, DetectedClient, ClientPlan,
InstallPlan, ClientResult` — contract types only; `__all__` re-exports **no functions**, so every real
consumer imports from the submodules. Callers must first put the repo root on `sys.path`; the package
is not installed.

Reached in practice through `scripts/install-agent-envs.py` (component `packaging-ci`):

```
--clients/--agents <auto|comma-list>  --source PATH  --project-root PATH  --python EXE
--install-root PATH  --global-settings FILE  --format human|json
--dry-run  --plan  --yes  --skip-validation  --detect-only  --uninstall
```

Exit 0 success (including `--plan` and `--detect-only`), 1 per-client failures, 2 no supported CLI
detected. Inside the library, every failure raises `RuntimeError` with a human-readable message;
`detect_client` raises `ValueError` only for an unknown client id; an absent client is `None`, not an
exception.

### 10. Installer state and evidence — JSON file contracts

| Artefact | Shape |
|---|---|
| `<install_root>/<safe_version>/.adr-kit-prepared-source.json` | `{source, version, python, platform, payload_sha256}` — the ownership token |
| `<state_root>/evidence/<client>-last-transaction.json` | `{schema_version: 1, client, status: healthy\|rolled-back\|failed, started_at_epoch, finished_at_epoch}` plus `error`/`rollback_error` |
| `<state_root>/updates/<client>.json` | `{schema_version: 1, client, version, trigger, last_check_epoch}` |
| Install plan (`--plan --format json`) | `{schema_version: 1, adr_kit: {version, source, source_sha256}, settings: {…}, clients: [ClientPlan…], requires_confirmation: bool}` |

### 11. Native plugin-manager protocol — subprocess, three different output shapes

| Client | Marketplace listing | Plugin listing | Version change |
|---|---|---|---|
| `claude` | `plugin marketplace list --json` → JSON **array** keyed by `name` | `plugin list --json`, match `id == "adr-kit@rvdbreemen-adr-kit"` and `scope == "user"` | `plugin update` / `install --scope user` |
| `codex` | `plugin marketplace list --json` → JSON **object**, `payload["marketplaces"]` | `payload["installed"]` keyed by `pluginId` | no `update` verb: `remove` then `add` |
| `copilot` | no JSON at all — **substring search** over stdout+stderr | substring `"adr-kit"` | `plugin install` |

Post-activation gate `validate_install` requires `adr-kit@<marketplace>` in `plugin list`, and for
Codex and Copilot additionally `adr-kit` in `mcp list`.

### 12. MCP handshake as an install gate

`_validate_mcp_process` speaks MCP over stdio (protocol `2025-06-18`): `initialize` →
`notifications/initialized` → `tools/list`, asserts stderr contains `serving root=<resolved cwd> `,
and asserts the advertised tool set is **exactly**
`{adr_context, adr_judge, adr_status, adr_quality, adr_readiness}`
([`clients/installer/payload.py:335`](../clients/installer/payload.py)). This is the interface where
the MCP path and the installer path meet, and it is a hard coupling — see notable finding 4.

---

## Dependencies

### Components used

| Slug | Mechanism |
|---|---|
| `bin-cli-retrieval` | MCP `adr_context` → **subprocess** `bin/adr-context --format json`. Hooks read the `docs/adr/ADR-INDEX.json` graph that `bin/adr-index` **generates** (a JSON file on disk, not a call). |
| `bin-cli-enforcement` | MCP `adr_judge` → **subprocess** `bin/adr-judge --diff - --json` with `ADR_KIT_NO_LLM=1`. Also the fail-closed floor this whole component must never replace. |
| `bin-cli-gates` | MCP `adr_quality` → **subprocess** `bin/adr-quality --format json <file>`, one process per ADR. |
| `bin-cli-lifecycle` | MCP `adr_status` → **subprocess** `bin/adr-status --format json`. The guardian `SessionStart` entry → **subprocess** `bin/adr-guardian check`. Skills drive `bin/adr`, `adr-guardian`, `adr-doctor`, `adr-retire`. |
| `bin-cli-readiness` | MCP `adr_readiness` → **subprocess** `bin/adr-readiness --format json`. Hooks read the `docs/adr/.adr-kit-readiness.json` queue that `adr-guardian refresh-readiness` writes. |
| `bin-lib-semantic-core` | The one **import** edge out of this component: `hooks/adr_hook_core.py:15-19` injects `<root>/bin` into `sys.path` and imports `query_adr_context`, `IndexQueryError` from `bin/adr_query.py`. Python host only — the Rust host reimplements retrieval instead. |
| `bin-cli-migration` | Skills drive `bin/adr-migrate --plan` / `--to-profile` (prose reference only). |
| `bin-lib-doctor` | **Inbound consumer**: `bin/adr_doctor_probes.py` imports `detect_clients` and `from hooks.hook_benchmark import measure`, and drives a 4-message MCP session asserting the exact five-tool set. `bin/adr_doctor_checks.py` imports `CLIENT_IDS`, `detect_clients`. |
| `schemas-templates` | `schemas/client-capabilities.schema.json` validates the registry (and carries ADR-010's enforcement). `templates/cc-settings/guardian-hook-entry.json` and `templates/githooks/pre-commit` are the project-side copy-out artefacts. |
| `packaging-ci` | Owns the generator (`scripts/build-client-adapters.py` → `client_generation*.py`) that renders skills, prompts and every `hooks.json` from this component's registries, and owns the real install entry point `scripts/install-agent-envs.py` plus the project-side `scripts/project_setup.py`. |
| `generated-distributions` | `codex/` and `copilot/` are **generated** downstream projections, not hand-synced copies: `bin` is one of the four `COPY_ROOTS` (`scripts/client_generation_model.py:31`, consumed at `client_generation.py:145`), so `codex/bin/adr-mcp` and `copilot/bin/adr-mcp` are written by `scripts/build-client-adapters.py` and drift-checked by `--check` in three CI workflows. `codex/hooks/` and `copilot/hooks/` carry the 8 `HOOK_RUNTIME_FILES`; `codex/skills/` and `copilot/skills/` are the thin generated corpora. Edit `bin/`, then re-run the generator — never edit a mirror. |
| `tests` | Protocol, parity, latency and contract certification: `test_adr_mcp.py` (24 subprocess-driven tests), `test_hook_protocol.py`, `test_hook_performance.py`, `test_agent_installer.py`, `test_client_adapter_generation.py`, `test_client_capabilities_schema.py`. |

### External systems

| System | How reached | Note |
|---|---|---|
| `claude`, `codex`, `copilot` CLIs | `subprocess` — `--version`, `plugin marketplace list/add/remove`, `plugin list/install/update/uninstall`, `mcp list` | Three different output shapes; Copilot has none and is matched by substring |
| Target Python interpreter | `-c` probe by `validate_python`; embedded as the patched MCP `command`; `sys.executable` for every MCP tool subprocess | Minimum 3.10 |
| `cmd.exe` / POSIX `sh` / PowerShell | Both halves of `run-hook.cmd`; `cmd.exe /d /c` or `sh` for the hook smoke test; PowerShell for Copilot's own hook branch | |
| `where` / `command -v` / `shutil.which` | Interpreter and client discovery | |
| `git` | Reached *indirectly*: `adr_readiness` with `base`/`head`, `adr-judge`'s snapshot logic, and the skills' documented `git diff`/`log`/`merge-base`/`config core.hooksPath` commands | `bin/adr-mcp` itself shells out only to `sys.executable` |
| `gh` (GitHub CLI) | Optional PR metadata in the `review` and `grill` skill prose | Documented to degrade honestly when absent |
| `claude` CLI as a model | Only through the skills' documented `adr-judge --llm` / `adr-suggest` paths | **Never** through MCP or hooks — both are key-free |
| `rustc` | Build-time only, manual per `hooks/native/README.md` | No CI step compiles the `.rs` files |
| `kernel32.dll` | Link-time `ExitProcess` in the `no_std` floor probe | |
| Filesystem and OS | Per-user data roots (`%LOCALAPPDATA%`, `~/Library/Application Support`, `$XDG_DATA_HOME`); `os.open` with `O_CREAT\|O_EXCL` for locking; `os.replace` for atomic swaps; POSIX `chmod`; the OS temp directory for hook dedupe state | |
| Environment | Read: `PROJECT_ROOT`, `ADR_KIT_PYTHON`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME`. Written for probes: `CLAUDE_PLUGIN_ROOT`, `PLUGIN_ROOT`, `COPILOT_PLUGIN_ROOT` | |
| **Network** | **None.** `hooks/manifest.json` declares `network_allowed: false`; no code in this component opens a socket, reads a credential, or invokes a model | |

---

## Component Diagram

```mermaid
flowchart TB
    subgraph AGENTS["Agent CLI clients (ADR-010: closed roster of three)"]
        CC["Claude Code CLI"]
        CX["Codex CLI"]
        CP["GitHub Copilot CLI"]
    end

    subgraph AI["agent-integration"]
        direction TB

        subgraph SURFACE["agent-surface — instruction layer (prose, no code)"]
            SK["skills/*/SKILL.md<br/>15 canonical-rich, 3730 lines<br/>gates · guards · immutability"]
            AG["agents/adr-generator.md<br/>Task tool, model: sonnet"]
            INS["instructions/ x3<br/>copied verbatim to both mirrors"]
            PR["prompts/&lt;client&gt;/*.md<br/>45 generated stubs"]
        end

        subgraph MCPS["bin-cli-mcp — pull path"]
            SRV["bin/adr-mcp<br/>JSON-RPC 2.0 over stdio<br/>initialize · ping · tools/list · tools/call"]
            TOOLS["5 read-only tools<br/>adr_context · adr_judge · adr_status<br/>adr_quality · adr_readiness<br/>key-free: ADR_KIT_NO_LLM=1"]
            MJ["*.mcp.json x3<br/>mcpServers['adr-kit']"]
        end

        subgraph HOOKS["hooks — push path (ADR-004 tiers, always exit 0)"]
            HJ["hooks.json x3 shapes<br/>generated from manifest.json<br/>Claude: convention-discovered"]
            DISP["run-hook.cmd<br/>polyglot cmd + sh<br/>&lt;event&gt; &lt;client&gt;"]
            NAT["hooks/bin/windows-x64/adr-hook.exe<br/>Rust, own JSON scanner + rank()"]
            PYH["adr-hook.py -> adr_hook_core.py<br/>Envelope · evaluate() · bounded"]
            AD["adapters/ claude · codex · copilot<br/>copilot returns {} on pre-edit"]
        end

        subgraph INST["clients-installer — provisioning + honesty ledger"]
            REG["capabilities.json · workflows.json<br/>exceptions.json + 3 fixtures"]
            DET["detection.py — read-only"]
            PLN["planning.py — frozen InstallPlan"]
            PAY["payload.py (exactly 400 lines)<br/>validate_source · prepare · smoke-test"]
            NTV["native.py — per-client plugin manager"]
            TX["transaction.py — lock · evidence · rollback"]
        end
    end

    subgraph ENGINE["Deterministic engine (other components)"]
        CTX["bin-cli-retrieval<br/>adr-context · adr-index"]
        JUD["bin-cli-enforcement<br/>bin/adr-judge = THE fail-closed floor"]
        QUA["bin-cli-gates<br/>adr-quality · adr-lint"]
        LIF["bin-cli-lifecycle<br/>adr · adr-guardian · adr-status"]
        RDY["bin-cli-readiness<br/>adr-readiness"]
        QRY["bin-lib-semantic-core<br/>bin/adr_query.py"]
    end

    subgraph DATA["Generated data contracts on disk"]
        IDX[("docs/adr/ADR-INDEX.json<br/>ADR-007 graph, schema_version 2")]
        QUE[("docs/adr/.adr-kit-readiness.json<br/>Proposed queue, 24h TTL")]
        SEEN[("tempdir/adr-kit-hook-&lt;sid&gt;.seen")]
    end

    subgraph EXT["External"]
        PM["native plugin managers<br/>claude / codex / copilot"]
        FS[("per-user data root<br/>adr-kit/marketplaces/&lt;version&gt;")]
        GIT["git · gh"]
        GEN["packaging-ci<br/>build-client-adapters.py<br/>install-agent-envs.py"]
    end

    CC -->|"/adr-kit:{workflow}"| SK
    CX -->|"$adr-kit:{workflow}"| PR
    CP -->|"adr-kit:{workflow}"| PR
    SK -->|"Task tool, by name"| AG
    INS -.->|"names adr-generator,<br/>but no agents/ dir in either mirror"| AG

    SK ==>|"prose instructs: run bin/&lt;cli&gt;"| CTX
    SK ==> JUD
    SK ==> QUA
    SK ==> LIF
    AG ==> CTX
    AG ==> QUA

    CC -->|"stdio JSON-RPC"| SRV
    CX --> SRV
    CP --> SRV
    MJ -.->|"wires command+args"| SRV
    SRV --> TOOLS
    TOOLS -->|"subprocess sys.executable, cwd=root"| CTX
    TOOLS -->|"subprocess + ADR_KIT_NO_LLM=1"| JUD
    TOOLS --> QUA
    TOOLS --> LIF
    TOOLS --> RDY

    CC -->|"registered event"| DISP
    CX -->|"registered event"| DISP
    CP -->|"bypasses run-hook.cmd:<br/>python3 adr-hook.py directly"| PYH
    HJ -.->|"registers"| DISP
    DISP -->|"native present"| NAT
    DISP -->|"else interpreter chain"| PYH
    PYH -->|"import query_adr_context<br/>strict_index=True"| QRY
    QRY --> IDX
    NAT -->|"hand-rolled JSON scan,<br/>own weighted rank()"| IDX
    PYH --> QUE
    NAT --> QUE
    PYH --> SEEN
    NAT --> SEEN
    PYH --> AD
    CTX -->|"generates"| IDX
    RDY -->|"feeds"| QUE

    AD -->|"one compact JSON line,<br/>advisory only"| CC
    NAT -.->|"same 3 shapes as format! templates"| CC

    GEN -->|"renders from"| REG
    REG -->|"15 workflow ids"| PR
    REG -->|"existence check only"| SK
    REG -->|"native_hook_config()"| HJ
    GEN -->|"drives"| DET
    DET --> PLN
    PLN --> PAY
    PAY -->|"copy · patch · atomic swap"| FS
    PAY -->|"initialize + tools/list<br/>exact 5-tool set equality"| SRV
    PAY -->|"run-hook.cmd session-start<br/>must exit 0"| DISP
    PAY -->|"PREPARED_MARKER"| NTV
    TX -->|"apply/validate/rollback"| NTV
    NTV -->|"plugin marketplace / plugin / mcp"| PM
    DET -.->|"--version"| PM

    SK -.-> GIT
    AD -.->|"never blocks"| JUD
```

---

## Notable findings carried forward

### Corrections to the Code-phase documents

Two Code-phase statements do not survive component-level cross-checking. Both are corrected here
rather than dropped, because a reader holding this document and its Code Elements together would
otherwise have to adjudicate a contradiction themselves.

**1. `c4-code-bin-cli-mcp.md` finding 4 is retracted: the mirrors *are* generated, and CI
drift-checks them.** That document reported "no generator that writes `codex/bin/` or `copilot/bin/`"
and flagged hand-syncing as an unresolved risk. Verified from primary source instead:
`COPY_ROOTS = ("bin", "schemas", "templates", "instructions")` and
`COPY_EXCLUSIONS = {"bin/bump-version"}` at
[`scripts/client_generation_model.py:31-32`](../scripts/client_generation_model.py), consumed at
[`scripts/client_generation.py:145`](../scripts/client_generation.py), which also lists
`<client>/<root>` for every `GENERATED_CLIENTS` value in `generated_roots` so the orphan sweep covers
them. `python scripts/build-client-adapters.py --check` runs in `validate.yml:149`,
`release-candidate.yml:48` and `release-publish.yml:64`. **Actionable consequence**: a TASK-58 edit to
`bin/adr-mcp` propagates by re-running the generator, not by hand-editing three files — and CI blocks
if it is not re-run. (Caveat from finding 17: use `--check` when verifying. The bare write invocation
rewrites files as LF, which makes the check pass locally and hides TASK-57.)

**2. The three `adr-mcp` copies are no longer byte-identical, and the drift is real content.** The
Code phase measured them `diff`-clean. As of this writing `bin/adr-mcp` is 773 lines while
`codex/bin/adr-mcp` and `copilot/bin/adr-mcp` are 763; all three have zero CR bytes, so this is *not*
the TASK-57 line-ending artefact. `--check` now reports 15 drift entries rather than 13, the two new
ones being `codex/bin/adr-mcp` and `copilot/bin/adr-mcp`. See finding 1 for what changed and why it
matters.

### Ranked findings

Ranked by how likely each is to bite a maintainer or an integrator.

1. **The MCP server implements the handshake era only, and now has a drafted-but-not-Accepted
   decision.** `DEFAULT_PROTOCOL_VERSION = "2025-06-18"`; `server/discover` is unrouted and answers
   `-32601`; `handle_initialize` **echoes the client's requested `protocolVersion` verbatim**, so it
   will claim to speak `2026-07-28` or any arbitrary string without implementing it, with no
   intersection against a supported set and no `-32022 UnsupportedProtocolVersion`; `dispatch()` never
   checks that `initialize` arrived first, so a modern-only client that skips the probe gets
   `tools/call` silently processed under legacy semantics. The echo is currently *asserted as
   intended* by `tests/test_adr_mcp.py:203-208`. Per the spec's own backward-compatibility rules a
   dual-era client must not key its fallback to a specific error code, so it correctly classifies
   this server as legacy — **non-compliant, not broken**. Tracked as TASK-58 (To Do, high, 12 ACs),
   now joined by an untracked TASK-58.1 ("version registry, negotiation and wire-derived era
   detection").

   **Work is in progress in the working tree, and right now the docstring is ahead of the code.**
   Verified state: `bin/adr-mcp` is modified but uncommitted, and `git diff` shows the change is
   **entirely inside the module docstring** — 13 insertions, 3 deletions, no executable line touched.
   That new docstring asserts the server "Serves BOTH protocol eras from one process (ADR-016)" with
   `server/discover`, `resultType`, `_meta.serverInfo` and `ttlMs`/`cacheScope`. The implementation
   does not do any of that yet: `MODERN_PROTOCOL_VERSIONS`, `HANDSHAKE_PROTOCOL_VERSIONS`,
   `UNSUPPORTED_PROTOCOL_VERSION` and `KNOWN_PROTOCOL_VERSIONS` each occur **zero** times;
   `DEFAULT_PROTOCOL_VERSION` is still live; `server/discover` is still unrouted; and the verbatim
   protocol echo survives at `bin/adr-mcp:651` as
   `protocol = requested if isinstance(requested, str) and requested else DEFAULT_PROTOCOL_VERSION`
   — which is *precisely* the expression ADR-016's `forbid_pattern` targets. This is the same class of
   defect the Code phase found in this file's other stale docstring (the LLM pass described as
   "opt-out" long after ADR-001 made it opt-in): `bin/adr-mcp` again documents behaviour it does not
   have.

   The ADR that TASK-58's AC #12 required now exists as an **untracked `Proposed`** draft, `ADR-016`,
   whose Enforcement block would `require_pattern` `MODERN_PROTOCOL_VERSIONS`,
   `UNSUPPORTED_PROTOCOL_VERSION` and `server/discover` in `bin/adr-mcp`, `forbid_import` the official
   `mcp` SDK, and `forbid_pattern` the echo expression above. Because `bin/adr-judge` reads Accepted
   ADRs only, **none of it is enforced today** — so nothing mechanical currently catches the
   docstring/implementation gap. Once ADR-016 is Accepted, three of its four rules would fail on the
   file as it stands.

2. **Latent UTF-8 corruption in the native hook host.**
   [`hooks/native/adr-hook.rs:84`](../hooks/native/adr-hook.rs) does `result.push(value as char)` on a
   `u8`, reinterpreting each raw byte as a Unicode code point — Latin-1 mojibake for any non-ASCII
   input. Reachability verified: this repository's `ADR-INDEX.json` currently has zero non-ASCII
   bytes, but `bin/adr-index` writes it with `ensure_ascii=False`, so a single em dash, curly quote or
   accented character in an ADR title or `decision_summary` triggers it. Escaped `\uXXXX` input *is*
   handled correctly, which is why the snowman-in-path protocol fixture passes (`json.dumps` defaults
   to `ensure_ascii=True`) — but real clients using JS `JSON.stringify`, and
   `hooks/hook_benchmark.py` itself, emit raw UTF-8. Latent, not currently firing.

3. **Two independent retrieval implementations for one contract, with parity tested by one
   platform-gated test.** The Python core delegates to `query_adr_context(strict_index=True)` per
   ADR-014; the Rust host hand-rolls its own `rank()` with hardcoded field weights (symbols ×95,
   components ×90, topics ×75, aliases ×70, title ×60, contract ×50, summary ×40) plus its own glob
   matcher, JSON scanner and stopword list. Parity is asserted by exactly one test,
   `tests/test_hook_protocol.py:288-350`, which is `skipif`-gated on `sys.platform != "win32" or not
   NATIVE.is_file()` — so on any non-Windows runner **nothing** verifies the two hosts agree, and even
   then the assertion is only on the *set* of ADR ids mentioned, not ordering or text. Queue freshness
   diverges outright: Python validates the payload's own `expires_at` field, Rust uses filesystem
   mtime < 24 h. Same fixture, two staleness rules.

4. **The exact five-tool set is asserted by set *equality* in two independent places.**
   `clients/installer/payload.py:335` and `bin/adr_doctor_probes.py:225-231` each require the
   advertised tools to be exactly `{adr_context, adr_judge, adr_status, adr_quality, adr_readiness}`.
   Adding or renaming any MCP tool anywhere in the repository breaks **every install** and turns the
   deep-doctor `mcp-live` check red until both literals are updated. This is the tightest coupling in
   the component.

5. **`--adr-dir` outside `--root` starts cleanly and then fails every single tool call.** `main()`
   resolves `--adr-dir` with no containment check and the stderr banner reports it happily, but
   `_call_paths` runs `adr_dir.relative_to(root)` *unconditionally* — including on the branch taken
   when the caller supplies no per-call override. Verified empirically: the banner looks normal, then
   every `tools/call` returns `isError` with "ADR directory must stay within project root". The
   containment rule is correct for untrusted per-call arguments; the defect is that a *trusted
   operator flag* is validated at call time instead of at startup.

6. **`adr_judge` exit code 1 is a success, not a failure.** A client that treats a non-empty finding
   list as a tool error will misreport clean enforcement runs. Repeated here because it is the single
   most likely integration mistake and it is invisible from the schema.

7. **The key-free property is enforced by absence, not by a rule.** `adr_judge` omits `--llm` and
   injects `ADR_KIT_NO_LLM=1`; `adr-suggest` is excluded on purpose. Neither is machine-checked —
   ADR-011's `require_pattern` only guards that the literal string `adr_readiness` stays present. A
   future edit could add an LLM path without tripping any enforcement.

8. **The native binary exists for `windows-x64` only, so edit-hook latency certification is
   structurally unreachable elsewhere.** Both halves of `run-hook.cmd` and
   `hook_benchmark.host_command` reference `bin/darwin-{x64,arm64}/adr-hook` and
   `bin/linux-{x64,arm64}/adr-hook` paths that do not exist in the repository. Combined with
   `docs/hook-performance.md` ("Python … is not eligible for the edit-hook latency certification"),
   and with the 25/50/100 ms edit budget that exists because a 3,072-byte `no_std` no-CRT Windows
   process already costs 18.1 ms p50 / 25.9 ms p95 to launch, off-Windows platforms cannot meet the
   edit-hook budget at all. No CI step compiles the `.rs` sources; the 248,832-byte `.exe` is
   committed while the 1.5 MB `.pdb` is gitignored.

9. **Copilot's hook path diverges twice, only one of which is a declared degradation.** The declared
   one: 3 of 6 lifecycle events, no `PreToolUse`, so ADR-004's edit-tier context never fires — a
   registered degradation with a `postToolUse` backstop, and ADR-004's fail-closed floor is
   unaffected because that floor is `bin/adr-judge` at pre-commit, client-independent, and ADR-004
   explicitly *rejects* a fail-closed `PreToolUse` gate. The undeclared one: Copilot's `hooks.json`
   bypasses `run-hook.cmd` entirely (verified in `_copilot_hook_config`), hardcoding `python3` on
   POSIX and re-implementing host selection inline in PowerShell — so `$ADR_KIT_PYTHON` and the
   `__ADR_KIT_PYTHON__` install-time pin are not honoured for Copilot. Nothing records this as a
   degradation. A consequence visible only at component level, where both halves sit in one document:
   the installer nevertheless substitutes `__ADR_KIT_PYTHON__` into `copilot/hooks/run-hook.cmd`
   (`_patch_mcp_python`, [`clients/installer/payload.py:151`](../clients/installer/payload.py)) and
   raises if the placeholder is absent — patching a wrapper no Copilot hook ever executes. That file
   is also absent from `REQUIRED_INSTALL_FILES`, so `validate_source` would not catch it missing; the
   failure would surface later inside `_patch_mcp_python` with a less specific error.

10. **`skills/` content is never drift-checked; only its existence is.** For the `canonical-rich`
    client the generator's sole assertion is `.is_file()`, raising `GenerationError("missing canonical
    rich skill")` otherwise. So the 759-line `skills/adr/SKILL.md` and the 6-step `adr` `procedure`
    array in `clients/workflows.json` are two independent descriptions of one workflow with no
    agreement check. They currently agree in substance. Meanwhile `codex/skills` and `copilot/skills`
    *are* byte-compared — **the generated corpora are better protected than the canonical one they
    nominally derive from**.

11. **`agents/adr-generator.md` never reaches Codex or Copilot, yet instructions copied verbatim into
    both trees tell those agents to invoke it.** Neither client tree contains an `agents/` directory;
    `agents` is not in `COPY_ROOTS`, not in the generator's expected map, and absent from
    `sync-agent-plugins.py`. Yet `instructions/adr.coding.md:22` and `instructions/adr.review.md:20`
    both name `adr-generator` as the scaffolder and ship byte-for-byte to both. Nuance: `agents` *is*
    in `packaging/public-artifacts.json` `include_roots`, so the file ships in the release payload —
    it just never lands where those clients look.

12. **The `mutates` flag has no schema and three workflows contradict their own skill.** `judge`,
    `guardian` and `review` are `mutates: false`, so their generated prompts read "This workflow is
    read-only", while their `SKILL.md` bodies declare `Edit, Write` and describe writing files (judge
    resolution path (a) drafts an ADR, review drafts Proposed records, guardian drafts retirement
    skeletons). `validate_workflows()` checks only `schema_version` and client membership, and
    `schemas/` contains no workflows schema, so the mismatch is unfalsifiable in both directions. The
    clean contrast worth reporting: of the seven `mutates: false` workflows, three declare write tools
    and four (`context`, `lint`, `related`, `retire`) genuinely declare none.

13. **Three files in `instructions/` give three different answers to "where is the canonical guide",
    and all three ship verbatim to all three clients.** `ADR-guide.md` (stamped v0.35.0) points at
    `.adr-kit/ADR-guide.md`; `adr.coding.md:31` says `.claude/adr-kit-guide.md`; `adr.review.md:3`
    says `docs/adr/README.md`. Only `ADR-guide.md` gets a provenance line; the other two are copied
    unmodified with v0.12-era pointers intact.

14. **The rich Claude corpus is ~13× the generated ones, and that asymmetry is by design.** 3,730
    lines of `skills/` against 274 for all 15 `codex/skills` files. The reasoning content — the
    anti-rationalisation guards, the gate sub-checks, migrate patterns A–H, the lint severity decision
    tree — exists only on the Claude path. ADR-010 requires equal *outcomes*, not equal instructions,
    so this is intentional; but a Codex or Copilot agent reaches the same `bin/` tools with
    substantially less guidance about when and why.

15. **Two independent `SessionStart` producers can feed one session.** The plugin hook
    (`hooks/hooks.json` → `run-hook.cmd` → `adr_hook_core`, emitting global Accepted ADRs and the
    readiness queue) and the project-scoped `.claude/settings.json` entry (→ `bin/adr-guardian check`,
    emitting the `[adr-guardian]` health nudge). They share no code; zero files under `hooks/`
    reference `adr-guardian`. The guardian entry's declared uninstall handle
    `"_remove_marker": "adr-guardian-session-start"` has **no reader** anywhere outside the generated
    mirrors.

16. **Dead code confirmed in the hook core, and copied into both mirrors.** `load_records` (:194),
    `rank` (:262) and `_matching_path_records` (:319) are unreferenced by the module and by every test
    — `evaluate` uses `_query`/`query_adr_context` exclusively. They are vestigial keyword ranking
    from before ADR-014 moved retrieval to the shared index-first engine, and they travel verbatim
    into `codex/hooks/` and `copilot/hooks/`. Relatedly, `bin/adr-watch` is **no longer the wired
    edit-tier implementation** (the shipped runtime dispatches through `hooks/hooks.json` →
    `adr_hook_core`; greps for `adr-watch` across all of `hooks/` return zero hits) even though
    `templates/adr-kit-guide.md`, `CHANGELOG.md` and ADR-004 all still describe
    `bin/adr-watch --pre-edit/--hook` as the edit tier.

17. **CRLF divergence is the root cause of open TASK-57, and it reaches this component.** The git
    index is LF for both trees, but a Windows worktree is CRLF for `hooks/**` and LF for
    `codex/hooks/**`; the generator normalizes `\r\n` → `\n` when copying, so a byte-comparison drift
    check false-positives. `.gitattributes` pins `bin/*`, `scripts/*.py`, `codex/bin/*`,
    `copilot/bin/*`, `.githooks/*`, `templates/githooks/*` and `.claude-plugin/hooks/*` — but
    `.claude-plugin/` contains no `hooks/` directory at all, so that rule targets a nonexistent path
    while `hooks/**` and `codex/hooks/**` go unpinned. Note the load-bearing consequence for the
    polyglot: the `sh` here-doc sentinel would not match a CRLF-terminated `CMDBLOCK` line, so
    LF-in-index is required for POSIX correctness. **The fix belongs in `.gitattributes`, not in the
    files** — running the generator's write mode "fixes" the check locally and hides the defect.

18. **`payload.py` sits exactly on its ADR-010 line ceiling.** ADR-010 sets support modules at "at
    most 400 physical lines", `tests/test_release_allowlist.py:70` asserts `<= 400`, and the file is
    400 lines. One added line fails the suite. It is also the only file under `clients/` named in that
    budget test; the other six installer modules are unbudgeted.

19. **`_copy_public_payload` honours only half the release allowlist.** It uses `include_roots` but
    never consults `forbidden_segments` or `forbidden_globs`; it hard-codes
    `ignore_patterns("__pycache__", "*.pyc", "*.pdb")`, covering three of the declared forbidden
    patterns. `**/*.key`, `**/*.pem`, `**/.env` and the `secrets` / `docs/plans` / `docs/reviews`
    segments are not filtered at copy time. The full allowlist is enforced in `validate_release_paths`
    — i.e. on the release-*archive* path, not the local-install path. Practical exposure is low (the
    prepared directory is per-user and local) but the two paths disagree.

20. **The desired-state model is wider than what is implemented.** `ClientResult.status` declares six
    values and `run_transaction` unconditionally returns `"updated"` on success, so `noop`,
    `installed`, `removed`, `failed` and `rolled-back` are unreachable through that path — even though
    the evidence *file* records `healthy`/`rolled-back`/`failed` correctly. `native_manager_available`
    is hardcoded `True`, `trusted` is hardcoded `None`, and every `ClientSpec.update_trigger` is the
    literal `"native-manager-deferred"`, written verbatim into every plan and every
    `updates/<client>.json`. Additionally, four settings keys declared in `capabilities.json`
    (`doctor.repair_safe`, `judgment.cloud_enabled`, `judgment.local_enabled`, `updates.mode`) appear
    **nowhere else in the repository**; the runtime schema in `scripts/adr_settings.py` uses a
    different namespace entirely, and nothing maps between the two vocabularies.

21. **Copilot is detected and version-checked by substring over stdout+stderr, not structured
    output** — because Copilot CLI emits no JSON. An unrelated line mentioning `adr-kit` would read as
    "installed". This is a real capability difference consistent with ADR-010's premise, but it is
    **not** recorded as a declared degradation in `capabilities.json`, which tracks hook-event
    degradations only.

22. **Source identity is pinned to one URL.** `validate_source` hard-fails unless
    `.claude-plugin/plugin.json`'s `repository` equals exactly
    `https://github.com/rvdbreemen/adr-kit.git`. Forks cannot install without editing the installer.
    Separately, `validate_source` re-implements the ADR-013 version-site registry in Python,
    hardcoding the same five sites that `packaging/version-sites.json` declares — ADR-013 carries no
    `path_glob` covering `clients/`, so it does not govern here, but the duplication runs against its
    stated intent.

23. **`adr_quality` fans out one subprocess per ADR file.** With `adr_id` omitted on a repository of
    *N* ADRs that is *N* Python interpreter startups inside one tool call, each sharing the 60-second
    `CLI_TIMEOUT_S`. Combined with `for line in sys.stdin` being strictly serial and
    `notifications/cancelled` being dropped, one slow tool call stalls the entire connection for up to
    a minute with no cancellation. And `tests/fixtures/cli/latency-corpus.json` contains **no
    `adr-mcp` entry**, so ADR-015's 2,000 ms ceiling does not currently bind this file — whether an
    agent-facing MCP call counts as a "deterministic user-facing path" is an open question.

24. **README documentation drift against the live `inputSchema`.** `README.md:384` documents
    `adr_readiness` as taking `changed_paths?` and `source_text?` — neither exists; the real optional
    pair is `base`+`head`. `README.md:380` lists `history?` where the actual property is
    `include_history`. An agent following the README sends arguments the server ignores. Two ADRs also
    carry stale line anchors into this file: `ADR-014:396` cites `bin/adr-mcp:295-316` and
    `ADR-004:191` cites `bin/adr-mcp:293`, but `tool_adr_context` starts at `:363` and line 293 sits
    inside `run_cli`'s `subprocess.run`.

25. **Honesty mechanisms worth preserving.** The degradation registry is credible because
    `tests/test_client_adapter_generation.py:159` requires each `exceptions.json` entry to have a
    non-empty rationale and user effect plus a fixture whose `exception_id` matches — though the three
    fixtures are three-key stubs asserting a degradation *exists and is named*, not that its backstop
    works. `hook_benchmark.measure` refuses to launder a timeout out of its percentiles.
    `tests/fixtures/hooks/windows-process-floor.json` preserves a recorded `hard_timeout: false`
    outlier rather than hiding it. `agents/adr-generator.md:151` states plainly that two of the kit's
    own gate tools disagree by design (`adr-quality`'s four gates versus `adr-lint`'s default
    completeness/audit/consistency). And `skills/grill/agents/openai.yaml` — the only non-Markdown
    file in the instruction layer — **has no known consumer**: it ships via the `skills` include_root
    but is absent from `COPY_ROOTS`, `HOOK_RUNTIME_FILES`, the generator's expected map and
    `capabilities.json`.

26. **Cost and latency figures in the instruction layer are asserted, not measured.** "~$0.10–0.30 per
    commit", "5–10 s latency", "up to 2 Sonnet calls per commit each with a 120 s timeout" appear in
    `skills/init/SKILL.md:263-267`, `skills/guardian/SKILL.md:129-132` and
    `instructions/adr.review.md:92`. Treat them as documentation claims.
