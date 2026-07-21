---
id: TASK-45
title: 'EPIC: Grilling for ADRs across the complete ADR lifecycle'
status: Done
assignee: []
created_date: '2026-07-20 19:50'
updated_date: '2026-07-20 23:15'
labels:
  - feature
  - adr-grilling
  - adr-lifecycle
  - agentic-coding
milestone: ADR Grilling
dependencies: []
references:
  - 'https://www.aihero.dev/grill-with-docs'
  - 'https://www.aihero.dev/skills-grilling'
documentation:
  - docs/feature-adr-grilling/README.md
  - docs/feature-adr-grilling/01-research.md
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
  - docs/feature-adr-grilling/task-map.md
  - docs/feature-adr-grilling/06-benchmark-report.md
  - docs/feature-adr-grilling/07-final-certification.md
  - >-
    docs/adr/ADR-011-adopt-deterministic-readiness-and-human-gated-grilling-across-the-adr-lifecycle.md
  - docs/adr-grilling.md
modified_files:
  - .github/actions/adr-readiness/action.yml
  - .github/workflows/adr-readiness.yml
  - .github/workflows/validate.yml
  - README.md
  - INSTALL.md
  - CHANGELOG.md
  - bin/adr
  - bin/adr-readiness
  - bin/adr-readiness-ci
  - bin/adr-grill-signal
  - bin/adr_readiness.py
  - bin/adr_readiness_ci.py
  - bin/adr_grill_signal.py
  - bin/adr_guardian_queue.py
  - bin/adr_doctor_probes.py
  - bin/adr-mcp
  - clients/workflows.json
  - clients/installer/payload.py
  - skills/grill/SKILL.md
  - skills/adr/SKILL.md
  - skills/init/SKILL.md
  - skills/review/SKILL.md
  - skills/judge/SKILL.md
  - skills/guardian/SKILL.md
  - skills/supersede/SKILL.md
  - skills/retire/SKILL.md
  - schemas/adr-readiness.schema.json
  - templates/github-workflows/adr-readiness.yml
  - templates/githooks/pre-commit
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - >-
    docs/adr/ADR-011-adopt-deterministic-readiness-and-human-gated-grilling-across-the-adr-lifecycle.md
  - docs/feature-adr-grilling
  - packaging/client-generation-benchmark.json
  - packaging/executables.json
  - packaging/public-artifacts.json
  - scripts/benchmark-adr-grilling.py
  - scripts/client_generation.py
  - scripts/client_generation_state.py
  - tests/fixtures/grill
  - tests/test_adr_grill_integrations.py
  - tests/test_adr_grill_signal.py
  - tests/test_adr_grill_workflow.py
  - tests/test_adr_guardian_queue.py
  - tests/test_adr_open_questions.py
  - tests/test_adr_readiness.py
  - tests/test_adr_readiness_ci.py
  - tests/test_adr_mcp.py
  - tests/test_client_adapter_generation.py
  - tests/test_client_doctor.py
priority: high
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend ADR Kit with an interactive grilling layer for creating, reconstructing, reviewing, completing, and revalidating Architecture Decision Records. Deterministic repository analysis establishes facts and readiness; the engineer or architect remains the decision maker. Grilling may prepare a Proposed ADR for acceptance but cannot bypass adr accept, the lifecycle rules, or the four verification gates. Hooks, MCP readiness, and CI remain deterministic and model-free.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All fifteen child tasks are Done with task-level validation evidence.
- [x] #2 New ADRs can be guided interactively from a subject to an explicitly confirmed lifecycle outcome.
- [x] #3 Code, pull requests, diffs, chat logs, and documents can serve as evidence for a Proposed ADR without being trusted as workflow instructions.
- [x] #4 No agent, MCP tool, hook, or CI job can accept an ADR without same-session human confirmation followed by adr accept.
- [x] #5 Accepted ADRs cannot contain unresolved open questions.
- [x] #6 Only a deterministically linked and implemented Proposed ADR can fail the new CI readiness gate; suspected undocumented decisions remain advisory.
- [x] #7 Readiness analysis is read-only, stably ordered, and reproducible for the same repository, arguments, and injected date.
- [x] #8 Hooks and CI require no model, network service, API key, or secret.
- [x] #9 Existing lint, evidence, quality, consistency, lifecycle, hook, packaging, and performance guarantees remain authoritative.
- [x] #10 All supported clients expose semantically equivalent workflows and all documentation, benchmarks, and release evidence are complete.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation started on branch dev. Work will proceed topologically through TASK-45.1 to TASK-45.15; no child or epic will be completed without its required functional, deterministic, performance, and regression evidence.

