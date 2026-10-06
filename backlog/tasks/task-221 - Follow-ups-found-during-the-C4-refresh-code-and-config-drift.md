---
id: TASK-221
title: Follow-ups found during the C4 refresh (code and config drift)
status: Done
assignee: []
created_date: '2026-10-06 12:44'
updated_date: '2026-10-06 19:38'
labels:
  - bug
  - tech-debt
dependencies: []
priority: medium
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Findings from the TASK-219 C4 revision that need code or config changes rather than documentation. Each was reported by a revision pass reading the code at v0.59.1; verify each before fixing (repo rule: reproduce the premise first). (1) adr-substance calls the host model via adr_llm but reads neither ADR_KIT_NO_LLM nor judge.llm_enabled, so the global LLM switch does not cover it. (2) ADR-017 is Superseded, so its two forbid_pattern rules are no longer enforced (the judge reads only Accepted ADRs), and its successor ADR-036 has no Enforcement section. (3) tests/fixtures/cli/latency-corpus.json still budgets the retired adr-embed and adr-context-vector, and excludes adr-watch as long-running although every mode exits; test_cli_corpus_coverage checks 'excluded' against bin/ but not 'budgets'. (4) adr-suggest's timeout constant is 30 s while the schema suggest.llm_timeout_seconds default and the --llm-timeout help say 120. (5) The shipped scripts subset is not import-closed: client_certification.py:153 imports client_support_matrix, which public-artifacts.json does not ship. (6) client_generation.py:72,144 still mentions prebuilt native hooks under hooks/bin/ and keeps a dead .exe/.dll branch. (7) clients/capabilities.json lists codex/hooks/hooks.json and copilot/hooks.json as hand_authored_validated although the generator writes both. (8) bin/adr-doctor:123 --deep help still says 'native, MCP, and model probes'; adr_doctor_core.run_audit runs adr-discover (misnamed). (9) templates/github-workflows/adr-judge.yml and adr-index-check.yml pin @main. (10) release_phases.py comments say phase 4/5 where step labels say 3/4. (11) pytest.ini still says slow tests are skipped in fast CI; tests/test_adr_index.py:573 dates the size-budget change to 0.55.0 while CHANGELOG says 0.55.1; tests/test_open_questions_append_only.py:95 mentions bin/adr-embed. (12) templates/adr-kit-guide.md:304, ADR-004 and adr-context's docstring still call adr-watch the wired edit tier / '5 weighted signals'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each numbered item verified, then fixed or closed with the reason it does not hold
- [x] #2 Items that change behaviour (1, 2, 5) get a test that failed before the fix
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Each item verified before fixing (repo rule). (1) CONFIRMED and wider: adr-suggest also ignored ADR_KIT_NO_LLM, and the pre-commit hook ran it under the switch; fixed in adr_llm.resolve_llm_backend (switch outranks --llm-cmd/ADR_KIT_LLM_CMD), tests/test_llm_kill_switch.py red->green with controls. (2) CONFIRMED: ADR-017's two forbid_patterns (no pinned --model claude, no DEFAULT_LLM_CMD) lapsed when it was superseded; ADR-036 has no Enforcement section. OPEN: needs a maintainer decision because it changes an Accepted ADR's enforcement. (3) CONFIRMED: stale embed/vector budget rows removed, adr-watch budgeted (measured ~189 ms --help, 300 ms like adr-status) instead of the false 'long-running' exclusion; new test rejects budget rows not in bin/ (red->green). (4) PARTLY: the 30 s default is deliberate (TASK-122); help text and schema (description and default) corrected to 30. (5) CONFIRMED in the installed 0.59.1 payload: build-client-adapters.py and sync-agent-plugins.py died with ModuleNotFoundError; client_support_matrix.py added to the allowlist, closure test red->green. (6) CONFIRMED: dead .exe/.dll branch and native-binary docstring removed. (7) CONFIRMED: the three hooks.json files moved to ownership.generated; C4 container/contracts updated. (8) PARTLY: 'native' in --deep help means native registration (current); only the model probe was stale; help, claude.md, TROUBLESHOOTING and README corrected; run_audit renamed run_discover. (9) CONFIRMED: adr-judge/adr-index-check templates and two readiness doc examples pinned to v0.59.1 and registered as version sites; install-smoke note updated. (10) CONFIRMED: phase comments now use the step numbers the driver prints. (11) pytest.ini marker text fixed; test comment corrected to 0.55.1 (git puts the commit in v0.55.0 only because that tag was misplaced on the dev tip, ADR-042); the bin/adr-embed mention in test_open_questions_append_only is fixture ADR text, not a claim, left as is. (12) CONFIRMED for the user-facing guide template and adr-context's docstring, both fixed; ADR-004 is a historical decision record, left as is. Full suite 1975 passed / 12 skipped (two foreground halves).

Item 2 resolved by the maintainer's choice B: new ADR-043 (Accepted 2026-10-06 after explicit confirmation) carries ADR-017's two forbid_pattern rules, widened to adr-substance, with gate adr-no-pinned-model-v1 (tests/test_no_pinned_model_gate.py: every file that resolves an LLM backend must be in scope). Verified live: a pinned --model claude-sonnet-4-6 appended to bin/adr-substance made adr-judge report 'VIOLATION ADR-043 forbid_pattern bin/adr-substance:312' and exit 1. ADR-036 linked both ways via bin/adr relate.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All twelve drift items from the C4 refresh closed. Eleven fixed in PR #187 (merged 1bbad8a, 14/14 CI): ADR_KIT_NO_LLM now stops every model call; the installed payload ships client_support_matrix.py (build-client-adapters and sync-agent-plugins no longer crash); workflow templates and examples pinned to a release as version sites; latency corpus cleaned with a stale-budget test; installed guide, help texts, schema, ownership and comments corrected. Item 2 resolved by ADR-043 (maintainer's option B), restoring the lapsed rules with a scope that follows the code.
<!-- SECTION:FINAL_SUMMARY:END -->
