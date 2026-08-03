---
id: TASK-75
title: 'Hook the plan-mode exit: ask for missing ADRs before build mode starts'
status: Done
assignee: []
created_date: '2026-08-01 10:31'
updated_date: '2026-08-02 07:02'
labels:
  - spec-gap
  - R3
  - hooks
dependencies: []
modified_files:
  - hooks/manifest.json
  - hooks/adr_hook_core.py
  - hooks/hooks.json
  - scripts/client_certification.py
  - docs/client-support.md
  - tests/test_adr_plan_exit_hook.py
  - CHANGELOG.md
  - codex/
  - copilot/
priority: high
ordinal: 80500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R3 is the only requirement the audit found entirely absent — not partially built, not deferred to prose. A repo-wide case-insensitive grep for `plan mode|planmode|ExitPlan|exit_plan` returns hits only inside spec.md itself.

`hooks/manifest.json` declares exactly six events (session-start, user-prompt-submit, pre-tool-use, post-tool-use, subagent-start, pre-compact) and none is plan-related, so this is a new manifest event plus a matcher, not a wiring fix.

**Why this moment.** The plan is complete and no code exists yet. It is the cheapest possible point to notice a missing decision, and the only one where the answer can still shape the implementation rather than justify it afterwards.

**Mechanism.** In Claude Code, leaving plan mode is a tool call (`ExitPlanMode`), so `PreToolUse` with that matcher is a real attachment point, symmetric with the existing `Edit|MultiEdit|Write` matcher. Codex and Copilot need their own answer; where a client has no equivalent event, say so in the client-support matrix rather than pretending parity.

Keep it inside the existing hook contract: deterministic, injection-only, no model, 1 s budget (ADR-015). Run the deterministic candidate finder over the plan text and name what looks undecided; do not block.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 hooks/manifest.json gains a plan-exit event and the generated per-client hooks.json files carry it where the client supports it
- [x] #2 Leaving plan mode injects the ADRs governing the planned work plus any candidate decisions the plan appears to make
- [x] #3 The hook stays inside the ADR-015 budget, calls no model, and never blocks the transition
- [x] #4 Clients without an equivalent event are documented as such in docs/client-support.md rather than silently omitted
- [x] #5 A test asserts the hook fires on the plan-exit event and stays silent when the repository has no ADRs
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`PreToolUse` with an `ExitPlanMode` matcher: the plan-mode transition now injects the ADRs governing the plan and asks whether the plan makes a decision no ADR records yet.

The attachment point turned out to be cheaper than the task expected. Leaving plan mode is a tool call, so the existing pre-tool surface carries it with a different matcher - one manifest event and one branch, not a new hook runtime.

Two design choices worth keeping:

**It asks and never blocks.** A gate here would teach people to write an empty ADR to get past it, which is exactly the failure mode that produced six rule-less Enforcement blocks in this repository. The injected text ends with the grill invocation so the question arrives with the way to answer it.

**Absent parity is recorded, not invented.** Codex and Copilot expose no plan-mode transition; the manifest holds `null` for both and the client-support matrix gained a Plan exit column that says "no plan-mode event". A fabricated event name would be a parity nobody could rely on.

A test asserts the new matcher does not swallow the fail-closed edit floor of ADR-004: an Edit still takes the pre-edit path.

Gates: 1320 passed / 12 skipped, adapter drift clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
