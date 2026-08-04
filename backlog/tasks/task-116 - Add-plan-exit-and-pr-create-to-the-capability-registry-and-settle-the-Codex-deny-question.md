---
id: TASK-116
title: >-
  Add plan-exit and pr-create to the capability registry, and settle the Codex
  deny question
status: Done
assignee: []
created_date: '2026-08-03 19:36'
updated_date: '2026-08-04 01:17'
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
- [x] #1 `plan-exit` and `pr-create` have `event_mappings` entries for all three clients
- [ ] #2 The Codex deny question is answered from the client's documented behaviour, not assumed
- [x] #3 If Codex cannot deny: the degradation is recorded in `clients/exceptions.json` and `capabilities.json` with effect, reason and backstop, and the guard does not spend on a judge whose verdict it cannot enforce
- [ ] #4 If Codex can deny: `hooks/adapters/codex.py` honours `kind` and a test proves the deny reaches the client
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`plan-exit` and `pr-create` are mapped per client with their matchers, for every client whose manifest entry offers them.

**Writing the test found three more gaps, and none was a missing row — each was a factual error about a client's protocol.**

- **`post-tool-use` had no entry on Claude Code or Codex at all.** `edit-governance` mapped only the pre-edit half, so the post-edit backstop — a tier that ships and fires — was absent from the registry that describes what ships.
- **Copilot's session event was recorded as `SessionStart`.** The client calls it `sessionStart`, and the same file already used Copilot's own spelling for `userPromptSubmitted`. The registry was internally inconsistent about the protocol of the client it describes, which is the one thing it exists to be right about.
- **Copilot's edit-governance backstop was recorded as `PostToolUse`** rather than `postToolUse` — the same error one row down.

The test walks every manifest event against every client that offers it and matches on native name *and* matcher together, so a row that exists but names the wrong event still fails. That is what caught all three.

**AC#2 and AC#4 were settled on `release/v0.44.1`, not here.** The Codex deny question was answered there when TASK-90 made the guard reachable: `hooks/adapters/codex.py` has no permission decision to return, so it labels the verdict as advisory and names the enforcing gates, and the degradation is recorded in `clients/exceptions.json` and `capabilities.json` with effect, reason and backstop. Repeating those edits on this branch would produce a merge conflict for no gain.

Full suite: 1566 passed, 13 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
