<!-- Generated from certification evidence; do not edit. -->
# ADR Kit client support

| Client | Surface | Windows | macOS | Linux | Evidence |
|---|---|---|---|---|---|
| Claude Code CLI | CLI | pass | not-run | not-run | simulated only |
| Codex CLI | CLI | pass | not-run | not-run | simulated only |
| GitHub Copilot CLI | CLI | pass | not-run | not-run | simulated only |

## Lifecycle retrieval support

| Client | Session global | Prompt/task query | Edit query | Plan exit | Subagent/compaction |
|---|---|---|---|---|---|
| Claude Code CLI | Accepted global only | Accepted governing + Proposed advisory | supported | supported (ExitPlanMode) | preserves parent context |
| Codex CLI | Accepted global only | Accepted governing + Proposed advisory | supported | no plan-mode event | preserves parent context |
| GitHub Copilot CLI | supported task context | Accepted governing + Proposed advisory | unsupported native event | no plan-mode event | unsupported native events |

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
