---
id: TASK-14
title: 'adr-review: PR/branch-level ADR audit skill + adr-suggest --intent-file'
status: Done
assignee: []
created_date: '2026-06-12 20:36'
updated_date: '2026-06-12 20:48'
labels:
  - tier-1
  - agent-guardrails
dependencies: []
references:
  - bin/adr-suggest
  - bin/adr-judge
  - bin/adr-context
  - skills/judge/SKILL.md
  - skills/guardian/SKILL.md
  - docs/research/2026-06-12-adr-landscape.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
New skill /adr-kit:review that audits the COMMITTED work of a branch/PR (not the staging area) against the ADR set, in two passes: (1) enforcement via the existing bin/adr-judge --diff - on the merge-base range diff (same engine as pre-commit and the CI action, so verdicts stay consistent), and (2) discovery: detect NEW architectural decisions in the range that no ADR documents yet, and drive drafting of Proposed ADRs for them. Discovery reads the diff PLUS the stated human intent (commit subjects/bodies via git log, PR title/body via gh pr view when available), because decisions are often confessed in prose while the diff looks like plumbing. Candidates are deduped against the existing set via bin/adr-context before anything is proposed. Closes the audit gap: judge enforces known decisions, suggest watches single staged commits, guardian watches the ADR set's health, but nothing audited a finished branch/PR for undocumented decisions.

Supporting bin enhancement: bin/adr-suggest --intent-file PATH appends commit/PR text to the detector prompt as a clearly delimited UNTRUSTED stated-intent section (prompt-injection posture: evidence of intent, never instructions; ties into task-12 hardening). Response schema unchanged; the skill's in-session model handles multi-decision analysis on top of the single adr-suggest signal.

Reuse: bin/adr-judge (enforcement engine), bin/adr-suggest (detector + llm_cmd security allowlist), bin/adr-context (dedupe ranking), adr-generator subagent (drafting), guardian/judge skill conventions (cost gate, never auto-accept, plugin path resolver).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 #1 /adr-kit:review resolves the branch range (merge-base with the base ref, default origin/main; gh pr view baseRefName when available) and runs bin/adr-judge --diff on it; enforcement pass works key-free (declarative-only) and reports violations per ADR
- [x] #2 #2 bin/adr-suggest accepts --intent-file PATH; the file content (commit messages / PR body) is appended to the LLM prompt as a delimited untrusted stated-intent block; missing file is a usage error (exit 2); response schema and advisory posture unchanged
- [x] #3 #3 Discovery pass surfaces candidate undocumented decisions from diff + intent; each candidate is deduped against existing ADRs via bin/adr-context before being proposed; user picks which to draft; drafted ADRs are Status: Proposed, never auto-accepted
- [x] #4 #4 Skill degrades gracefully: no gh CLI means no PR metadata (git log intent only), no claude CLI means enforcement-only with an honest note; advisory paths never fail the run
- [x] #5 #5 Tests cover --intent-file: intent text reaches the prompt inside the delimiters, intent absent keeps prompt byte-identical to before, missing intent file exits 2, intent is truncated to the documented cap
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.26.0. skills/review/SKILL.md (merge-base range, gh-aware, key-free judge pass, suggest + in-session discovery, adr-context dedupe, Proposed-only drafting) plus bin/adr-suggest --intent-file. Integration change vs the worktree version: the intent block uses the task-12 content-derived sentinel fences instead of static BEGIN-INTENT/END-INTENT markers, so intent gets the same unforgeable anti-injection guarantee as the diff; the 4 new tests were adapted accordingly. Full suite 373 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
