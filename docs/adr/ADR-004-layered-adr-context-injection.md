---
id: "ADR-004"
title: "Layered ADR Context Injection for Agent Work"
status: "Accepted"
date: "2026-07-05"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
---
# ADR-004 Layered ADR Context Injection for Agent Work

## Status

Accepted, 2026-07-05.

<!-- When accepted or superseded: update this line and append the same transition below in Status History. Do not edit earlier history entries or other sections of an Accepted/Deprecated ADR; write a new superseding ADR instead. -->

## Status History

```yaml
status_history:
  - date: 2026-07-05
    status: Proposed
    changed_by: robert@vandenbreemen.net
    reason: Initial proposal
    changed_via: adr-kit v0.30.5
  - date: 2026-07-05
    status: Accepted
    changed_by: robert@vandenbreemen.net
    reason: Approved; implementing all phases of the companion design spec
    changed_via: adr-kit v0.30.5
```

## Context

adr-kit already carries the knowledge (Accepted ADRs) and three of the four
mechanisms needed to put that knowledge in front of a coding agent, but they are
not organised into one coherent model and one of them fires on the wrong side of
the action.

The existing surfaces:

1. **Session tier.** `bin/adr-guardian check` (ADR-002) injects health and
   staleness nudges at `SessionStart`, and `templates/adr-kit-guide.md` is
   `@`-imported into `CLAUDE.md` at init. Deterministic, no LLM.
2. **Edit tier.** `bin/adr-watch --hook` runs at `PostToolUse` for
   `Edit|MultiEdit|Write` and prints at most three nudges naming the Accepted
   ADRs that match the edited path (Enforcement `path_glob`, score 1.0; keyword
   relevance, scaled to 0.8). Deterministic. Two weaknesses: it fires *after* the
   edit is already written, so it cannot steer the code the agent produces, and it
   emits only the ADR *name*, not the decision the agent must honour.
3. **Task tier.** `bin/adr-context` ranks ADRs against a query with five weighted
   signals (`exact_keyword` 0.40, `domain_tag` 0.25, `related_decisions` 0.15,
   `acceptance_status` 0.10, `recency` 0.10). Deterministic, no LLM. Pulled by the
   `adr-generator` subagent and `/adr-kit:judge`, and exposed key-free over MCP
   (`bin/adr-mcp` tool `adr_context`).
4. **Enforcement floor.** `bin/adr-judge` runs declarative `forbid_pattern` /
   `forbid_import` / `require_pattern` rules from each ADR's `## Enforcement` block
   against the staged diff at pre-commit. Fully deterministic. Optional
   `llm_judge: true` escape hatch, opt-in since ADR-001.

The reference for organising these is the OpenWolf context-management layer used
in the sibling `OTGW-firmware` project (`.wolf/hooks/*.js`, wired through
`.claude/settings.json`). OpenWolf runs a three-part loop around a knowledge
store: inject (a static `@`-imported index plus a `PreToolUse:Read` hook that
prints an `anatomy.md` summary *before* the read), freshen (a `PostToolUse:Write`
hook that upserts the index), and enforce (a small fail-closed floor that is
deliberately *not* part of OpenWolf itself, only the `backlog-mcp-guard.py` exit-2
guard and the git `commit-msg`/`pre-commit` hooks). Two lessons transfer:

- **Inject before the action, not after.** OpenWolf's token and steering win comes
  from `PreToolUse:Read` running before the file is read. adr-watch's `PostToolUse`
  timing is the equivalent of injecting after the read: too late to change the
  outcome.
- **The maintained layer and the enforced layer must read the same on-disk field.**
  OpenWolf's auto-bug-detector silently no-ops forever because the hooks read
  `{bugs:[]}` while the file on disk is a bare array. The OTGW `cerebrum.md`
  bug-036 records the same failure for ADR *status*: there was no canonical status
  line, so tooling matched the wrong text. Any injector and the judge must agree on
  where scope and status live.

