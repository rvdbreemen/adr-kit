---
id: TASK-116
title: >-
  Add plan-exit and pr-create to the capability registry, and settle the Codex
  deny question
status: To Do
assignee: []
created_date: '2026-08-03 19:36'
labels:
  - clients
  - hooks
dependencies:
  - TASK-90
priority: medium
ordinal: 5200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`clients/capabilities.json` lists `hooks/manifest.json` and its siblings under `ownership.canonical`, but its `event_mappings` for all three clients cover only edit-governance, task-context, prompt-context, subagent-context and compaction-context. Neither of the two most recently added moments has an entry, so the registry lags the manifest it claims to be canonical for.

The second half becomes live once TASK-90 lands: `hooks/adapters/codex.py` ignores `kind`, so a `pr-guard-deny` would be emitted as advisory `additionalContext` **after** `adr-judge` has already been spawned and paid for. That is the worst of both — the cost of a gate with none of the protection.

Two possibilities and they need distinguishing rather than guessing: either Codex PreToolUse supports a permission decision and this is an adapter bug, or it does not and this is a degradation missing from `clients/exceptions.json` (no codex entry) and from `clients/capabilities.json` (`degradations: []` for codex-cli). R17 requires a degradation to be recorded with its user-visible effect, its reason and its backstop.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `plan-exit` and `pr-create` have `event_mappings` entries for all three clients
- [ ] #2 The Codex deny question is answered from the client's documented behaviour, not assumed
- [ ] #3 If Codex cannot deny: the degradation is recorded in `clients/exceptions.json` and `capabilities.json` with effect, reason and backstop, and the guard does not spend on a judge whose verdict it cannot enforce
- [ ] #4 If Codex can deny: `hooks/adapters/codex.py` honours `kind` and a test proves the deny reaches the client
<!-- AC:END -->
