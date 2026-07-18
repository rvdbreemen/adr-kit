---
id: TASK-25
title: Perform multi-perspective source review and refresh public documentation
status: Done
assignee:
  - Codex
created_date: '2026-07-18 15:06'
updated_date: '2026-07-18 16:28'
labels:
  - review
  - documentation
dependencies: []
documentation:
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - CONTRIBUTING.md
  - SECURITY.md
  - ROADMAP.md
  - CHANGELOG.md
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
  - docs/adr/README.md
modified_files:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - CONTRIBUTING.md
  - SECURITY.md
  - ROADMAP.md
  - CHANGELOG.md
  - CLAUDE.md
  - .github/ISSUE_TEMPLATE/bug.yml
  - .github/workflows/validate.yml
  - templates/
  - skills/
  - agents/adr-generator.md
  - examples/
  - tests/test_documentation_contracts.py
  - tests/test_python_compatibility.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Review the complete adr-kit repository across core correctness, security/fail-open behavior, cross-platform packaging and installation, tests/CI, ADR governance, and user-facing documentation. Consolidate reproducible findings, then update README and supporting documentation so they accurately describe the current implementation, development verification workflow, and any confirmed constraints. This is a review-and-documentation task; source-code fixes discovered during review require explicit scope confirmation unless they are necessary to keep the requested documentation truthful.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The whole repository is reviewed from at least three independent technical perspectives, including cross-file interactions beyond the current branch diff.
- [x] #2 Every reported source finding is reproduced or supported by precise code and test evidence and is prioritized by impact.
- [x] #3 README.md and relevant supporting documentation accurately describe the current architecture, supported client payloads, development verification workflow, and confirmed limitations.
- [x] #4 Generated ADR indexes are updated only through repository tooling and all documentation changes pass the applicable lint and consistency checks.
- [x] #5 Focused checks and the broadest practical test suite are run, with failures and environment-specific behavior recorded clearly.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Read the relevant Accepted ADRs and preserve their constraints during review and documentation changes.
2. Run three independent, read-only review tracks in parallel: (a) core CLI correctness, security, state mutation, and fail-open behavior; (b) cross-platform packaging, installers, generated payloads, and release/version contracts; (c) tests, CI, performance gates, public documentation, and ADR-governance consistency.
3. Independently reproduce candidate findings in the primary workspace, inspect cross-file interactions, and prioritize only evidence-backed defects.
4. Write a durable review artifact under docs/reviews/ and update README.md, INSTALL.md, and CONTRIBUTING.md where confirmed implementation behavior or developer workflow is missing or inaccurate. Do not manually edit generated ADR indexes.
5. Run focused regression checks, payload consistency checks, ADR doctor/lint/index checks, documentation checks, and the broadest practical pytest suite.
6. Update acceptance criteria, implementation notes, modified files, and final summary in TASK-25; mark Done only when documentation and verification match the actual repository state.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by the user on 2026-07-18. Source-code fixes are outside the initial review/documentation scope unless required to keep the requested documentation truthful; confirmed defects will be reported with follow-up options.

Paused on 2026-07-18 before documentation edits when the user introduced a higher-priority architecture change: selectable ADR template formats with research-driven agent-friendly default. Read-only review evidence remains available, but no README or documentation files were changed. Resume after the format initiative establishes the new documentation contract.

Resumed after TASK-26 established the final selectable-format and documentation contract. Reconciled the review artifact with subsequent remediation and current verification evidence; final documentation and task-state checks are in progress.

Final reconciliation completed after TASK-26. The durable audit contains 20 prioritized, evidence-backed findings across core enforcement/lifecycle, packaging/portability, and quality/documentation perspectives, and now distinguishes baseline v0.33 behavior from subsequent TASK-26 remediation. Public docs describe the current three-client architecture, Python 3.10 floor, selectable profiles, verification workflow, and remaining security/packaging limitations. Verification: 555 passed, 3 skipped (558 collected); focused documentation/profile/client/runtime slice 42 passed; 64 applicable Markdown files lint clean; all five ADRs strict-lint clean; doctor zero findings; both generated indexes current; payload sync check passed; git diff check had only expected checkout EOL warnings.

Post-completion clarification requested by the user: README.md, INSTALL.md, and INSTALL-AGENT.md now explain why MADR is the default. The text states that no authoritative global format census exists; MADR was selected for agent reliability (4.52/5 in adr-kit's weighted evaluation), while Nygard remains the concise/tooling option and canonical remains the compatibility option. A documentation contract test preserves this explanation.

Extended the template-choice rationale into the installed project guide and synchronized Codex/Copilot copies. CHANGELOG now records the documentation clarification. Final focused verification: 21 documentation/profile tests passed, payload sync check passed, and all 8 affected Markdown files lint clean.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Codex
created: 2026-07-18 15:54
---
Completed the three-perspective read-only source audit and drafted `docs/reviews/2026-07-18-source-audit/FINDINGS.md` with 20 prioritized findings. A draft README/supporting-doc refresh and documentation contract tests are present in the shared working tree. Final reconciliation, payload synchronization, broad verification, acceptance checks, and completion remain intentionally deferred because the user-approved TASK-26 format initiative is active and owns overlapping `templates/`, `README.md`, `INSTALL.md`, `ROADMAP.md`, client payloads, and tests. Do not treat TASK-25 as complete until TASK-26.3 establishes the final documentation contract.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the requested multi-perspective source review and documentation refresh. Published a durable 20-finding audit with impact priorities, reproducible code/test evidence, remediation status, and recommended ordering. Updated README, installation/runbook, contributing, security, roadmap, changelog, project guidance, examples, templates, and documentation contracts to match the actual Claude/Codex/Copilot architecture, Python 3.10 runtime floor, selectable ADR profiles, and confirmed limitations. Verification: 555 passed and 3 skipped; focused documentation/client/profile tests passed; Markdown, strict ADR lint, doctor, indexes, generated payload sync, and diff whitespace checks are clean.

Added the explicit template-choice rationale to the public README and both installation paths, linked the full format evaluation and ADR-005, and added a regression contract. Verification: 7 documentation-contract tests passed; README.md, INSTALL.md, INSTALL-AGENT.md, and the research report are markdownlint-clean.

The installed project guide now explains the same MADR/Nygard/canonical trade-off as the README and install runbooks, so configured coding agents receive the rationale locally.
<!-- SECTION:FINAL_SUMMARY:END -->
