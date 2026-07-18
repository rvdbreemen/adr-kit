---
id: TASK-32.2
title: Bound regex execution and align generated validators
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 20:05'
labels:
  - security
  - regex
  - validators
  - F-01
  - F-10
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
modified_files:
  - bin/adr_regex.py
  - bin/adr_regex_worker.py
  - bin/adr-judge
  - bin/adr-generate-scripts
  - tests/test_adr_regex_safety.py
  - tests/test_adr_generate_scripts.py
parent_task_id: TASK-32
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resolve source-audit F-01 and F-10 by making policy regex evaluation killable and bounded, and by defining and testing generated-validator enforcement semantics without unsafe direct searches or silent rule loss.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Catastrophic regular expressions cannot hang judge, hooks, CI, MCP calls, or generated Python validators.
- [x] #2 Regex execution has deterministic input and wall-clock budgets with actionable timeout findings.
- [x] #3 Generated validators preserve supported scope and require semantics or explicitly reject unsupported compilation with machine-readable capability metadata.
- [x] #4 Catastrophic-pattern and judge/generated-validator parity tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce catastrophic backtracking through judge and generated validators.
2. Introduce one stdlib, killable subprocess regex helper with explicit input and wall-clock budgets.
3. Route judge declarative matching through the helper and return actionable timeout findings.
4. Make generated Python and shell validator output preserve path scope and require rules where safe, or reject unsupported compilation explicitly instead of silently dropping semantics.
5. Add parity/capability tests and run focused performance and security suites.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Replaced the in-process daemon-thread timeout with a persistent isolated Python worker. The parent enforces 1s wall-clock, 2 MiB input, and 4096-character pattern budgets and kills/restarts a stuck worker. Timeout, worker failure, or budget exhaustion now produces a violation so the enforcement floor fails closed.

Generated Python validators now evaluate each unscoped forbid/import/require regex in a killable subprocess with the same fixed timeout and input budget. Generated shell validators are thin Python launchers, eliminating POSIX ERE drift. `require_pattern` is preserved. `path_glob` and `llm_judge`, which cannot be preserved by a stdin-only standalone validator, now cause exit 2 and a versioned `capabilities.json` instead of silent semantic loss.

Verification: 43 judge/security/performance tests passed after worker integration; final regex/generator slice passed 22 tests with 2 platform skips. Regressions prove catastrophic backtracking is killed, judge fails closed, worker restart succeeds, generated validators time out safely, require rules work, and scoped/LLM rules are rejected explicitly.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved F-01 and F-10. Repository-authored regexes can no longer hold the judge process GIL indefinitely, safety-budget failures block rather than advise, and generated validators either preserve deterministic unscoped forbid/import/require semantics with bounded Python regex behavior or explicitly refuse unsupported scoped/LLM compilation through machine-readable capabilities.
<!-- SECTION:FINAL_SUMMARY:END -->
