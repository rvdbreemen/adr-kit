# ADR Kit across coding-agent environments

Status: research; wider client implementation deferred to TASK-43
Date: 2026-07-19
Scope: ADR Kit packaging, lifecycle hooks, installation, updates, project
instructions, and client diagnostics

## Implementation disposition

This report intentionally preserves the broad client research. It is not the
current implementation scope.

- TASK-40 implements only Claude Code CLI, Codex CLI, and GitHub Copilot CLI.
- TASK-43 is the future expansion epic for generic portability and every other
  researched client or surface.
- No support classification or target in this report authorizes current
  implementation, installer behavior, release gating, or a public support
  claim beyond the three TASK-40 clients.
- TASK-43 must refresh all external evidence and receive explicit maintainer
  activation before using this report as an implementation input.

## Executive conclusion

ADR Kit should not become a collection of unrelated client-specific forks. It
should remain one deterministic Python core with generated client adapters.
Each adapter may use a different manifest, prompt directory, hook envelope, or
installation command, but it must expose the same user-visible workflows:

- discover relevant ADRs before work;
- invoke ADR Kit through skills and prompt or command entry points;
- inject bounded ADR context at useful lifecycle points;
- expose the same local MCP tools where the client supports MCP;
- preserve project instructions without replacing user content;
- install and update idempotently through the client's native mechanism; and
- diagnose the real installed environment, including stale caches and broken
  launchers.

The current three-client implementation is a sound base, but it does not yet
provide full parity. Claude Code receives SessionStart, PreToolUse, and
PostToolUse hooks. Codex and Copilot currently receive skills and MCP only.
Copilot's official hook contract can inject context at SessionStart and after a
tool, but its PreToolUse output can allow, deny, or modify the call rather than
inject arbitrary model-visible context. That is a genuine fidelity difference,
not something the adapter should hide.

The recommended support expansion uses a deliberately strict distinction
between **supported**, **contract-test candidate**, and **portable
compatibility**:

1. Keep Claude Code, Codex, and GitHub Copilot CLI as supported clients, while
   documenting Copilot's event-specific output limitations.
2. Add first-class adapters, in this order, for Kimi Code, Qwen Code, Cursor
   IDE/local Agent, VS Code Agent Plugins, Gemini CLI, OMP, and Pi.
3. Admit Hermes and OpenCode only after their adapters pass the executable
   install, hook, update, rollback, and doctor contract suite.
4. Add Kilo Code to the first-class target set. Keep Amp, goose, Kiro,
   Antigravity, OpenHands, MiMo Code, Letta Code, OpenHarness, and Z Code behind
   explicit contract tests until their distribution, lifecycle, or impact
   gaps are closed.
5. Do not advertise Warp, Crush, Aider, Cursor CLI, CodeBuff, Neovate,
   OpenClaude, Open Claude Cowork, claude-code-rust, Claw Code, or OpenClaudia
   as full clients. Some can consume portable skills, instructions, or MCP,
   but that is compatibility, not plugin parity.

For ADR Kit, lifecycle automation should stay deliberately narrow:

- SessionStart provides a bounded ADR overview and staleness signal;
- UserPromptSubmit provides task-relevant ADR context where supported;
- PreToolUse injects the governing Accepted ADR before an edit;
- PostToolUse is the deterministic confirmation backstop; and
- Stop and SessionEnd perform no required ADR mutation.

No hook should rewrite an ADR or spend money on an LLM. Decision creation,
acceptance, supersession, and retirement remain explicit workflows.

## Research method and admission rule

This report prioritizes official product documentation and primary
repositories. The Codex Marketplace documentation supplied with the request is
useful ecosystem material, but it is third-party and is not treated as the
normative Codex contract. Likewise, a README claim was not enough to admit a
client when no installable plugin format or lifecycle contract could be found.

A client qualifies for first-class ADR Kit support only when an automated
installer and doctor can verify all of the following, natively or through a
small supported adapter:

1. reusable skills following the local `SKILL.md` Agent Skills convention;
2. user-invocable prompts, commands, or user-invocable skills;
3. persistent project guidance (`AGENTS.md`, a client-specific context file, or
   plugin rules);
4. a session-start equivalent that can make context visible to the model;
5. before-edit and after-edit lifecycle interception;
6. MCP tools or an equally capable in-process tool bridge;
7. a versioned install, update, disable, and uninstall lifecycle;
8. a way for `adr-kit doctor` to inspect loaded skills, hooks, tools, and
   version state; and
9. reliable propagation of project instructions and ADR context into supported
   agent/subagent execution modes; and
10. Windows, macOS, and Linux behavior that can be tested or explicitly
   scoped.

For community and open-source clients, first-class support additionally
requires at least **2,000 GitHub stars**, a release or substantive commit in the
last six months, and a maintainable upstream security/update story. The
2,000-star threshold is a sensible default: it limits a small project to
clients with enough adoption to justify a permanent adapter, without turning
popularity into a technical proxy. Stars never compensate for a missing hook
or plugin contract. Closed-source clients are exempt from the star measurement
only when they have material ecosystem impact and an official, versioned
plugin and lifecycle contract. Every admitted client still has to pass the
same executable capability suite.

These rules intentionally exclude technically interesting but immature
clients. Portable compatibility may still install ADR Kit's `SKILL.md`,
`AGENTS.md` block, or MCP server, but it must be opt-in and described as
partial. It must never appear as successful full-plugin installation.

## Standards and instruction files

### AGENTS.md, not AGENT.MD

