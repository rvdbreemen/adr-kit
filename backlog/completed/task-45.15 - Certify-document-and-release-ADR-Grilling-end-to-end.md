---
id: TASK-45.15
title: 'Certify, document and release ADR Grilling end to end'
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-20 19:53'
updated_date: '2026-07-20 23:11'
labels:
  - feature
  - adr-grilling
  - certification
  - release
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.6
  - TASK-45.9
  - TASK-45.10
  - TASK-45.11
  - TASK-45.12
  - TASK-45.13
  - TASK-45.14
documentation:
  - docs/feature-adr-grilling/README.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
  - docs/feature-adr-grilling/06-benchmark-report.md
  - docs/feature-adr-grilling/07-final-certification.md
modified_files:
  - .github/actions/adr-readiness/action.yml
  - .github/workflows/adr-readiness.yml
  - .github/workflows/validate.yml
  - README.md
  - INSTALL.md
  - CHANGELOG.md
  - bin/adr_doctor_probes.py
  - clients/installer/payload.py
  - clients/workflows.json
  - docs/feature-adr-grilling/README.md
  - docs/feature-adr-grilling/06-benchmark-report.md
  - docs/feature-adr-grilling/07-final-certification.md
  - docs/feature-adr-grilling/task-map.md
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
  - tests/test_client_adapter_generation.py
  - tests/test_client_doctor.py
  - tests/test_documentation_contracts.py
parent_task_id: TASK-45
priority: high
ordinal: 46500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Certify ADR Grilling as one coherent ADR Kit feature after every implementation branch is complete. Run cross-platform and cross-client end-to-end scenarios, deterministic-output checks, packaging and generated-artifact validation, hook and command benchmarks, upgrade testing, and release documentation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 End-to-end scenarios cover a new subject, PR and diff reconstruction, chat log or document reconstruction, Proposed resume, accept, reject, defer, supersede, shipped-but-Proposed, CI advisory, and CI block.
- [x] #2 The full test suite passes on every Python version and operating system supported by ADR Kit.
- [x] #3 All fifteen canonical workflows generate reproducible Claude, Codex, and Copilot artifacts and checked-in output matches generation.
- [x] #4 Clean client generation has p95 no greater than 2000 ms and maximum no greater than 5000 ms.
- [x] #5 Warm no-op client generation has p95 no greater than 500 ms, maximum no greater than 1000 ms, and writes zero files.
- [x] #6 No existing measured path regresses by more than 20 percent and every new readiness, linkage, MCP, hook, and CI budget passes.
- [x] #7 Every new executable and artifact is included in packaging, inventory, upgrade, and drift validation.
- [x] #8 Strict lint, index, related, lifecycle, MCP, hook, packaging, deterministic permutation, and security regression suites pass.
- [x] #9 User documentation contains a complete Proposed-to-Accepted interaction and the upgrade guide explains the implicit auto to assist default change.
- [x] #10 The parent epic records the exact certification commands, environment, results, compatibility conclusion, and release evidence.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Expand and validate the end-to-end scenario matrix across authoring, reconstruction, lifecycle, guardian, hooks and CI. 2. Regenerate all client artifacts and certify clean plus warm no-op generation budgets. 3. Run the complete local regression, strict ADR/index/related checks, packaging allowlist/inventory, deterministic generation and security suites. 4. Record platform/Python scope honestly, finalize benchmark/release/user documentation, then close the epic only if every local release gate is green.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Certification environment: Windows 11 10.0.26200, CPython 3.12.9 and Python 3.10 via uv. Windows is the ADR-010 required native baseline; Linux/macOS are best-effort. `.github/workflows/validate.yml` now enforces the full suite on ubuntu-latest, macos-latest and windows-latest for Python 3.10 and 3.12 when the branch is pushed or a PR is opened.

Exact full-suite evidence: `python -m pytest -q` -> 821 passed, 6 skipped in 398.57s after the final doctor contract fix. `uv run --python 3.10 --with pytest python -m pytest -q` -> 820 passed, 6 skipped in 381.82s; the post-fix Python 3.10 doctor regression `uv run --python 3.10 --with pytest python -m pytest tests/test_client_doctor.py -q` -> 11 passed.

Final release checks: `python scripts/build-client-adapters.py --check` -> changed=0, written=0; focused doctor/documentation/packaging/client/CI suite -> 52 passed; Markdown lint -> 0 issues; `python bin/adr-lint --strict docs/adr` -> 11 PASS and no findings; `python bin/adr-index --check docs/adr` -> unchanged; ADR-011 related/readiness checks passed; `git diff --check` passed.

Deep doctor exposed and drove a fix for its stale four-tool MCP expectation. The final deep check reports healthy generated adapters, a healthy live five-tool handshake, zero required failures and zero ADR findings. Remaining degraded observations are optional machine-local Claude trust, local-model/project-guidance configuration, and five-sample hook variance; the authoritative 30-sample hook benchmark passes.

Performance: clean client generation p95 896.896ms/max 925.082ms; warm no-op p95 128.694ms/max 141.799ms with zero reads/writes. Versus approved references clean is 10.31% faster and warm 14.20% faster. Readiness core p95 66.246ms, linkage p95 150.444ms, persistent MCP p95 336.830ms, CI action p95 1150.890ms, and signal p95 616.388ms; every absolute and regression budget passed.

Compatibility conclusion: all 15 canonical workflows reproduce across checked-in Claude, Codex and Copilot artifacts. No model, network service, API key or secret is used by readiness, hooks, or CI. Remote six-job OS/Python matrix execution is deliberately left to the branch/PR CI trigger and is not represented as a local pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Certified ADR Grilling end to end. The feature now covers subject-based authoring, PR/diff and chat/document reconstruction, resumable one-question grilling, explicit accept/reject/defer/supersede outcomes, guardian work queues, bounded hook/pre-commit advice, and a deterministic PR readiness action that blocks only explicit implementations of Proposed ADRs. All release-required Windows regressions and 30-sample performance budgets pass, generated three-client artifacts are drift-free, packaging and documentation are complete, and the full six-combination Python/OS CI matrix is enforced for pushed commits and pull requests.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All upstream dependencies are Done before certification begins.
- [x] #2 The final benchmark report includes environment, fixture sizes, p50, p95, maximum, sample count, baseline comparison, and pass or fail for every budget.
- [x] #3 Release documentation, modified files, exact validation commands, and final summary are complete.
<!-- DOD:END -->
