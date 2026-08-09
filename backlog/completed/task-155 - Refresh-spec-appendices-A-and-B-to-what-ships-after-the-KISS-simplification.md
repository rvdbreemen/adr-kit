---
id: TASK-155
title: Refresh spec appendices A and B to what ships after the KISS simplification
status: Done
assignee: []
created_date: '2026-08-09 13:22'
updated_date: '2026-08-09 13:26'
labels: []
dependencies: []
references:
  - docs/plans/kiss-simplification-plan.md
priority: medium
ordinal: 122500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Cleanup after TASK-143..150 and the ADR-035 default flip. Appendix A is a dated inventory (2026-08-04) whose claims have drifted: the plan-exit budget reads 100 ms where the manifest says 1800 ms; A.2 and A.4 call adr-suggest opt-in while ADR-035 turned it on by default; A.4's closing asymmetry (an unrecorded decision survives by default) predates plan-exit naming candidates (TASK-150) and the default-on suggest pass. Appendix B still lists B1 (delivered by TASK-150) and B3 (delivered: validate.yml lints docs/adr at PR time, per A.3's own row) as open proposals. Re-date the inventory to 2026-08-09, correct the rows, mark B1 and B3 delivered, keep B2/B4/B5 honest.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Appendix A carries the 2026-08-09 date and no claim contradicted by hooks/manifest.json or the shipped defaults
- [ ] #2 Appendix B marks B1 and B3 delivered with the task ids; B2, B4 and B5 remain honest proposals
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Appendix A re-dated to 2026-08-09; plan-exit row corrected (1.8 s budget, names decision-shaped lines per TASK-150); A.2 and A.4 no longer call adr-suggest opt-in (ADR-035 default flip); A.4's closing asymmetry rewritten: four unprompted authoring moments now exist, advisory by design, with the whole-branch view (B2) the remaining on-request gap. Appendix B marks B1 and B3 delivered with task ids; B4 points at TASK-156. Full suite 1746 passed, 14 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
