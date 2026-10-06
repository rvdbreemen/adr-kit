---
id: TASK-221
title: Follow-ups found during the C4 refresh (code and config drift)
status: To Do
assignee: []
created_date: '2026-10-06 12:44'
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
- [ ] #1 Each numbered item verified, then fixed or closed with the reason it does not hold
- [ ] #2 Items that change behaviour (1, 2, 5) get a test that failed before the fix
<!-- AC:END -->
