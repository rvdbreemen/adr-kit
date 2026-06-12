---
id: TASK-13
title: '/adr-kit:review: PR-level decision discovery + enforcement skill'
status: To Do
assignee: []
created_date: '2026-06-12 20:32'
labels:
  - tier-2
  - agent-guardrails
  - teams
dependencies: []
references:
  - docs/research/2026-06-12-adr-landscape.md
  - bin/adr-suggest
  - bin/adr-judge
  - bin/adr-context
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PR-level vigilance pass orchestrating existing engines over a committed range instead of the staging area. (1) Range resolution: merge-base vs origin/main; optionally gh pr view for title/body. (2) Enforcement pass: pipe range diff into bin/adr-judge --diff -. (3) Discovery pass: bin/adr-suggest with new --intent-file flag carrying git log subjects/bodies + PR body as clearly delimited untrusted "stated intent" data (catches "migrate to Redis" confessed in commit message but invisible in diff); response may carry multiple findings. (4) Dedupe gate via bin/adr-context per candidate (high score = already documented, or supersede hint). (5) Follow-through: draft Proposed ADRs via existing authoring flow, never auto-accept. Optional advisory CI comment action (never fails build, opt-in LLM posture per v0.17). Prompt-injection caution: PR bodies attacker-writable; reuse task-12 sentinel delimiting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Skill resolves branch range en draait judge + suggest erover
- [ ] #2 adr-suggest --intent-file voegt commit/PR-tekst toe als gedelimiteerde untrusted data, backward compatible
- [ ] #3 Dedupe via adr-context voorkomt ADR-spam
- [ ] #4 Kandidaten worden als Proposed ADR-drafts gepresenteerd, nooit auto-accepted
<!-- AC:END -->
