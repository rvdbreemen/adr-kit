<!-- Generated from certification evidence; do not edit. -->
# ADR Kit client support

| Client | Surface | Windows | macOS | Linux | Evidence |
|---|---|---|---|---|---|
| Claude Code CLI | CLI | pass | not-run | not-run | simulated only |
| Codex CLI | CLI | pass | not-run | not-run | simulated only |
| GitHub Copilot CLI | CLI | pass | not-run | not-run | simulated only |

## Lifecycle retrieval support

Derived from `hooks/manifest.json`, which is the registry of what each
client is *wired for*. A cell names that client's own event, or states
that the client offers none.

This table makes one claim and not two. It says a moment is registered;
it does not say the wiring behind it works. That second question belongs
to the dispatch tests, which drive every registered event through the
real entrypoint on every client -- and it is a question worth keeping
separate, because `Plan exit | supported (ExitPlanMode)` sat in this file
through a release in which that event never fired. The Evidence column
above says how the wiring was verified.

| Client | Session global | Prompt/task query | Edit query | Post-edit backstop | Plan exit | Shell tool / PR moment | Subagent | Compaction |
|---|---|---|---|---|---|---|---|---|
| Claude Code CLI | `SessionStart` | `UserPromptSubmit` | `PreToolUse` / `Edit\|MultiEdit\|Write` | `PostToolUse` / `Edit\|MultiEdit\|Write` | `PreToolUse` / `ExitPlanMode` | `PreToolUse` / `Bash` | `SubagentStart` | `PreCompact` |
| Codex CLI | `SessionStart` | `UserPromptSubmit` | `PreToolUse` / `Edit\|MultiEdit\|Write` | `PostToolUse` / `Edit\|MultiEdit\|Write` | no native event | `PreToolUse` / `Bash` | `SubagentStart` | `PreCompact` |
| GitHub Copilot CLI | `sessionStart` | `userPromptSubmitted` | no native event | `postToolUse` / `Edit\|MultiEdit\|Write` | no native event | no native event | no native event | no native event |

All retrieval is local, bounded, and index-first. Unsupported native lifecycle events are not advertised; deterministic pre-commit enforcement remains the backstop.

### Known degradation: no fail-closed edit floor on GitHub Copilot CLI

ADR-004 names the pre-edit tier the *fail-closed* floor of the injection
model: the one place that refuses rather than degrades, because an edit is
the last moment before a decision is violated in code. Copilot CLI exposes
no pre-tool-use event that can carry model context, so on that client the
floor does not exist. What runs instead is a backstop, and a backstop is a
weaker guarantee by construction: `postToolUse` reports drift after the
edit has already been written, and the generated workflow prompts ask for
an ADR lookup before editing, which is instruction rather than enforcement.

This is stated here rather than left to be inferred from a null in
`hooks/manifest.json`. The enforcement that does not weaken is the
pre-commit hook, which is client-independent: a violation is caught before
the commit lands on every client, including this one.

IDE, cloud, preview, wrappers, legacy surfaces, and TASK-43 clients are not promoted by this matrix.