What is missing is (a) an explicit layered model with a documented soft-steer
versus hard-gate boundary, (b) an edit-tier injector that fires *before* the write
and carries the decision text, not just the ADR name, and (c) a pinned pair of
canonical machine-readable fields that every reader shares.

## Decision

Adopt a layered ADR context injection model with three fail-open injection tiers
and one fail-closed enforcement floor, and pin the canonical fields all readers
share.

1. **Three injection tiers, all fail-open (exit 0), never blocking:**
   - **Session tier.** Keep `adr-guardian` (ADR-002). Add a generated
     `docs/adr/ADR-INDEX.md` (one row per ADR: id, status, one-line decision,
     `path_glob` scope) produced deterministically by a new `bin/adr-index` and
     `@`-imported into `CLAUDE.md`. Regenerated on demand and in CI, not on a
     daemon.
   - **Edit tier.** Add a `PreToolUse` hook for `Edit|MultiEdit|Write` that reuses
     the existing adr-watch matcher (Enforcement `path_glob` strongest, keyword
     fallback) to find the governing ADR for the target path and injects that
     ADR's `## Decision` text (the constraint), bounded to a fixed token budget,
     as `hookSpecificOutput.additionalContext` *before* the edit is applied. The
     existing adr-watch `PostToolUse` nudge is retained as a lightweight
     confirmation backstop. Both share the cooldown state in
     `docs/adr/.adr-kit-state.json`.
   - **Task tier.** Keep `bin/adr-context` and the key-free MCP tools
     (`adr_context`, `adr_judge`). Document them as the pull-feed available to any
     subagent or workflow so an agent can retrieve decisions and self-check a diff
     mid-task.
2. **One fail-closed floor.** `bin/adr-judge` at pre-commit (and the CI action)
   remains the only mechanism that blocks. Injection hooks never block; they steer.
3. **Pin canonical fields.** Scope is the `## Enforcement` `path_glob`; status is
   the `## Status` line reconciled with the latest (last) `status_history` entry,
   the same `entries[-1]` comparison `bin/adr-judge` and `bin/adr-lint` already
   make. The new
   injector and index reader use exactly these fields, the same ones `adr-judge`
   already reads. No new duplicate status or scope source is introduced.
4. **Bound the injected content.** The edit-tier injector caps injected text to the
   single top-ranked ADR's decision within a fixed token budget, and honours the
   adr-watch cooldown, so context is not flooded and the same ADR is not re-injected
   within the window.

## Alternatives Considered

- **Keep PostToolUse-only (status quo).** adr-watch already names ADRs after an
  edit. Rejected as the edit tier: it fires after the code is written, so it cannot
  steer the code the agent produces, and it carries no decision text.
- **Hard-block edits to ADR-governed paths (PreToolUse exit 2).** Deny any edit
  that touches a path an Accepted ADR governs until the agent acknowledges it.
  Rejected: brittle and hostile. Legitimate compliant edits touch governed paths
  constantly; a fail-closed edit gate produces false positives and contradicts the
  advisory posture that the pre-commit judge already backstops. Blocking belongs at
  commit, not keystroke.
- **LLM or embedding retrieval (RAG) for injection.** Build a vector index of ADRs
  and retrieve by semantic similarity. Rejected: adds a store to build and keep in
  sync, introduces nondeterminism and per-call cost, and duplicates a job that
  `adr-context`'s deterministic keyword-plus-domain ranking already does well
  enough. It also violates the toolkit's standing "no database, no embeddings, parse
  Markdown live" design.
- **MCP pull-only (agent must ask).** Expose only `adr_context`/`adr_judge` and rely
  on the agent to query. Rejected as the sole mechanism: it depends on the agent
  choosing to ask, so decisions can be missed entirely. Pull complements push; it
  does not replace it.
