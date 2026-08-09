---
id: TASK-157
title: >-
  Harden the per-ADR stamp against silent loss, and keep the R5 instruction
  inside the budget
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 15:05'
updated_date: '2026-08-09 15:23'
labels:
  - bug
  - guardian
  - hooks
dependencies: []
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Four review findings against dev after PR #84/#85, each empirically reproduced. (1) stamp llm --adr '' --verdict ok passes validation (not-None) but fails the truthiness dispatch, falling through to the TIER branch: an empty id stamps a completed sweep, exit 0. (2) An id that does not match a filename-derived id (nonexistent ADR-999, unpadded ADR-1) is written and then pruned inside the same transaction: exit 0, verdict silently lost - a violation vanishing is exactly the false state ADR-037 forbids. (3) The guardian skill step 3b maps adr-judge exit 0 to verdict ok, but a DEGRADED llm pass (no backend, per ADR-017 never-block) also exits 0: a sweep with a broken backend stamps every ADR ok without a single model call. (4) The R5 selection instruction is appended before the Python MAX_CONTEXT_CHARS slice, so at a large candidate set the instruction is the first thing truncated; the Rust host truncates per render() section but never re-caps the combined context, so it exceeds the budget instead. Python and native diverge at exactly the boundary. Fixes: validate --adr up front (non-empty, resolves against the existing ADR-file set, refuse with exit 2 and no state write; dispatch on is-not-None); skill 3b treats a degradation marker in the judge output as no-verdict and aborts the sweep naming the backend problem; both hosts reserve the instruction length and truncate the candidate sections, so the instruction always survives and the total stays inside the budget.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 stamp llm --adr '' and --adr with an id not resolving to an existing ADR file are refused with exit 2 and provably write no state
- [x] #2 A valid per-ADR stamp still works and prune still removes entries for later-deleted files
- [x] #3 Skill step 3b does not stamp any verdict when the judge output carries a degradation marker, and says why the sweep aborted
- [x] #4 The R5 selection instruction survives truncation in both hosts and the combined context stays within MAX_CONTEXT in both
- [x] #5 python -m pytest -q passes; adapters --check clean; native exe rebuilt
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All four review findings fixed and tested. (1) Empty --adr refused with exit 2 before the dispatch that used to fall through to a tier stamp. (2) An id that does not resolve against the filename-derived ADR set (ADR-999, unpadded ADR-1) is refused with exit 2 and a zero-padding hint BEFORE any state write; the same existing-ids set still drives the prune, and a test proves entries for files deleted after their stamp still age out. (3) Guardian skill step 3b now treats a degradation marker in the judge output (DEGRADED to declarative-only / no LLM backend / LLM pass evaluated 0) as no-verdict: stamp nothing, abort the sweep, surface the judge's own --set-backend fix-it line - exit 0 alone is not proof the model judged. (4) Both hosts reserve the R5 instruction's length and truncate the CANDIDATES: Python via _prompt_candidates_context (tested: fat set stays <= MAX_CONTEXT_CHARS and ends with the instruction), Rust with saturating_sub and a char-boundary-safe truncate (titles carry em dashes), exe rebuilt per the README recipe after redoing a build that had added a non-recipe --edition flag. Nuance vs the reviewer's claim on (4): Rust did truncate per render() section; what it never capped was the combined context - both hosts were wrong in opposite directions. 5 new tests; guardian suite 48/48, hook suites 33/33, full suite 1761 passed / 12 skipped, exit code read directly. Adapters --check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
