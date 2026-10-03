---
id: TASK-213
title: Small follow-ups from the 2026-10-03 backlog sweep
status: Done
assignee: []
created_date: '2026-10-03 15:52'
updated_date: '2026-10-03 20:38'
labels:
  - chore
dependencies: []
priority: low
type: chore
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Side findings recorded while working TASK-191..211. None is fixed; each needs its premise checked first.
1. skills/lint/SKILL.md refers to output of the deterministic CLI, but allowed-tools is Read/Glob/Grep, so the skill never runs it. A model that tries Bash meets a permission prompt.
2. This repository's .githooks/pre-commit lags templates/githooks/pre-commit in comment text: backend selection versus ADR-036, and suggest opt-in versus ADR-035. The version registry syncs only the stamp.
3. Something in the full pytest run writes into codex/ and copilot/: they showed as modified before an adapter regeneration that reported written=0.
4. `bin/adr answer` rewrites a CRLF file to LF, like the other lifecycle writers.
5. .githooks/pre-commit runs adr-judge without its own timeout; the LLM pass ceiling from TASK-210 now bounds it, but the declarative pass is not bounded there.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Resolved 2026-10-03, item by item.

1. Lint skill: allowed-tools now include Bash. A new section runs `bin/adr-lint --format json` first and uses the gate text to explain its findings and the heuristic calls; it falls back to reading files only when the CLI cannot run.

2. Dogfood copies: setup-project refreshed .githooks/pre-commit and .adr-kit/ADR-guide.md, which had fallen behind again, to 0.57.0, because the 0.58.0 bump moves only the source. .adr-kit/ADR-guide.md is now a declared version site (bump-version fixture extended), and test_this_repositorys_dogfood_copies_match_their_source keeps both copies byte-equal to their source.

3. Reproduced with a probe line in bin/adr-lint plus the full suite: codex/ and copilot/ were rewritten at 22:21:14, inside test_doctor_detects_stale_index_and_fix_index_cleans_it. Cause: adr-doctor in repair mode calls generate(plugin_root, check=False) on the tree it runs from, which is this checkout (bin/adr_doctor_checks.py _generated_check). Fix: when plugin_root is a git checkout, report the adapters stale with the build command instead of rewriting them; installed payloads keep the repair. New test pins it. Doctor tests: 13 passed.

4. bin/adr _atomic_write_text keeps CRLF when the existing file uses it; test_answering_keeps_a_crlf_file_crlf. Lifecycle suites: 132 passed.

5. No change, by reasoning. .githooks/pre-commit runs adr-judge, which is now bounded: the LLM pass by judge.llm_pass_timeout_seconds (TASK-210), each declarative regex by the isolated worker's 1 s budget, and the file set by the staged diff. A shell `timeout` in the hook is not available on stock macOS.

6. release.py preflight accepts a dirty tree only when the version is already everywhere and every changed path is a declared version site or under codex/ or copilot/; otherwise it names the stray files. Three tests. release_phases.py is at 355 of 400 lines.

Broad set (release, bump, artifacts, answer, lifecycle, docs, adapters, allowlist, installer, setup, packaging): 236 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All six follow-ups are resolved. The lint skill runs its CLI. The dogfood guide and hook are refreshed and guarded by a test, and the guide stamp is a declared version site. adr-doctor no longer rewrites a source checkout's adapters; that was the test-suite writer into codex/ and copilot/, reproduced and fixed. Lifecycle writes keep CRLF. The hook timeout needs no change, since adr-judge is bounded end to end. release.py's preflight lets the prepared release continue.
<!-- SECTION:FINAL_SUMMARY:END -->
