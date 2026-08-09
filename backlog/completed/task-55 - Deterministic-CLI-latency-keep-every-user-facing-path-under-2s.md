---
id: TASK-55
title: 'Deterministic CLI latency: keep every user-facing path under 2s'
status: Done
assignee: []
created_date: '2026-07-26 08:45'
updated_date: '2026-07-26 10:21'
labels:
  - performance
  - cli
  - deterministic
dependencies: []
modified_files:
  - bin/adr-lint
  - bin/adr-retire
  - tests/fixtures/cli/latency-corpus.json
  - tests/test_cli_performance.py
priority: high
ordinal: 55500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Measurement pass over all deterministic adr-kit entry points (hooks, CLIs, MCP) found two paths that exceed the 2s user-wait goal, both from the same bug class: an un-memoized full-repo walk repeated once per ADR / per gate.

Baseline (Windows, Python 3.12.9, 16 ADRs, contaminated tree incl. 8 agent worktrees):
- adr-lint     p50 1496ms / p95 2032ms  -> OVER budget at p95
- adr-retire   p50 1869ms / p95 2607ms  -> OVER budget at p50 and p95
- native hooks 18-24ms, all within manifest budgets (not a problem)
- Python interpreter floor ~124ms per CLI spawn

Root causes:
1. bin/adr-retire `_walk_repo_files` is called once per ADR from `detect_tech_removal` (13 full os.walk passes; 2.789s of 3.2s profile).
2. bin/adr-lint `_gate_exists_locally` walks AND read_text()s up to 5000 files per gate needle (1662 reads x N gates).
3. bin/adr-lint `load_config` eagerly imports jsonschema (~257ms, ~17% of runtime) even when no schema validation is needed.
4. Neither tool prunes nested checkouts (.claude/worktrees/), so agent worktrees are scanned as if they were source.

Cost scales linearly with ADR count, so team repos degrade fastest — exactly the target audience.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Clean-tree and contaminated-tree baselines are both measured and recorded, not extrapolated
- [x] #2 adr-lint and adr-retire p95 are under 2000ms at 16, 50 and 100 ADRs, proven by a scaling measurement
- [x] #3 adr-retire performs one repo walk per run instead of one per ADR
- [x] #4 adr-lint gate detection is a single pass over files checking all needles, not O(gates x files) reads
- [ ] #5 jsonschema import in adr-lint is lazy so it is not paid when unused
- [x] #6 Nested checkouts are pruned via a .git-entry check rather than blanket-skipping .claude
- [x] #7 A CLI latency budget fixture lands in tests/fixtures alongside reference-corpus.json so the 2s goal stays enforced
- [x] #8 Existing test suite passes with no behavioural regression in lint or retire output
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Criterion #5 (lazy jsonschema): investigated and intentionally NOT changed. The import already sits inside load_config (lazy at module level); it is paid only when a .adr-kit.json exists, and it performs real validation that raises PolicyError on invalid config. Removing it would silently change detection behaviour for a fixed ~243ms cost that leaves adr-lint at 1.11s p50 even at 100 ADRs. Trade rejected: correctness over 243ms.

Criterion #8 (full suite): first full run after both fixes passed 872/5 skipped; confirmation re-run in flight at time of writing.

Evidence files: tests/fixtures/cli/latency-corpus.json (committed) + scratchpad bench_before-clean.json / bench_after-clean.json / scaling_before.json / scaling_after.json / bench_after_contaminated.json.

Confirmation run complete: 881 passed, 5 skipped (872 pre-existing + 9 new perf-regression tests), exit 0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed the O(ADRs x files) and O(gates x files) repeated-walk bugs in bin/adr-retire and bin/adr-lint, plus nested-checkout pruning (.git-entry check) in both scanners. Client mirrors (codex/, copilot/) synced.

Proof: adr-retire p95 2607ms -> 472ms on the contaminated tree, 5229ms -> 560ms at 100 ADRs (linear -> flat); adr-lint p95 2032ms -> 1278ms. Output byte-identical before/after on an unmodified clone; 881 tests passed, 5 skipped.

Guarded by tests/fixtures/cli/latency-corpus.json (2s budgets + measured evidence) and tests/test_cli_performance.py (9 tests: structural single-pass/memoization/nested-checkout guards + live 2s-ceiling smoke).

Criterion #5 (jsonschema) intentionally not changed: the import is already lazy and performs real config validation raising PolicyError; removing it would trade correctness for a fixed ~243ms.

Committed as d2d0ccc on fix/claude-hook-resilience.
<!-- SECTION:FINAL_SUMMARY:END -->
