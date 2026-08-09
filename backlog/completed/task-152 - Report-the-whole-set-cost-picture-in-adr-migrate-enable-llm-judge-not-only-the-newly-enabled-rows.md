---
id: TASK-152
title: >-
  Report the whole-set cost picture in adr-migrate --enable-llm-judge, not only
  the newly enabled rows
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 08:10'
updated_date: '2026-08-09 08:28'
labels:
  - bug
  - migrate
dependencies: []
priority: high
ordinal: 115500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The dry-run and apply output of --enable-llm-judge lists unbounded_scope only for ADRs the migration flips. ADRs already enabled (which since TASK-74 includes every Enforcement block without an explicit llm_judge key) are invisible. Observed 2026-08-09 on OTGW-firmware otgw-1.x.x: the scan reported '6 enabled, 0 unbounded' while 58 already-enabled unscoped ADRs were active, so the operator read the migration as cost-free and the pre-commit judge then took ~20s per unscoped ADR on every commit (68 judged ADRs, 64 unscoped, measured 20-28s per call). The result must carry set-wide totals: how many ADRs the LLM pass will judge after this migration, and how many of those declare no path_glob.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 JSON result gains a summary object with total judged and total unbounded after the migration
- [x] #2 Text output prints the same two totals
- [x] #3 Dry-run and apply agree on the numbers
- [x] #4 Unit test covers a repo where already-enabled unscoped ADRs dominate the newly enabled ones
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
adr-migrate --enable-llm-judge now reports the whole-set cost picture. apply() gains a summary object {judged_after, unbounded_after} counting every ADR the LLM pass will evaluate after the migration (already-enabled plus newly enabled, minus opt-outs); the CLI prints the two totals plus a cost hint when unscoped ADRs exist, in dry-run and apply alike. Reproduced first: a repo with 4 already-enabled unscoped ADRs and 1 legacy-off reported 'would enable: 1 ADR(s)' with no set context; it now adds 'would judge: 5 ADR(s), 4 without any path_glob'. Two tests added (module summary incl. opt-out effect; CLI text+json), module suite 15/15, full suite 1875 passed / 13 skipped in 10:19. Adapters regenerated, --check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