- **Always-on full-ADR dump into context.** `@`-import every ADR in full.
  Rejected: unbounded token cost that grows with the ADR set and no relevance
  ranking, so the signal for the current task is buried. The one-line index plus
  targeted edit-time injection carries the same coverage at a fraction of the cost.

## Consequences

**Positive:**

- The agent sees the governing decision *before* it writes the code, closing the
  gap where adr-watch fired too late.
- One documented model with a clear soft-steer versus hard-gate boundary replaces
  four ad hoc surfaces, so the enforcement posture is legible.
- All tiers stay deterministic and key-free; the only cost-bearing path
  (`llm_judge`) is unchanged and still opt-in per ADR-001.
- Pinning scope and status to fields the judge already reads removes the
  status-mismatch failure class that bit OpenWolf's buglog and OTGW bug-036.
- Reuses the existing adr-watch matcher, cooldown state, and additionalContext
  envelope, so the new component is small.

**Negative:**

- A second hook fires on every `Edit|MultiEdit|Write`. The `PreToolUse` injector
  must hold the same sub-100ms, always-exit-0 budget as adr-watch or it will slow
  the edit loop.
- `docs/adr/ADR-INDEX.md` is a generated artifact that can drift if not
  regenerated; it needs a regeneration trigger (CI check or a post-write nudge) to
  stay honest.
- Injecting decision text spends context tokens on every governed edit; the token
  budget cap and cooldown are load-bearing and must be tuned, not left unbounded.

## Related Decisions

- Builds on ADR-001 (Make Per-Commit LLM Gates Opt-In): the fail-closed floor keeps
  the LLM pass opt-in; all new tiers are deterministic and free.
- Builds on ADR-002 (ADR Guardian): reuses the fail-open exit-0 hook contract, the
  `hookSpecificOutput.additionalContext` envelope, and the
  `docs/adr/.adr-kit-state.json` cooldown-state pattern. The edit tier is the
  `PreToolUse` sibling of the guardian's `SessionStart` detector.

## References

- Design spec and phased plan: `docs/superpowers/specs/2026-07-05-adr-agent-injection-design.md`
- Task-tier feed: `bin/adr-context` (five-signal ranking, weights at `bin/adr-context:249`), MCP tool `adr_context` in `bin/adr-mcp:293`
- Edit-tier prior art: `bin/adr-watch` (PostToolUse matcher, `path_glob` strongest then keyword, `bin/adr-watch:35`)
- Claude Code hook contract (SessionStart / PreToolUse / PostToolUse envelopes): https://docs.claude.com/en/docs/claude-code/hooks
- Session-tier prior art: `bin/adr-guardian` (SessionStart detector, ADR-002)
- Enforcement floor: `bin/adr-judge`, `schemas/adr-enforcement.schema.json`
- Hook wiring: `.claude-plugin/plugin.json`, `.claude-plugin/hooks/`
- OpenWolf reference pattern: `OTGW-firmware/.wolf/hooks/{pre-read,post-write}.js`, `OTGW-firmware/.claude/settings.json`, and the status-mismatch failure recorded in `OTGW-firmware/.wolf/cerebrum.md` (bug-036)
- ADR-001: `docs/adr/ADR-001-llm-gates-opt-in.md`
- ADR-002: `docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md`

## Enforcement

```json
{
  "llm_judge": false
}
```

Manual review only. The load-bearing properties of this decision are behavioral,
not syntactic: the injection hooks must always exit 0 (fail-open), the edit-tier
injector must hold a bounded token budget and honour the cooldown, and the injector
and index must read the pinned canonical fields (`## Enforcement` `path_glob` for
scope, the `## Status` line for status) rather than inventing a new source. These
cannot be expressed as regex on a staged diff without broad false positives, the
same reasoning ADR-002 applied to the guardian. Reviewers should verify: (a) the new
`PreToolUse` hook wrapper and its bin exit 0 on every path including error paths,
(b) the injected content is capped to the configured token budget for a single
top-ranked ADR, and (c) scope and status are read only from the pinned fields.