[agents.md](https://agents.md/) defines the portable project instruction file
as `AGENTS.md`, plural. The associated
[agents.md repository](https://github.com/agentsmd/agents.md) describes nested
files and closest-scope precedence. ADR Kit should use `AGENTS.md` as its
portable target.

Some clients, notably Amp, still read the older singular `AGENT.md`. The
installer should not create that competing file by default. If a repository
already has `AGENT.md`, doctor should report it and setup may append the same
managed block only after confirming that the client actually reads it. A
Windows-hostile symlink strategy should not be the default.

### Agent Skills versus skills.md

The portable artifact is a local skill directory containing `SKILL.md`, as
described by the [Agent Skills specification](https://agentskills.io/). The
site [skills.md](https://skills.md/docs) is a hosted discovery and execution
platform, not the neutral on-disk specification. ADR Kit may be listed there,
but it must not require that service. Local, offline, reviewable skills remain
the source of truth.

### Non-clobbering project guidance

Project setup should install one canonical guide:

`/.adr-kit/ADR-guide.md`

Client-visible files should contain only a short managed block that points to
that guide and the generated ADR indexes. Targets are:

- `AGENTS.md` for Codex, Cursor, Amp, Pi, OMP, OpenCode, and other compatible
  clients;
- `CLAUDE.md` for Claude Code and Claude-compatible wrappers;
- `.github/copilot-instructions.md` for GitHub Copilot surfaces;
- `GEMINI.md` for Gemini CLI when extension context alone is insufficient;
- `QWEN.md` for Qwen Code when extension context alone is insufficient; and
- client-native rules only where a plugin cannot rely on one of the files
  above.

Every managed block must have stable begin and end markers. Setup must:

1. read the file before writing;
2. create it if absent;
3. append only when no block exists;
4. replace only the bytes between its own markers;
5. preserve encoding, newline style, BOM, and unrelated content;
6. stop on duplicate, nested, or malformed markers;
7. offer `--dry-run` with a unified diff; and
8. make a timestamped backup before a non-trivial migration.

This replaces the current Claude-specific guide location over a compatibility
period. Existing `.claude/adr-kit-guide.md` files remain valid and are migrated
only by the explicit upgrade workflow.

## Current ADR Kit baseline

The repository currently ships:

- a Claude plugin rooted at `.claude-plugin/plugin.json`;
- a Codex plugin under `codex/`;
- a Copilot CLI plugin under `copilot/`;
- a Python-only MCP and deterministic ADR engine;
- a detector/installer limited to `claude`, `codex`, and `copilot`;
- copied Codex and Copilot payloads generated from canonical root files; and
- project setup centered on `CLAUDE.md` plus
  `.claude/adr-kit-guide.md`.

Relevant accepted decisions are:

- [ADR-001](../adr/ADR-001-llm-gates-opt-in.md): cost-bearing LLM gates remain
  opt-in.
- [ADR-002](../adr/ADR-002-adr-guardian-session-start-staleness-detector.md):
  SessionStart is a dumb, fail-open detector with no daemon.
- [ADR-004](../adr/ADR-004-layered-adr-context-injection.md): session, task, and
  edit tiers are bounded; PreToolUse is the ideal edit tier and PostToolUse is
  a backstop.
- [ADR-006](../adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md):
  installs use validated, versioned, platform-local prepared sources and native
  client APIs.
- [ADR-008](../adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md):
  engine roots are version-ranked so stale installed caches do not silently win.

During this research the installed Codex ADR Kit MCP launcher from the `0.35.0`
cache still referenced a removed `0.34.0` path. Running the checkout's
`bin/adr-context` worked. This is exactly the class of stale-cache defect that
the cross-client doctor and atomic update design must detect.

## ADR Kit lifecycle architecture

### Normalized, bounded hook execution

ADR Kit should normalize the client events it actually uses into a small
internal envelope:

```text
client, client_version, event, session_id, agent_id,
cwd/workspace, timestamp, tool_name, tool_arguments
```

Client adapters translate native event names, JSON shapes, tool aliases, and
paths into this envelope. The deterministic core then selects one bounded
operation:

```text
SessionStart     -> ADR index summary and cheap staleness signal
UserPromptSubmit -> task-relevant ADR references
PreToolUse       -> governing Accepted ADR before an edit
PostToolUse      -> confirmation backstop and dirty-state signal
other events     -> successful no-op unless an ADR feature explicitly needs one
```

Hooks remain read-only toward ADR documents. Any operation that creates or
changes an ADR stays behind an explicit skill, command, or MCP tool.

Recommended ADR Kit hook targets are p95 below 150 ms for SessionStart and
below 50 ms for edit hooks, with hard timeouts of 500 ms and 100 ms
respectively. Timeout, malformed input, missing Python, or a broken index must
fail open; the deterministic pre-commit gate remains the enforcement floor.

### Recommended latency budgets

These are ADR Kit design targets, not vendor guarantees:

| Path | p50 target | p95 target | Hard timeout | On timeout |
|---|---:|---:|---:|---|
| SessionStart | 50 ms | 150 ms | 500 ms | inject the cached minimum or nothing |
| UserPromptSubmit ADR ranking | 75 ms | 250 ms | 500 ms | keyword-ranked ADR references only |
| SubagentStart ADR propagation | 30 ms | 100 ms | 250 ms | project instructions only |
| PreToolUse / PostToolUse edit signal | 25 ms | 50 ms | 100 ms | fail open; rely on pre-commit |
| PreCompact ADR reminder | 30 ms | 100 ms | 500 ms | no-op |
| Stop / SubagentStop cleanup | 50 ms | 200 ms | 750 ms | no-op |
| SessionEnd cleanup | 100 ms | 500 ms | 1 s | no-op |

The timed work must remain deterministic and local. Generated indexes, bounded
decision summaries, and cached configuration are suitable hook inputs.
Network access, LLM calls, index rebuilding, native plugin updates, and ADR
lifecycle mutations are not.

### Cross-client lifecycle coverage

This table is intentionally about lifecycle semantics, not merely whether a
client can run an arbitrary script. `A` means an extension API can implement a
close analogue; `D` means a documented degradation; `N` means the official
surface reviewed here does not expose the event.

| Client | Start | Prompt | Pre/Post tool | Subagent start/stop | Pre-compact | Turn stop | Session end |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Code | Y | Y | Y | Y | Y | Y | Y |
| Codex | Y | Y | Y | Y | Y | Y | N |
| Copilot CLI | Y | Y | Y | Y | Y | Y | Y |
| Cursor local | Y | Y | Y | Y | Y | Y | Y |
| VS Code Agent Plugins | Y | Y | Y | Y | Y | Y | D |
| Qwen Code | Y | Y | Y | Y | Y | Y | Y |
| Gemini CLI | Y | Y | Y | Y | Y | Y | Y |
| Kimi Code | Y | Y | Y | Y | Y | Y | Y |
| Hermes | Y | A pre-model | Y | Y | ? context engine | Y | Y |
| Amp | Y | A | Y | A | ? | Y | A |
| goose | Y | Y | Y | N | N | Y | Y |
| OMP | Y | A | Y | A | Y | Y | A |
| Pi | Y | A | Y | D, extension-owned | Y | Y | A |
| OpenCode | A `session.created` | A message event | Y | D task-tool only | A experimental | A idle/status | A |
| Kilo Code | A plugin load/session event | Y `chat.message` | Y | A event/task tool | A experimental | A `session.idle` | A |
| Antigravity | D PreInvocation | D PreInvocation | Y | N | N | Y | N |
| Warp | N | N | N | N | N | N | N |
| Kiro CLI | A AgentSpawn | Y | Y | N | N | Y | N |
| Crush | N | N | D pre only | N | N | N | N |
| OpenClaudia | Y | Y | Y | N as hook | N | Y | Y |
| OpenHarness | ? | ? | Y | ? | ? | ? | ? |

Question marks are admission blockers, not invitations to assume behavior.
They become `Y`, `D`, or `N` only after a native fixture and model-visible
smoke test.

### Hook-by-hook evaluation

#### SessionStart: bounded repository orientation

Use it for:

- locating and validating the ADR index;
- injecting a compact map of Accepted and Proposed decisions;
- running the cheap, fail-open Guardian staleness check from ADR-002; and
- pointing the agent to `ADR-guide.md` and the task-specific context command.

Do not rebuild indexes, run the LLM audit tier, modify ADRs, or install project
artifacts. A new session often has no useful task prompt yet.

ADR Kit value: **5/5**.

#### UserPromptSubmit / beforeSubmitPrompt: task-tier ADR context

This is the best place to run ADR Kit's deterministic context ranking because
the task text is available. Inject only a bounded set of relevant ADR
references and decision summaries. Skip trivial prompts, avoid model calls,
and never create a decision automatically.

ADR Kit value: **5/5 when available**.

#### SubagentStart: propagate governing decisions

Subagents may not inherit all parent context. Where the client exposes this
event, inject:

- the repository ADR operating contract;
- the small set of decisions already selected for the parent task; and
- the relevant source paths or ADR identifiers.

If the client has no SubagentStart event, project instructions and explicit
skill invocation are the fallback. This is useful parity, but not required for
the core edit gate when subagents already inherit project guidance.

ADR Kit value: **3/5**.

#### PreCompact and PostCompact: normally no-op

ADR Kit has no session knowledge that must be archived before compaction. A
PreCompact hook may inject a short reminder to re-read the generated ADR index
after compaction, but project instructions and on-demand skills are the more
portable mechanism.

ADR Kit value: **1/5**.

#### Stop, SubagentStop, and SessionEnd: no ADR mutation

ADR Kit should not create, accept, supersede, retire, or rewrite decisions at
an agent boundary. Stop hooks can fire repeatedly and some clients allow them
to force continuation, so using them for governance would be brittle.

At most, these events may clear an owned temporary cache or emit anonymous
local timing counters when diagnostics are explicitly enabled. The default
adapter should be a successful no-op.

ADR Kit value: **1/5**.

#### PreToolUse: primary edit-tier enforcement

PreToolUse is ADR Kit's ideal edit-tier enforcement point because the target
file is known. Limit it to edit/write tools and inject:

- the top-ranked governing Accepted ADR;
- the bounded `## Decision` text; and
- a direct ADR path for verification.

ADR Kit value: **5/5**.

#### PostToolUse and PostToolUseFailure: evidence and dirty signals

Use successful edit events to confirm which governing ADR applies and mark the
project state dirty for a later deterministic check. Failure events should
normally no-op. Filter by tool name and never process unrelated searches or
shell output.

ADR Kit value: **4/5 as a backstop**.

#### Error hooks

Errors in optional ADR Kit hooks must fail open and become doctor diagnostics.
They must not deny a client tool call accidentally.

ADR Kit value: **2/5**.

#### PermissionRequest and notification hooks

ADR Kit should not make permission decisions. Notifications are not a portable
governance boundary and require no default handler.

ADR Kit value: **1/5**.

#### Interrupt, StopFailure, retry, and model-call hooks

Interrupt, StopFailure, retry, and model-call events do not correspond to an
ADR Kit state transition. No default handler is required.

ADR Kit value: **1/5**.

#### Task, agent, worktree, configuration, and file hooks

Worktree and workspace events can select the correct repository root and ADR
index. Configuration events can invalidate an owned index cache after ADR Kit
settings or plugin versions change. Generic file and shell events are too
noisy; edit-tier tool hooks are more precise.

ADR Kit value: **3/5 for repository routing**.

## Official hook contracts for the major clients

### Codex

The official [Codex hooks documentation](https://learn.chatgpt.com/docs/hooks)
documents PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact,
SessionStart, UserPromptSubmit, SubagentStart, SubagentStop, and Stop. Plugins
may bundle hooks, but changed hook definitions require trust review. That
explains an installed-but-inactive hook table whose entries are marked for
review.

Important adapter details:

- hook output can inject additional context at SessionStart, SubagentStart,
  UserPromptSubmit, PreToolUse, and PostToolUse;
- SubagentStop and Stop can force continuation, which ADR Kit should not use
  for housekeeping;
- multiple matching hooks may run concurrently;
- the `async` field is parsed but asynchronous hooks are currently skipped;
- the default timeout is far too large for ADR Kit and must be overridden; and
- hosted tools such as hosted web search are outside the local tool hook set.

Codex is a **first-class target**. ADR Kit should add plugin hooks to its current
skills and MCP payload and include trust state in doctor.

### Claude Code

The official [Claude hooks documentation](https://code.claude.com/docs/en/hooks)
has the broadest event surface in this comparison, including SessionStart,
UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, SubagentStart,
SubagentStop, PreCompact, PostCompact, Stop, SessionEnd, errors, tasks, config,
worktrees, and other lifecycle events. The
[Claude plugin documentation](https://code.claude.com/docs/en/plugins) packages
skills, commands, agents, hooks, MCP, LSP, and monitors.

Claude is a **first-class target** and the current reference implementation.
ADR Kit should keep its bounded SessionStart, prompt, and edit hook set; other
lifecycle events remain successful no-ops unless a future ADR Kit feature
explicitly needs them.

### GitHub Copilot CLI and cloud agent

The [Copilot hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)
documents SessionStart, SessionEnd, UserPromptSubmitted, PreToolUse,
PostToolUse, PostToolUseFailure, agentStop, SubagentStart, SubagentStop,
PreCompact, errors, permission, and notification events. Plugins can bundle
hooks, skills, agents, commands, and MCP through the
[Copilot plugin workflow](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating).

Notable differences:

- command PreToolUse hooks fail closed on crashes and non-zero exits, while a
  timeout fails open;
- PreToolUse may allow, deny, or modify arguments, but does not advertise an
  arbitrary `additionalContext` output;
- PostToolUse and SessionStart can inject context;
- PascalCase events use the cross-compatible snake_case envelope;
- cloud jobs have an ephemeral filesystem and constrained network; and
- prompt hooks are interactive-session-only and are unreliable for cloud jobs.

Copilot remains a **supported first-class client with one documented
degradation**: proactive edit context must be loaded at session/task scope, or
confirmed after the edit. Do not manufacture parity by denying and retrying
every edit.

### Cursor

The [Cursor plugin reference](https://cursor.com/docs/reference/plugins) can
bundle skills, agents, commands, rules, MCP, and hooks. The
[Cursor hooks documentation](https://cursor.com/docs/hooks) includes
sessionStart/sessionEnd, beforeSubmitPrompt, PreToolUse/PostToolUse,
SubagentStart/SubagentStop, preCompact, Stop, shell, MCP, read, edit, and
workspace events.

Cursor local Agent is a **first-class target**. Cursor cloud is not: its
documentation says several start/end and MCP/workspace events are unavailable
or deferred. The product name in support output must therefore be `cursor-local`,
not an unqualified `cursor`.

### Antigravity

The [Antigravity plugin documentation](https://antigravity.google/docs/plugins)
bundles skills, rules, MCP configuration, and hooks. Its
[hook surface](https://antigravity.google/docs/hooks) is materially smaller:
PreToolUse, PostToolUse, PreInvocation, PostInvocation, and Stop. It does not
document native SessionStart, SessionEnd, SubagentStart/SubagentStop, or
compaction events.

Antigravity is a **contract-test candidate**. PreInvocation can supply the
bounded session-level ADR map and the native pre/post tool events cover edit
enforcement. Promote it only after its official install/update behavior,
model-visible context, instruction propagation, and doctor probes pass the ADR
Kit certification suite.

### OpenCode

[OpenCode plugins](https://opencode.ai/docs/plugins/) are JavaScript or
TypeScript modules with session, message, tool, command, file, installation,
and TUI events. OpenCode also has project commands, skills, agents, rules, and
MCP configuration, but these are not one declarative plugin bundle. Compaction
has a session event and an experimental pre-compaction hook. There is no
dedicated subagent lifecycle contract.

OpenCode is an **adapter candidate**. Full behavior is possible through a
composite installer, but it introduces a Bun/JavaScript adapter into a
deliberately Python/stdlib-first project. That architectural trade-off needs an
ADR and a passing cross-platform prototype before support is advertised.

### Kilo Code

[Kilo Code](https://github.com/kilo-org/kilocode) now has a documented plugin
contract for both its CLI and VS Code extension. Plugins are TypeScript or
JavaScript modules loaded from project/global directories or versioned npm
specifiers. They can observe the event bus, intercept and mutate pre/post tool
calls, handle new chat messages and commands, register tools, change the
compaction context, and receive installation and session events. Kilo also
supports:

- portable Agent Skills under `.kilo/skills` and `.agents/skills`;
- Markdown slash workflows under `.kilo/commands`;
- `AGENTS.md` plus project/global instruction files;
- MCP at project or user scope;
- custom agents and subagents;
- `kilo plugin`, `kilo upgrade`, `kilo uninstall`, `/reload`, and debug tools;
- CLI, VS Code, JetBrains, Windows, macOS, and Linux surfaces.

The repository had roughly 26,400 stars and a current July 2026 release during
this review, comfortably passing the adoption and maintenance gate. The plugin
API is explicitly documented as behavior-compatible with OpenCode, which
creates a useful shared adapter family while still requiring Kilo-native
fixtures.

Verdict: **first-class, high-priority target after native certification**.
Generate a thin Kilo/OpenCode TypeScript bridge from common source, but keep
client-specific manifests, paths, update probes, and smoke tests. Doctor must
verify the plugin is not suppressed by `KILO_PURE=1`, the skill and command are
discoverable, MCP starts, edit hooks fire in both CLI and VS Code, and the
installed version matches the canonical ADR Kit payload.

## Broader coding-agent landscape

### VS Code Agent Plugins

The new [VS Code Agent Plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
format is a strong match. One plugin bundles slash commands, Agent Skills,
agents, hooks, and MCP. It understands Claude and OpenPlugin layouts and shares
format concepts with Copilot CLI. The
[VS Code hook contract](https://code.visualstudio.com/docs/agent-customization/hooks)
includes model-visible JSON output.

Verdict: **first-class, high priority**, but label it preview until Microsoft
removes that status. Reuse the Copilot/OpenPlugin adapter where possible rather
than creating another copied engine.

### Qwen Code

[Qwen Code](https://github.com/QwenLM/qwen-code) and its
[extension documentation](https://qwenlm.github.io/qwen-code-docs/en/users/extension/introduction/)
bundle MCP, commands, skills, subagents, and extension context, and can import
Gemini and Claude plugin ecosystems. Its
[hooks](https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/)
cover SessionStart/End, UserPromptSubmit, Pre/Post tool, failures, Stop,
SubagentStart/Stop, PreCompact, and notifications, with command, HTTP, prompt,
and background execution options.

Verdict: **first-class, high priority**. It is one of the closest non-Claude
contracts and supports Windows explicitly.

### Gemini CLI

The [Gemini CLI extension reference](https://geminicli.com/docs/extensions/reference/)
bundles MCP, commands, hooks, Agent Skills, subagents, and `GEMINI.md`. Its
installer has an explicit `--auto-update` option. The same documentation warns
that some Gemini CLI users will migrate to Antigravity CLI.

Verdict: **first-class transition adapter**. Generate it from the same adapter
family as Qwen, keep it tested while installed clients exist, and avoid
Gemini-only core behavior.

### Kimi Code

[Kimi Code's plugin manager](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)
installs local directories, archives, GitHub repositories, and marketplace
packages. A plugin can bundle skills, slash commands, MCP servers, hook
configuration, and session-start instructions; it can be enabled, disabled,
updated, and removed through the native manager.

Its [hook contract](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/hooks.html)
is one of the broadest lifecycle contracts reviewed. It includes
SessionStart/End, UserPromptSubmit, Pre/PostToolUse and failure events,
PermissionRequest/Result, Stop/StopFailure, Interrupt,
SubagentStart/SubagentStop, and PreCompact/PostCompact. Hook errors fail open.
Kimi also reads project and global `AGENTS.md`, runs isolated subagents, and
stores local JSONL session data. The current
[Kimi CLI repository](https://github.com/MoonshotAI/kimi-cli) comfortably
passes the adoption and activity gates, while documenting its transition to
the Kimi Code CLI product.

Verdict: **first-class, highest-priority new adapter**. Its plugin is largely a
packaging and JSON-envelope translation problem rather than a behavioral
emulation. Installation must detect and safely migrate the legacy Kimi CLI
layout instead of creating parallel copies.

### Hermes Agent

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is an actively
maintained, native-Windows, open-source agent with a large user base. Its
[plugin system](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
can bundle tools, hooks, slash commands, CLI commands, injected messages, and
skills, with native install, update, enable, disable, remove, update, and
doctor flows. Its lifecycle includes pre/post tool and model calls, session
start/end/finalize/reset, and subagent start/stop. Shell hooks use structured
JSON, and session finalization covers normal exit, reset, errors, and
best-effort `atexit`/Ctrl+C paths.

The remaining work is executable packaging proof: installation, updates,
cross-platform shell-hook behavior, instruction/skill discovery, and doctor
visibility must all be verified against a real client.

Verdict: **first-class contract-test candidate**. Promote it only after the
native plugin manager and hook bridge pass the complete ADR Kit certification
suite.

### Pi

[Pi](https://pi.dev/) supports packages distributed through npm or git that
bundle TypeScript extensions, Agent Skills, prompt templates, and themes. It
loads `AGENTS.md`, exposes prompt templates and skills as commands, stores full
JSONL session trees, and lets extensions intercept tool, turn, session, and
compaction behavior. Pi intentionally does not ship built-in subagents or MCP,
but extensions can add both.

Verdict: **first-class adapter after prototype**. The adapter is a Pi package
containing a thin TypeScript bridge plus the canonical ADR Kit skills and
prompts. The doctor must verify package load and the bridge-to-Python MCP/tool
handshake.

### OMP / Oh My Pi

The [OMP repository](https://github.com/can1357/oh-my-pi) is a Pi-derived
harness with native discovery for skills, commands, MCP, extensions, plugins,
and subagents. Its primary
[skills documentation](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md)
shows compatibility providers for `.agents`, Claude, Codex, OpenCode, and
GitHub skill layouts. Its hook API includes session start, agent/turn, tool,
retry, and pre/post compaction events.

Verdict: **first-class, high priority**. Prefer an OMP plugin/package rather
than relying on incidental discovery of the Codex or Claude payload.

### Amp

The [Amp manual](https://ampcode.com/manual) documents `AGENTS.md`, local Agent
Skills, MCP, project/system TypeScript plugins, commands, custom agents, and
session/tool/agent lifecycle events. Plugins reload without reinstalling and
apply in interactive and execute modes.

Verdict: **contract/impact-test candidate**. A prototype can package the skill
and MCP with a small `.amp/plugins/adr-kit.ts` event bridge. Before promotion,
it must prove reliable project/system plugin discovery and a trustworthy
idempotent update path;
because Amp plugins are currently files rather than a marketplace bundle, the
ADR Kit installer would own versioning and updates.

### goose

[goose](https://goose-docs.ai/) is a native open-source agent with CLI,
desktop, and API surfaces. It supports Agent Skills, persistent instructions,
custom slash commands, prompts, MCP extensions, subagents, recipes, and an
Open Plugins-compatible package layout. Its
[hook documentation](https://goose-docs.ai/docs/guides/context-engineering/hooks/)
defines `plugin.json` plus `hooks/hooks.json`, `${PLUGIN_ROOT}`, and
SessionStart, SessionEnd, Stop, UserPromptSubmit, Pre/Post tool, failures, file,
and shell events. Hook failures are fail-open.

goose does not currently emit SubagentStart/SubagentStop or PreCompact, but
those events are not required by ADR Kit's current bounded lifecycle. Its
SessionStart, prompt, pre/post-tool, Stop, and SessionEnd events cover ADR
orientation and edit-tier enforcement.

Verdict: **contract-test candidate**. Its Open Plugins layout can share
canonical source with the VS Code/OpenPlugin family, but it must pass native
instruction propagation, edit-hook, install/update, and doctor tests before
promotion.

### Letta Code

Letta the platform is broader than a coding client, but
[Letta Code](https://github.com/letta-ai/letta-code) is a distinct coding
harness for CLI, desktop, browser, and messaging surfaces. It documents project
Agent Skills under `.agents/skills`, user commands, subagents, custom scripts
at agent lifecycle points, permissions, schedules, and a native doctor.

Verdict: **contract-test candidate**. The public feature set is strong, but this
research did not find a stable distributable plugin manifest that bundles
skills, prompts, hooks, and MCP with a native update lifecycle. A first adapter
may therefore be a composite installer, subject to the same rule as OpenCode.

### OpenHands

The [OpenHands plugin guide](https://docs.openhands.dev/sdk/guides/plugins)
defines a Claude-compatible plugin bundle with skills, hooks, MCP, agents, and
commands, plus install/list/enable/disable/uninstall lifecycle in the SDK.

Verdict: **contract-test candidate**. The plugin model is excellent, but the
research evidence is SDK-centric. Promote it only after proving the normal
OpenHands CLI or UI can install and run the plugin without an application
author manually wiring the SDK.

### OpenClaudia

The primary [OpenClaudia repository](https://github.com/dollspace-gay/OpenClaudia/)
documents skills, commands, MCP, project hooks for session start/end,
prompt submission, pre/post tool use, and Stop, plus a plugin directory. It
does not document `AGENTS.md`, a stable marketplace/update contract, or
subagent/compaction hooks as plugin lifecycle events.

Verdict: **watchlist/prototype**. The feature claims are promising, but the
distribution and compatibility contract is not mature enough for an
idempotent supported installer.

### OpenHarness

[HKUDS OpenHarness](https://github.com/HKUDS/OpenHarness) is an open-source
Python harness with separate subsystems for skills, plugins, commands, hooks,
agents, MCP, tasks, and multi-agent coordination. Its published
architecture describes plugin contributions for commands, hooks, agents, and
MCP, with PreToolUse and PostToolUse lifecycle events.

Verdict: **contract-test candidate**. The component model can host ADR Kit, but
the evidence reviewed here does not yet establish a versioned end-user plugin
install/update/disable lifecycle or SessionStart injection. Support should
target the `oh` coding client, not the underlying Python library in isolation.

### Oh My OpenAgent

[Oh My OpenAgent](https://omo.dev/docs) is an extensive agent orchestration
plugin and installer for OpenCode and Codex rather than a new independent
coding runtime. It demonstrates production techniques directly relevant to ADR
Kit: managed hook trust hashes, versioned Codex plugin caches, timestamped
configuration backups, idempotent uninstall, OpenCode event hooks, commands,
skills, MCP, AGENTS.md injection, auto-update checks, and a doctor.

Verdict: **reference implementation, no separate client adapter**. ADR Kit
should test coexistence with OMO and learn from its installer/doctor behavior.
It must not write OMO-owned configuration or assume OMO is present. Support
continues through the Codex and OpenCode adapters.

### OpenSkills

[OpenSkills](https://openskills.cc/) is a marketplace/catalog for portable
`SKILL.md` packages. It is not a coding harness and has no session, tool,
subagent, compaction, or update hook lifecycle of its own.

Verdict: **distribution channel, not a client**. ADR Kit may publish its
canonical skills there after supply-chain and namespace review. Installation
through OpenSkills cannot replace the native ADR Kit plugin because it would
omit hooks, MCP, commands, doctor, and managed project guidance.

### OpenClaude by Gitlawb

[OpenClaude](https://openclaude.gitlawb.com/) is an active terminal coding
agent with tools, agents, MCP, skills, and slash commands. Its public
documentation and repository do not currently expose an independent plugin or
hook contract.

Verdict: **not supported yet**. Skills/MCP portability alone is insufficient
for full ADR Kit automation.

### openclaudia.com

[openclaudia.com](https://openclaudia.com/) describes a Rust inference server
with WASM middleware plugins. It is not the same project as the OpenClaudia
coding harness and does not expose Agent Skills, `AGENTS.md`, coding-agent
prompts, or coding lifecycle hooks.

Verdict: **out of scope**.

### Open Claude Cowork

[Open Claude Cowork](https://openclaudecowork.com/) is a desktop shell that
reuses Claude settings and provides session and permission UI. It does not
publish its own skills, prompts, hooks, MCP, and plugin contract.

Verdict: **not a separate client**. If it faithfully runs Claude Code plugins,
the Claude adapter may work transitively, but doctor must report it as a Claude
surface rather than a new environment.

### claude-code-rust

[claude-code-rust](https://github.com/srothgan/claude-code-rust) is a native TUI
over the Claude Agent SDK and still requires Claude Code for unsupported
features. It does not document an independent plugin, hooks, skills, or project
instruction contract.

Verdict: **not a separate client**. Test whether the Claude plugin is honored;
do not maintain a duplicate adapter.

### Claw Code

[Claw Code](https://claw-code.codes/architecture) documents skills, subagents,
MCP, slash commands, `CLAUDE.md`, sessions, and compaction. Its published
architecture does not document a distributable plugin system or user-defined
lifecycle hook contract.

Verdict: **watchlist, not supported**.

### Warp

[Warp's open-source repository](https://github.com/warpdotdev/Warp) passes the
adoption gate by a wide margin. Warp supports
[Agent Skills](https://docs.warp.dev/agent-platform/capabilities/skills),
`AGENTS.md`-style
[rules](https://docs.warp.dev/agent-platform/capabilities/rules),
[slash commands](https://docs.warp.dev/agent-platform/capabilities/slash-commands),
and [MCP](https://docs.warp.dev/agent-platform/capabilities/mcp). Those are
useful portable integration surfaces.

The official material reviewed here does not publish an end-user plugin
manifest or lifecycle hook contract for session start, prompt submission,
tool use, subagents, compaction, Stop, and hard-exit recovery. MCP is described
as plugin-like, but an MCP server cannot observe the entire native lifecycle.
The long-running repository discussion requesting general extension support
reinforces that this is not a documented public plugin API.

Verdict: **compatibility only** despite its popularity. ADR Kit may expose
skills, a managed `AGENTS.md` block, slash prompts, and MCP to Warp, but Warp
fails the full-plugin admission gate and must not be auto-installed as a
supported environment.

### Cursor CLI versus Cursor IDE

Cursor's IDE/local-agent plugin and hook contract is broad enough for a
first-class adapter. The separate
[Cursor CLI documentation](https://docs.cursor.com/en/cli/using) documents
rules, `AGENTS.md`/`CLAUDE.md`, MCP, sessions, and `/compress`, but this
research found no official CLI lifecycle-hook or plugin-parity guarantee.

Verdict: **support Cursor IDE/local Agent; compatibility only for Cursor CLI**.
Doctor must detect these as distinct surfaces and must not infer CLI hook
support from the IDE documentation.

### Kiro CLI

[Kiro CLI hooks](https://kiro.dev/docs/cli/hooks/) cover AgentSpawn,
UserPromptSubmit, Pre/PostToolUse, and Stop. Kiro also has steering, skills,
custom agents, MCP, a cross-platform installer, background updates, and a
native doctor. Its public repository passes the adoption threshold.

Its documented events cover ADR Kit's current start, task, edit, and Stop
needs. The remaining question is whether Kiro Powers and CLI hook files form a
stable, versioned, independently installable payload with inspectable update
state.

Verdict: **contract-test candidate**. Promote it when that packaging and doctor
contract passes on the supported operating systems.

### Crush

[Crush](https://github.com/charmbracelet/crush) passes the adoption gate and
supports Agent Skills, skill commands, `AGENTS.md`, and MCP. Its official hook
guide explicitly describes hooks as preliminary and currently exposes only
top-level `PreToolUse`; subagent tool calls are not intercepted.

Verdict: **excluded from full support**. One preliminary pre-tool event cannot
provide session orientation, task-tier context, or ADR Kit's post-edit
backstop.

### Z Code

[Z Code's beta plugin system](https://zcode.z.ai/en/docs/plugin) bundles
skills, commands, agents, MCP, hooks, and LSP. It supports marketplace, GitHub,
git, archive, and local sources, reports versions, automatically refreshes the
runtime, and can enable, disable, update, and uninstall plugins. It also reads
workspace/global `AGENTS.md`, supports isolated subagents, local `SKILL.md`
packages, and Markdown slash commands.

The public documentation reviewed here names hooks but does not publish a
complete event/schema contract. Its adoption and material-impact evidence also
does not yet justify the closed-source exemption.

Verdict: **contract-test watchlist**. Do not add an adapter until Z Code
publishes enough hook detail to test every required lifecycle event and passes
the impact gate.

### MiMo Code

[MiMo Code](https://github.com/XiaomiMiMo/MiMo-Code) is an active OpenCode fork
that passes the adoption threshold. It advertises plugins, MCP, skills,
workflows/slash commands, subagents, and Windows installation.

The public product material reviewed here does not establish an independent
versioned plugin manifest, doctor/update lifecycle, or a complete stable hook
contract. Its built-in context features must not bypass ADR Kit's
deterministic indexes or explicit ADR lifecycle.

Verdict: **contract-test candidate**, not a supported OpenCode alias. It must
pass the full native suite before promotion.

### Aider, CodeBuff, Groq Code CLI, and Neovate

- [Aider](https://github.com/Aider-AI/aider) has enormous adoption and strong
  git/repository conventions, but no end-user plugin bundle with the required
  lifecycle hooks.
- [CodeBuff](https://github.com/CodebuffAI/codebuff) offers custom agents, an
  SDK, knowledge files, and built-in commands, but no complete installable
  plugin/hook contract was found.
- [Groq Code CLI](https://github.com/build-with-groq/groq-code-cli) is
  extensible by changing and registering source-level tools and commands, not
  by installing a versioned user plugin with lifecycle hooks.
- [Neovate Code](https://github.com/neovateai/neovate-code) falls below the
  2,000-star threshold and did not expose the full required contract in its
  public documentation.

Verdict: **not first-class clients**. High adoption does not rescue missing
capabilities, and source modification is not an acceptable installer.

### Discovery-list screening

The [awesome-code-agents](https://github.com/sorrycc/awesome-code-agents) and
[awesome-cli-coding-agents](https://github.com/bradagi/awesome-cli-coding-agents)
lists are useful discovery inventories, not evidence of compatibility. Every
candidate at or above the 2,000-star gate was classified before planning:

| Class | Environments | Result |
|---|---|---|
| Full-contract targets | Claude Code, Codex, Copilot CLI, Cursor IDE/local, VS Code Agent Plugins, Qwen Code, Gemini CLI, Kimi Code, Kilo Code, OMP, Pi | build and certify |
| Strong contract-test candidates | Hermes, OpenCode, Amp, goose, Kiro, Antigravity, OpenHands, MiMo Code | prototype; never advertise before native tests |
| Missing lifecycle surface | Warp, Aider, Crush, Cline, Roo Code, Continue, Windsurf, CodeBuff, Groq Code CLI, Plandex, ForgeCode, Mistral Vibe, gptme | compatibility or exclude |
| Framework/task runner, not an installable coding client | SWE-agent, Open Interpreter, Deep Agents Code, OpenHands SDK-only uses, Trae Agent, AutoCodeRover, Agentless, Smol Developer | out of adapter scope |
| Fork/wrapper without an independent contract | OpenClaude variants, claude-code-rust, Open Claude Cowork, Oh My OpenAgent, leaked/archival Claude clones | use underlying client, or exclude |
| Below the adoption gate | San, Neovate, OpenClaudia and other sub-2,000 projects | watchlist only |

This classification is intentionally conservative. Names such as Every Code,
Devon, Grok CLI, RA.Aid, Nanocoder, Kode, Codel, CodeMachine, OpenSquilla, and
similar discovery-list entries remain excluded unless current official
documentation proves the entire end-user plugin lifecycle. A large list of
partial adapters would increase permanent installer and doctor cost without
meeting the user's parity requirement.

### Other screened environments

The following are worth tracking, but they should not be added merely because
they support one or two portable files:

| Environment | Useful surface | Missing proof for first-class admission |
|---|---|---|
| Cline | rules, MCP, modes, skills in some surfaces | stable packaged lifecycle hooks and updater |
| Roo Code | modes, rules, commands, MCP | one supported plugin bundle and hook contract |
| Windsurf Cascade | rules, workflows, MCP | distributable lifecycle hooks |
| Continue | assistants, rules, prompts, MCP | session/edit hook package contract |
| Aider | repository conventions and scripting | skills/plugin/hook lifecycle |
| Goose | extensions, recipes, many hooks | subagent and pre-compaction events |
| Kiro CLI | steering, hooks, agents, powers | executable packaging and update contract proof |
| Mistral Vibe / Junie | skills or prompt integrations | full hook and plugin lifecycle |
| Xcode coding agents | skills and agent configuration | cross-platform installer and general plugin hooks |

These rows are discovery leads, not compatibility promises. Each requires the
same official-contract and executable contract-test pass before admission.

## Capability matrix and support tiers

Legend: Y = official/native; A = adapter/emulation; D = documented degradation;
? = must be proven; N = absent.

| Client/surface | Skills | Commands | Instructions | Required lifecycle | MCP/tool bridge | Update lifecycle | Admission |
|---|---:|---:|---:|---:|---:|---:|---|
| Claude Code | Y | Y | Y | Y | Y | Y | supported |
| Codex | Y | A via skills | Y | Y | Y | Y | supported |
| Copilot CLI | Y | Y | Y | Y, event-output limits | Y | Y | supported |
| Cursor IDE/local | Y | Y | Y | Y | Y | Y | target |
| VS Code Agent Plugins | Y | Y | Y | Y | Y | Y | target, preview |
| Qwen Code | Y | Y | Y | Y | Y | Y | target |
| Gemini CLI | Y | Y | Y | Y | Y | Y | transition target |
| Kimi Code | Y | Y | Y | Y | Y | Y | highest-priority target |
| Kilo Code | Y | Y | Y | Y plugin/event API | Y | Y | high-priority target |
| OMP | Y | Y | Y | Y | Y | Y | target |
| Pi | Y | Y | Y | Y | A | Y | target after bridge test |
| Hermes | Y | Y | Y | A, compact unproven | Y | Y | contract test |
| OpenCode | Y | Y | Y | A/composite | Y | Y | contract test |
| Amp | Y | Y | Y | Y | Y | A | contract/impact test |
| OpenHands normal client | Y | Y | A | Y in SDK | Y | Y in SDK | contract test |
| MiMo Code | Y | Y | Y | ? independent contract | Y | ? | contract test |
| Letta Code | Y | Y | native context | D | tool bridge | ? | watchlist |
| OpenHarness | Y | Y | CLAUDE.md | D | Y | ? | watchlist |
| Z Code | Y | Y | Y | ? undocumented schema | Y | Y | watchlist |
| Cursor CLI | Y | Y | Y | N documented parity | Y | Y | compatibility |
| Warp | Y | Y | Y | N | Y | Y app | compatibility |
| goose | Y | Y | Y | Y for ADR Kit events | Y | Y | contract test |
| Kiro CLI | Y | Y | Y | Y for ADR Kit events | Y | Y | contract test |
| Crush | Y | Y | Y | D PreToolUse only | Y | Y | excluded |
| Antigravity | Y | A via skill | Y | A PreInvocation + tool | Y | ? | contract test |
| OpenClaudia | Y | Y | client rules | D | Y | ? | below gate |
| Oh My OpenAgent | inherited | inherited | inherited | inherited | inherited | inherited | no separate adapter |
| OpenClaude | Y | Y | ? | N | Y | Y | excluded |
| Open Claude Cowork | inherited | inherited | inherited | inherited | inherited | inherited | no separate adapter |
| claude-code-rust | inherited | inherited | inherited | inherited | inherited | inherited | no separate adapter |
| Claw Code | Y | built-in | CLAUDE.md | N | Y | ? | excluded |

Tier meanings:

- **Supported/target:** eligible for automatic installation when detected, but
  a target becomes supported only after release certification and full doctor.
- **Contract test:** implementation may exist behind an explicit experimental
  flag; it is never presented as supported until every gate passes.
- **Compatibility:** portable artifacts may be offered explicitly, with a
  visible degradation report; no full-plugin claim or default automation.
- **Watchlist/excluded/no separate adapter:** documented by doctor and the
  report, but not installed.

## Target plugin architecture

### Canonical source plus generated adapters

Retain the existing Python core and introduce a declarative capability registry:

```text
clients/
  capabilities.json
  claude/
  codex/
  copilot/
  cursor/
  vscode/
  qwen/
  gemini/
  kimi/
  kilo/
  opencode/
  amp/
  omp/
  pi/
  hermes/
scripts/
  build-client-adapters.py
  install-agent-envs.py
  doctor-agent-envs.py
skills/                    canonical skills
prompts/                   canonical user-invocable workflows
instructions/
  ADR-guide.md              canonical installed guide
hooks/
  adr-hook.py               normalized Python hook core
  adapters/                 thin envelope translators
bin/ and schemas/           canonical deterministic engine
```

`capabilities.json` records event names, input fields, output fields, manifest
layout, root token, executable probes, install/update/list commands, and known
degradations. JSON preserves the stdlib-only build rule.

Generated payloads must never contain independently edited copies of the
engine. A build check compares normalized bytes and fails on drift.

### Stable internal hook protocol

Every native wrapper calls one command:

```text
python adr-hook.py --client <id> --event <normalized-event>
```

The wrapper:

1. reads native JSON from stdin;
2. validates only fields needed for that event;
3. normalizes tool names and paths;
4. resolves the highest valid ADR Kit engine root;
5. executes a bounded core operation;
6. maps the core result back to native JSON; and
7. exits in the client's fail-open form.

Pre-edit policy errors must not accidentally become fail-closed on clients such
as Copilot. The adapter catches all internal exceptions and emits a successful
empty result. Deterministic ADR violations remain the responsibility of the
git pre-commit floor.

### Commands, prompts, and skills

Each workflow has one canonical skill. Client adapters expose it through the
best native entry point:

- native slash command where plugins support prompt files;
- user-invocable skill where the client maps skills into `/`;
- namespaced command for clients with collision handling; and
- discoverable skill plus natural-language fallback where no command exists.

The command must not duplicate workflow instructions. It tells the client to
load the canonical skill with the supplied arguments.

## Installer design

### Detection

Detection is read-only and records:

- executable path and version;
- user/config home overrides;
- native plugin manager availability;
- installed ADR Kit version and source;
- legacy project footprints;
- disabled or untrusted hook state;
- duplicate installs across caches; and
- whether the client is supported, a contract-test candidate, compatibility
  only, or unsupported.

Do not infer installation from a directory alone. Run a short version probe and
the client's native list command when available.

### Idempotent desired-state algorithm

For every selected detected client:

1. validate the source release and all generated manifests;
2. validate Python 3.10+ and resolve its absolute executable;
3. prepare a versioned immutable payload in platform-local application data;
4. acquire a per-client install lock;
5. inspect existing installs, including prior marketplace names and caches;
6. no-op when version, source hash, trust state, MCP handshake, and artifacts
   already match;
7. install or update through the native client API;
8. atomically switch the active pointer only after validation;
9. run the client doctor;
10. retain the previous valid payload for rollback; and
11. remove only ADR Kit-owned stale payloads after the new version is healthy.

Re-running after interruption converges to the same state. Partial prepared
directories are never advertised as active.

### Automatic updates

Use the native update manager where it exists. For file-based adapters such as
Amp, maintain an ADR Kit-owned versioned install root and a tiny stable loader.

Recommended policy:

- automatically apply signed/verified stable patch and minor updates;
- never cross an incompatible major version without confirmation;
- update all adapters from one validated ADR Kit release;
- run doctor before switching active versions;
- roll back automatically if hook smoke tests or MCP handshake fail; and
- allow offline/pinned installations.

Because ADR Kit is pre-1.0, the release process should mark compatibility
breaks explicitly rather than assuming every minor version is safe.

### Project setup

Setup detects the repository root and patches only ADR Kit-owned markers in:

- `AGENTS.md`;
- `CLAUDE.md`;
- `.github/copilot-instructions.md`; and
- any required client-specific context file.

It writes `.adr-kit/ADR-guide.md` once, preserving local edits according to the
existing three-way upgrade policy. Client adapters should reference this
single guide rather than create one copy per client.

## Cross-client doctor

`adr-kit doctor` should have common and client-specific checks.

Common checks:

- Python version and executable path;
- canonical engine version and source hash;
- duplicate or stale version-ranked roots;
- ADR index health;
- instruction marker integrity;
- guide version and local modifications;
- MCP initialize/list-tools/call handshake;
- hook fixture input/output and fail-open behavior;
- latency against the budgets in this report; and
- permissions, trust, and disabled state.

Client checks:

- native executable and version;
- plugin list reports ADR Kit enabled;
- manifest version equals engine version;
- skills and commands are discoverable;
- hook events are installed and active;
- required trust/review has been accepted;
- MCP command resolves the current immutable payload;
- native update source is valid; and
- known degradations are printed plainly.

Machine-readable output:

```json
{
  "status": "pass|advisory|fail",
  "coreVersion": "0.x.y",
  "clients": {
    "codex": {
      "installed": true,
      "active": true,
      "version": "0.x.y",
      "checks": [],
      "degradations": []
    }
  }
}
```

Doctor must reproduce the stale-cache failure encountered during this research:
a current manifest whose launcher points at a removed older cache is a failure,
not a healthy current install.

## Phased implementation plan

### Phase 0: record the architecture decision

Create a Proposed ADR for canonical multi-client adapter generation. It should
cover the runtime-dependency exception for TypeScript-native clients, the
support admission rule, native update policy, and generated payload ownership.
Do not change accepted ADRs in place.

### Phase 1: normalize the current three clients

- move hook core behavior behind a client-neutral Python entry point;
- add Codex plugin hooks and trust-aware doctor checks;
- add Copilot lifecycle hooks with the documented pre-edit degradation;
- replace string-replacement skill generation with structured metadata;
- introduce `.adr-kit/ADR-guide.md` and managed blocks;
- add installer dry-run and JSON plan output; and
- add cache/launcher integrity checks.

Acceptance: all existing tests plus native list, hook smoke, MCP handshake, and
idempotent double-install tests for Claude, Codex, and Copilot.

### Phase 2: shared OpenPlugin family

Implement Cursor IDE/local and VS Code Agent Plugins from a shared OpenPlugin
adapter source. Use event-level filtering in the wrapper because VS Code
currently ignores Claude matcher values. Prototype goose from the same source,
but keep it behind the contract-test gate until its native package lifecycle
and doctor probes pass.

Acceptance: local edit receives ADR context before the write; post-edit backstop
works; command/skill and MCP are visible; cloud/unsupported surfaces are
reported as degraded rather than passing.

### Phase 3: Gemini-family adapters

Generate Qwen and Gemini extension payloads from shared sources, and implement
Kimi Code as the reference full-lifecycle adapter. Enable native auto-update
for Gemini when selected and native plugin update for Kimi. Keep all core
execution in Python.

Acceptance: extension install/update/list, skill invocation, command invocation,
SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, and MCP contract tests.
Kimi additionally proves legacy-layout migration and successful no-op handling
for unused lifecycle events.

### Phase 4: TypeScript bridge family

Build minimal reviewed bridges for OMP and Pi. The bridge contains no ADR
logic; it maps native events to the Python core. Package prompts and skills
from the canonical source. Keep Amp behind the commercial-impact and native
update contract gate.

Acceptance: clean install, update, rollback, reload, start/edit/stop smoke,
Windows path quoting, no network on hook hot paths, and p95 latency budget.

### Phase 5: Kilo and OpenCode plugin family

Build a shared TypeScript bridge for Kilo Code and OpenCode, with separate
client descriptors for paths, configuration, install/update commands, and
event envelopes. Kilo is the first certification target; OpenCode remains
experimental until its composite installer and Bun runtime trade-off are
accepted.

Acceptance: npm/local plugin install, skill and Markdown command discovery,
`AGENTS.md` propagation, MCP handshake, chat/session orientation, pre/post edit
hooks, `KILO_PURE=1` diagnosis, update/rollback, and CLI plus VS Code smoke.

### Phase 6: experimental contract tests

Prototype Hermes, Amp, goose, Kiro, Antigravity, OpenHands, and MiMo Code
without advertising support. Keep Z Code, Letta Code, OpenHarness, and
OpenClaudia in research-only status until their documented contracts improve.
Promote a client only when:

- all required artifacts install without manual code wiring;
- start context reaches the model;
- edits are observed with file arguments;
- a tool/MCP call works;
- project guidance and task-tier context reach every supported execution mode;
- unused lifecycle events no-op without blocking or mutating ADRs;
- upgrade and uninstall preserve unrelated configuration; and
- doctor can distinguish enabled, disabled, stale, and broken states.

## Verification strategy

### Fixture contracts

Maintain versioned native input/output fixtures for every supported event and
client. Test:

- missing optional fields;
- paths containing spaces and Unicode;
- malformed JSON;
- timed-out backends;
- missing Python;
- removed prior cache directories;
- duplicate hooks;
- disabled plugins;
- changed/trust-pending hooks;
- resumed and compacted sessions;
- repeated Stop and SessionEnd events; and
- non-ADR tools and unsupported event payloads.

### Native smoke matrix

Run at least one real native smoke per release:

| Client | Install/list | Skill/command | Hook | MCP | Update/rollback |
|---|---:|---:|---:|---:|---:|
| Claude | required | required | required | required | required |
| Codex | required | required | required | required | required |
| Copilot | required | required | required | required | required |
| Cursor local | required | required | required | required | required |
| VS Code | required | required | required | required | required |
| Qwen | required | required | required | required | required |
| Gemini | required while supported | required | required | required | required |
| Kimi | required | required | required | required | required |
| Kilo CLI + VS Code | required | required | required | required | required |
| OMP | required | required | required | required | required |
| Pi | required | required | required | required | required |

No client becomes supported based only on manifest validation.

## Decisions that should remain optional

Most deterministic behavior can safely default on for every detected supported
client. Three controls deserve an explicit policy:

1. **Cost-bearing LLM judgment:** keep opt-in, as required by ADR-001.
2. **Blocking git pre-commit enforcement:** recommend during project init, but
   allow users and automated installs to decline it.
3. **Automatic release policy:** choose between stable auto-update,
   notify-before-update, and pinned/offline.

Recommended default:

- install all detected supported clients;
- enable deterministic fail-open lifecycle hooks;
- install skills, commands/prompts, MCP, and managed instruction blocks;
- enable stable verified plugin updates with rollback;
- ask before installing a blocking git hook;
- keep LLM spending off.

## Source index

Primary sources used in the report:

- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex plugin building](https://learn.chatgpt.com/docs/build-plugins)
- [OpenAI Developers Codex plugin](https://developers.openai.com/learn/developers-codex-plugin)
- [Claude hooks](https://code.claude.com/docs/en/hooks)
- [Claude plugins](https://code.claude.com/docs/en/plugins)
- [Copilot CLI hooks](https://docs.github.com/en/copilot/reference/hooks-reference)
- [Copilot plugin creation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating)
- [Cursor plugins](https://cursor.com/docs/reference/plugins)
- [Cursor hooks](https://cursor.com/docs/hooks)
- [Antigravity plugins](https://antigravity.google/docs/plugins)
- [Antigravity hooks](https://antigravity.google/docs/hooks)
- [OpenCode plugins](https://opencode.ai/docs/plugins/)
- [VS Code Agent Plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
- [VS Code hooks](https://code.visualstudio.com/docs/agent-customization/hooks)
- [Qwen Code extensions](https://qwenlm.github.io/qwen-code-docs/en/users/extension/introduction/)
- [Qwen Code hooks](https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/)
- [Qwen Code source](https://github.com/QwenLM/qwen-code)
- [Gemini CLI extensions](https://geminicli.com/docs/extensions/reference/)
- [Kimi Code plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)
- [Kimi Code hooks](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/hooks.html)
- [Kimi Code documentation](https://www.kimi.com/code/docs/en/)
- [Kimi CLI source](https://github.com/MoonshotAI/kimi-cli)
- [Kilo Code source](https://github.com/kilo-org/kilocode)
- [Kilo Code plugins](https://kilo.ai/docs/automate/extending/plugins)
- [Kilo Code skills](https://kilo.ai/docs/customize/skills)
- [Kilo Code workflows](https://kilo.ai/docs/customize/workflows)
- [Kilo Code CLI](https://kilo.ai/docs/code-with-ai/platforms/cli)
- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes Agent source](https://github.com/NousResearch/hermes-agent)
- [Pi](https://pi.dev/)
- [OMP](https://github.com/can1357/oh-my-pi)
- [Amp manual](https://ampcode.com/manual)
- [goose](https://goose-docs.ai/)
- [goose hooks](https://goose-docs.ai/docs/guides/context-engineering/hooks/)
- [Warp source](https://github.com/warpdotdev/Warp)
- [Warp Agent Skills](https://docs.warp.dev/agent-platform/capabilities/skills)
- [Cursor CLI](https://docs.cursor.com/en/cli/using)
- [Kiro CLI hooks](https://kiro.dev/docs/cli/hooks/)
- [Crush source and hook guide](https://github.com/charmbracelet/crush/tree/main/docs/hooks)
- [Z Code plugins](https://zcode.z.ai/en/docs/plugin)
- [MiMo Code](https://github.com/XiaomiMiMo/MiMo-Code)
- [Aider](https://github.com/Aider-AI/aider)
- [CodeBuff](https://github.com/CodebuffAI/codebuff)
- [Groq Code CLI](https://github.com/build-with-groq/groq-code-cli)
- [Neovate Code](https://github.com/neovateai/neovate-code)
- [awesome-code-agents discovery list](https://github.com/sorrycc/awesome-code-agents)
- [awesome-cli-coding-agents discovery list](https://github.com/bradagi/awesome-cli-coding-agents)
- [Letta Code](https://github.com/letta-ai/letta-code)
- [OpenHands plugins](https://docs.openhands.dev/sdk/guides/plugins)
- [OpenHarness](https://github.com/HKUDS/OpenHarness)
- [Oh My OpenAgent](https://omo.dev/docs)
- [OpenSkills](https://openskills.cc/)
- [OpenClaudia](https://github.com/dollspace-gay/OpenClaudia/)
- [OpenClaude](https://openclaude.gitlawb.com/)
- [Open Claude Cowork](https://openclaudecowork.com/)
- [claude-code-rust](https://github.com/srothgan/claude-code-rust)
- [Claw Code architecture](https://claw-code.codes/architecture)
- [AGENTS.md](https://agents.md/)
- [Agent Skills](https://agentskills.io/)
- [skills.md](https://skills.md/docs)
