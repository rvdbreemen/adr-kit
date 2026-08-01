---
id: TASK-75
title: 'Hook the plan-mode exit: ask for missing ADRs before build mode starts'
status: To Do
assignee: []
created_date: '2026-08-01 10:31'
updated_date: '2026-08-01 10:32'
labels:
  - spec-gap
  - R3
  - hooks
dependencies: []
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
- [ ] #1 hooks/manifest.json gains a plan-exit event and the generated per-client hooks.json files carry it where the client supports it
- [ ] #2 Leaving plan mode injects the ADRs governing the planned work plus any candidate decisions the plan appears to make
- [ ] #3 The hook stays inside the ADR-015 budget, calls no model, and never blocks the transition
- [ ] #4 Clients without an equivalent event are documented as such in docs/client-support.md rather than silently omitted
- [ ] #5 A test asserts the hook fires on the plan-exit event and stays silent when the repository has no ADRs
<!-- AC:END -->
