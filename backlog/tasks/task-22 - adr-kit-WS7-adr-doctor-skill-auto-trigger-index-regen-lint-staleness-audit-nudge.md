---
id: TASK-22
title: >-
  adr-kit WS7: 'adr doctor' + skill auto-trigger (index regen, lint,
  staleness/audit nudge)
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:30'
labels:
  - adr-kit
  - governance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Whenever ADR skills run, check whether the index needs regenerating and whether an audit is warranted, and act. adr doctor = lint + index --check + staleness: (a) Proposed whose verified_in resolves (shipped-but-unaccepted), (b) Proposed older than N days, (c) Accepted whose verified_in files changed since acceptance (code-drift, e.g. ADR-160/147), (d) named-but-absent ADR-080 gates. Skill/adr-generator runs doctor at START and index+lint at END; material drift auto-triggers an audit. Full plan: docs/plan/adr-kit-governance-plan.md. Repo: adr-kit + skills.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 adr doctor reports the four staleness classes plus index/lint status
- [x] #2 ADR skill/adr-generator runs doctor at start and index+lint at end, auto-fixing the index
- [x] #3 A shipped-but-Proposed ADR is surfaced as a fast-path candidate
- [x] #4 Material drift auto-triggers an audit pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation plan for TASK-22:
1. Add a stdlib-only bin/adr-doctor CLI that runs local checks: adr-lint --strict, adr-index --check, and staleness/audit-nudge analysis over canonical frontmatter.
2. Report the four staleness classes: Proposed with resolving verified_in (shipped-but-unaccepted), Proposed older than a configurable threshold, Accepted ADRs whose verified_in file evidence changed after acceptance, and named-but-absent gates via strict lint findings.
3. Add --fix-index so doctor can regenerate the generated index before rechecking; keep JSON and text output for agents/CI.
4. Update ADR skill and adr-generator agent instructions: run doctor at start; run adr-index + adr-lint/doctor at end, allowing index auto-fix.
5. Add tests for doctor index stale detection/fix, shipped-but-Proposed detection, old Proposed detection, changed evidence detection, and missing gate surfaced through strict lint.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1011 because this is adr-kit repo work.

Implemented adr-doctor as a local stdlib-only health check: it runs adr-index --check, adr-lint --strict, and frontmatter-based staleness analysis. Findings cover shipped-but-Proposed ADRs, old Proposed ADRs, Accepted ADRs whose verified_in evidence changed after acceptance, and missing named gates surfaced by strict lint. --fix-index regenerates docs/adr/README.md before checking.

Material drift now auto-triggers a local read-only adr-audit --root pass and includes the audit summary in doctor JSON/text output. The ADR skill, adr-generator agent, and README now instruct agents to run doctor at start/end and to refresh the generated index via adr-index instead of hand-editing it.

Verification:
- python -m pytest tests/test_adr_doctor.py -q -> 5 passed
- python -m pytest tests/test_adr_doctor.py tests/test_adr_auto_accept.py tests/test_adr_lifecycle.py tests/test_adr_index.py tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_lint_governance.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 80 passed
- python bin/adr-doctor --fix-index docs/adr -> index_ok=True lint_ok=True findings=0
- python bin/adr-doctor --fix-index --format json docs/adr -> index_ok=true, lint_ok=true, findings=0, audit.triggered=false
- python bin/adr-index --check docs/adr -> ADRs=3, duplicates=0, changed=False
- python bin/adr-lint --strict docs/adr -> PASS strictly 3, FAIL 0
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Done. TASK-22 adds bin/adr-doctor, tests all required staleness/index/lint paths, auto-runs a local audit pass on material drift, and wires the doctor/index/lint workflow into the ADR skill, adr-generator agent, and README.
<!-- SECTION:FINAL_SUMMARY:END -->
