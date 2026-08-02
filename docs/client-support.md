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

IDE, cloud, preview, wrappers, legacy surfaces, and TASK-43 clients are not promoted by this matrix.
