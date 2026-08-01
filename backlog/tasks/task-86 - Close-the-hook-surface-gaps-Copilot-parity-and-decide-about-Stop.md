---
id: TASK-86
title: 'Close the hook-surface gaps: Copilot parity, and decide about Stop'
status: To Do
assignee: []
created_date: '2026-08-01 10:35'
labels:
  - spec-gap
  - R4
  - hooks
  - client-parity
dependencies: []
priority: low
ordinal: 91500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R4 and R14. The registered ledger today: Claude Code and Codex six events each (SessionStart 5 s, UserPromptSubmit 5 s, PreToolUse 1 s on `Edit|MultiEdit|Write`, PostToolUse 1 s same matcher, SubagentStart 1 s, PreCompact 1 s); GitHub Copilot three (sessionStart, userPromptSubmit, postToolUse). Two gaps that are not covered by TASK-75 or TASK-76.

**Copilot has no pre-edit injection.** `hooks/manifest.json` lists `github-copilot-cli` as null for pre-tool-use, subagent-start and pre-compact. ADR-004 calls the pre-edit tier the fail-closed floor, so on Copilot that floor does not exist — the post-edit backstop is all there is. Either the client genuinely cannot do it, in which case `docs/client-support.md` should say so plainly as a documented degradation, or it can and the manifest is simply behind.

**Stop, SubagentStop and SessionEnd are a designed silence.** They are hard-coded in `NOOP_EVENTS` (`hooks/adr_hook_core.py:35-43`) and registered by no client. That is exactly where "work finished — were decisions made?" belongs, and its absence is why R2's second clause has nowhere natural to live.

The reason for the silence is real: every hook today is deterministic and model-free, and answering "were decisions made?" over a whole session wants a model. So this is a decision, not an oversight, and it should be made deliberately — an ADR before code. Options worth weighing: keep the silence; add a deterministic end-of-session summary that only *lists* changed surfaces without judging them; or allow one bounded model call at session end, which would be the first hook to spend.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Copilot either gains pre-edit injection or docs/client-support.md records the missing fail-closed floor as a known degradation
- [ ] #2 The Stop/SessionEnd question is decided in an ADR rather than left as an undocumented no-op
- [ ] #3 If an end-of-session hook is added, its cost and budget are explicit and it degrades like every other hook
- [ ] #4 The NOOP_EVENTS list carries a comment explaining why each entry is silent, so the next reader inherits the reasoning
<!-- AC:END -->