Released behavior: ADR Kit now has a deterministic readiness model and CLI/MCP surface, semantic Open Questions across supported profiles, explicit implementation linkage, a canonical one-question grill, adaptive reconstruction, lifecycle integrations, an active Proposed queue, bounded hook/pre-commit signals, and a key-free GitHub readiness action. Human confirmation plus `adr accept` remains the only acceptance path.

Exact certification commands and results: `python -m pytest -q` on CPython 3.12.9 -> 821 passed, 6 skipped in 398.57s; `uv run --python 3.10 --with pytest python -m pytest -q` -> 820 passed, 6 skipped in 381.82s; post-fix Python 3.10 doctor tests -> 11 passed; final focused release slice -> 52 passed. `python bin/adr-lint --strict docs/adr` -> 11 PASS; `python bin/adr-index --check docs/adr` -> unchanged; ADR-011 related/readiness -> valid/Accepted with no findings; generation check -> 0 changed/0 written; Markdown lint and `git diff --check` -> clean.

Performance evidence, 30 samples on Windows 11 10.0.26200 / CPython 3.12.9: clean generation p95 896.896ms/max 925.082ms; warm p95 128.694ms/max 141.799ms/zero reads and writes; readiness core p95 66.246ms; 500-path linkage p95 150.444ms; MCP p95 336.830ms; CI action p95 1150.890ms; signal p95 616.388ms. Existing paths remain within 20% regression and all new budgets pass.

Compatibility impact: 15 canonical workflows generate reproducibly for Claude, Codex and Copilot. The after-the-fact default changes from implicit `auto` to `assist`; explicit legacy `auto` remains available. The full regression suite is now mandatory in CI on Python 3.10/3.12 across Windows, Linux and macOS. Windows remains the required native certification baseline under ADR-010; remote Linux/macOS execution is best-effort and awaits the normal pushed-branch/PR run.

Release evidence: ADR-011 is Accepted; the research/design/implementation/validation/benchmark/final-certification dossier is under `docs/feature-adr-grilling`; packaging inventories include all new engines, schema, workflow, action and templates; live deep doctor has a healthy five-tool MCP handshake, zero required failures and zero ADR findings.

Explicitly deferred: no functional TASK-45 scope remains. Remote Linux/macOS matrix results are deferred to the first pushed dev branch or pull request because the current certification was performed on an uncommitted Windows working tree. Optional local model selection, generated per-project guidance, and Claude plugin trust are operator environment configuration, not feature blockers.

Post-certification documentation follow-up TASK-46 is Done. It added the public `docs/adr-grilling.md` runnable lifecycle guide, corrected INSTALL to the five-tool MCP contract, cross-linked all client and release docs, and passed Markdown plus documentation/packaging validation. No TASK-45 implementation behavior changed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed all fifteen ADR Grilling subtasks and certified the epic. ADR Kit can now guide and reconstruct decisions interactively while preserving deterministic facts, read-only readiness, explicit human lifecycle authority, four-gate acceptance, model-free hooks/CI, reproducible three-client artifacts, packaging integrity and established performance budgets. The implementation and evidence are complete in the dev working tree; only the normal remote multi-OS CI execution remains for the subsequent push/PR lifecycle.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Every child task is Done and its exact validation commands and results are recorded.
- [x] #2 The full regression, end-to-end, deterministic-output, packaging, client-generation, and performance certification suites pass.
- [x] #3 The final Backlog notes identify the released behavior, compatibility impact, measured budgets, and remaining explicitly deferred work.
<!-- DOD:END -->
