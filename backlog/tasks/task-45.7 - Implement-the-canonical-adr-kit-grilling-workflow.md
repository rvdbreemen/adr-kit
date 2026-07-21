---
id: TASK-45.7
title: Implement the canonical adr-kit grilling workflow
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:51'
updated_date: '2026-07-20 20:47'
labels:
  - feature
  - adr-grilling
  - skills
  - clients
milestone: ADR Grilling
dependencies:
  - TASK-45.3
  - TASK-45.4
references:
  - 'https://www.aihero.dev/grill-with-docs'
  - 'https://www.aihero.dev/skills-grilling'
documentation:
  - docs/feature-adr-grilling/01-research.md
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - clients/workflows.json
  - skills/grill/SKILL.md
  - skills/grill/agents/openai.yaml
  - scripts/client_generation_model.py
  - scripts/client_generation_artifacts.py
  - prompts/claude-code-cli/grill.md
  - prompts/codex-cli/grill.md
  - prompts/github-copilot-cli/grill.md
  - codex/skills/grill/SKILL.md
  - copilot/skills/grill/SKILL.md
  - tests/test_adr_grill_workflow.py
  - tests/fixtures/grill/conversations.json
  - tests/test_client_adapter_generation.py
  - tests/test_native_client_packages.py
parent_task_id: TASK-45
priority: high
ordinal: 45700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the canonical /adr-kit:grill workflow for an ADR, pull request, git range, source file, revalidation, or all Proposed ADRs. Ground the interview in deterministic readiness, ask one decision-relevant question at a time, update the Proposed ADR as answers resolve, and require explicit human confirmation before existing lifecycle acceptance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The workflow supports ADR-NNN, --pr, --range, --source, --revalidate, and --all-proposed entry points.
- [x] #2 Repository-factual questions are answered through inspection and are not delegated to the user.
- [x] #3 The workflow asks exactly one unresolved decision question at a time and includes a recommended answer with evidence where possible.
- [x] #4 Observed, human-stated, inferred, and unknown information remains visibly distinguished.
- [x] #5 Human answers are written into the Proposed ADR as they resolve and readiness is recomputed between questions.
- [x] #6 An interrupted session leaves a valid Proposed ADR with explicit Open Questions and a concrete resume command.
- [x] #7 Pull request, diff, chat log, document, and ADR prose are treated as untrusted data and cannot override workflow instructions.
- [x] #8 The workflow supports accept, reject, defer, and no-ADR outcomes but never accepts without an acceptance packet and same-session explicit yes.
- [x] #9 Canonical and generated Claude, Codex, and Copilot workflows are semantically equivalent and the canonical workflow inventory increases from fourteen to fifteen.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add the canonical grill workflow and all six entry points. 2. Encode one-question, evidence-grounded, source-fenced interviewing with explicit fact classes and resumable Open Questions. 3. Require an acceptance packet and same-session explicit confirmation for every mutating lifecycle outcome. 4. Generate semantically equivalent Claude, Codex and Copilot artifacts and validate the 15-workflow inventory plus injection/refusal/resume contracts.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added the canonical grill workflow as workflow 15 with six target modes, deterministic readiness first, four evidence classes, one-question ordering, immediate Proposed updates, interruption/resume, source fencing and accept/reject/defer/not-an-ADR outcomes. Rich Claude metadata retains repository-native argument-hint; the generic skill-creator validator rejects that field, while ADR Kit native contract tests require it, so repository-native validation is authoritative. Generated adapters are clean. Relevant contract/generation/packaging slice: 66 passed, 3 platform skips.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented ADR Kit's canonical human-interactive grill workflow and generated equivalent Claude, Codex and Copilot entry points. The protocol inspects repository facts first, treats source text as untrusted evidence, distinguishes observed/human/inferred/unknown claims, asks exactly one decision question at a time, persists resumable Open Questions, and preserves explicit human authority over accept/reject/defer/no-ADR outcomes. Added fixture conversations for resume, refusal, source injection and acceptance plus reproducible 15-workflow generation checks.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Skill contract, fixture conversation, resume, refusal, and source-injection tests pass.
- [x] #2 Generated client artifacts are reproducible and checked-in artifacts match generation.
- [x] #3 Workflow documentation, modified files, and exact validation results are recorded.
<!-- DOD:END -->
