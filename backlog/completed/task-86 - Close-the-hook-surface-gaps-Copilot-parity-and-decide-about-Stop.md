---
id: TASK-86
title: 'Close the hook-surface gaps: Copilot parity, and decide about Stop'
status: Done
assignee: []
created_date: '2026-08-01 10:35'
updated_date: '2026-08-02 19:54'
labels:
  - spec-gap
  - R4
  - hooks
  - client-parity
dependencies: []
modified_files:
  - docs/adr/ADR-019-keep-the-end-of-session-hooks-deliberately-silent.md
  - hooks/adr_hook_core.py
  - scripts/client_certification.py
  - docs/client-support.md
  - tests/test_adr_hook_noop_events.py
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
- [x] #1 Copilot either gains pre-edit injection or docs/client-support.md records the missing fail-closed floor as a known degradation
- [x] #2 The Stop/SessionEnd question is decided in an ADR rather than left as an undocumented no-op
- [x] #3 If an end-of-session hook is added, its cost and budget are explicit and it degrades like every other hook
- [x] #4 The NOOP_EVENTS list carries a comment explaining why each entry is silent, so the next reader inherits the reasoning
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**AC#1 — Copilot's missing fail-closed floor is now recorded plainly.** The degradation already existed in `clients/capabilities.json` and `clients/exceptions.json`, but `docs/client-support.md` only said "unsupported native event", which tells a reader nothing about what they lose. The generated matrix now names it: ADR-004 calls the pre-edit tier the fail-closed floor, on Copilot that floor does not exist, and `postToolUse` reporting drift after the write is a weaker guarantee by construction. It also names what does not weaken — the pre-commit hook is client-independent. Copilot was not given pre-edit injection because it exposes no pre-tool-use event that can carry model context.

**AC#2/#3 — ADR-019 records the end-of-session decision** (`docs/adr/ADR-019-keep-the-end-of-session-hooks-deliberately-silent.md`). It keeps the silence and states the two reasons: answering "were decisions made?" over a session needs a model, and a session ends when nobody is watching, so a hook that spends there spends on an event the user cannot see fire and cannot refuse. Every other paying path in the kit is opt-in or asks first; neither property survives at session end. The question moves to `/adr-kit:audit` (TASK-84) and `adr-suggest`, which run on request. Its Decision Contract forbids any hook spending on an unseeable event, and the Exceptions section notes that a deterministic listing-only summary is excluded for a different reason — it writes when attention has left.

**AC#4 — `NOOP_EVENTS` carries a reason per entry**, including the two that are not about the work at all (a permission dialog and a notification are UI moments) and the one nobody wants more text during (an interrupt).

`tests/test_adr_hook_noop_events.py` (11 tests) holds the silence in place: the three events stay in `NOOP_EVENTS`, no client registers them, the runner answers nothing and exits 0, and the rationale comment is present. A change that wires one up fails there first.

**ADR-019 is Proposed, not Accepted — accepting it is the maintainer's call, never the agent's.** Its retrieval metadata was narrowed after the dogfood probe caught the first draft outranking ADR-004 for "fail open lifecycle hook context injection"; this ADR is about end-of-session silence, not injection. Full suite green (1395 passed, 13 skipped).
<!-- SECTION:FINAL_SUMMARY:END -->
