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

## Observed client evidence

What an installed binary reported, from its own event stream. Separate
from the table above on purpose: that one says what adr-kit is wired
for, this one says what a client did. Every hook defect this kit has
shipped lived in the gap between the two.

An event that does not appear here is `not-observed`, not unsupported.
A probe run that used no tools cannot produce a tool event, and reading
that silence as a missing capability is how this document acquired the
claims it had to be rewritten to remove.

| Client | Version | Platform | Evidence | Observed events |
|---|---|---|---|---|
| Claude Code CLI | 2.1.221 (Claude Code) | win32 | native | `SessionStart`, `Stop`, `UserPromptSubmit` |

Source: `tests/certification/probe-windows.json`.
Regenerate with `python scripts/probe-client-events.py`, which exits 0 when a client is absent because an unmeasured client is a normal outcome rather than a failure.

All retrieval is local, bounded, and index-first. Unsupported native lifecycle events are not advertised; deterministic pre-commit enforcement remains the backstop.

## Where enforcement is fail-closed

Derived from `hooks/manifest.json` and `clients/capabilities.json`.

ADR-004 puts all three injection tiers -- session, edit and task -- on
the fail-open side without exception: they steer, and none of them
blocks. It rejected a fail-closed edit gate by name, because legitimate
compliant edits touch governed paths constantly, so blocking belongs at
commit rather than at keystroke. There is no pre-edit floor on any
client, and the absence of one is not a degradation.

Two tiers block, and neither is an injection tier:

* **Commit tier** (ADR-004) -- `bin/adr-judge` at pre-commit and in CI.
  Client-independent, because `git commit` happens whether or not an
  agent is running. A violation is caught before the commit lands on
  every client in this table, and on no client at all.
* **Pull-request tier** (ADR-023) -- `hooks/adr_pr_guard.py` on
  `gh pr create`. Client-qualified: a client that has no permission
  decision to return cannot stop the tool call, and where it cannot the
  branch is still judged and the verdict shown, labelled as advisory.

| Client | Pull-request tier |
|---|---|
| Claude Code CLI | enforced at `PreToolUse` |
| Codex CLI | advisory only (`codex-pr-guard-advisory-only`) |
| GitHub Copilot CLI | no native event: the commit tier is the only floor here |

## Known degradations

Every entry is declared in `clients/capabilities.json`, with its reason,
its user-visible effect and the backstop that still holds (ADR-010,
ADR-023). A weakening that is not declared there does not appear here.

| Client | Outcome | Reason | User effect | Backstop |
|---|---|---|---|---|
| Claude Code CLI | `workflow-discovery` | Claude supports richer skill metadata and native slash-command discovery. | Claude receives the canonical rich skill while the other clients receive generated concise adapters with the same outcome. | All clients also receive generated prompt wrappers and use the same executables. |
| Codex CLI | `enforcement` | The Codex hook adapter has no permission decision to return, so a PreToolUse hook cannot stop the tool call. | The branch is judged and the violation is shown, labelled as not enforced at this moment, rather than the pull request being stopped. | The pre-commit hook blocks the commit, and adr-judge-self.yml judges the branch diff on the pull request. |
| GitHub Copilot CLI | `edit-governance` | Copilot CLI exposes no pre-tool-use event, so ADR-004's edit tier has no moment to fire in. That tier is an injection tier, not a floor: what is absent here is context before the write, not enforcement. | The governing decision is not injected before an edit; postToolUse reports drift after the write instead. | Generated workflow prompts require an ADR lookup before edits, postToolUse records drift, and the commit tier still blocks a violation on every client. |
| GitHub Copilot CLI | `task-context` | Copilot CLI does not expose SubagentStart or PreCompact lifecycle hooks. | Selected ADR context cannot be re-injected at those unavailable event boundaries. | Session and prompt context remain native; generated workflow instructions require agents to carry the selected ADR bundle forward without broadening it. |

IDE, cloud, preview, wrappers, legacy surfaces, and TASK-43 clients are not promoted by this matrix.
