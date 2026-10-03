---
id: TASK-204
title: >-
  Nothing checks that an ADR's stated scope is the scope the code actually
  implements
status: In Progress
assignee: []
created_date: '2026-09-07 05:34'
updated_date: '2026-10-03 14:49'
labels:
  - enhancement
  - adr
  - governance
dependencies: []
priority: medium
ordinal: 48000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two instances in one session, in two unrelated repositories, both found by accident while chasing something else. In both the ADR text is correct and the code is a narrower subset of it, so every check that asks 'does this exist' reports green.

Instance 1, this repository. ADR-041 (Accepted 2026-08-20) enumerates queue eligibility as 'unresolved human input, ready-for-confirmation, an active implementation link, shipped evidence while still Proposed, or a quality score below the existing 0.70 threshold'. rank_proposed in bin/adr_guardian_queue.py implemented the first of those as bool(item.get('open_questions')) alone. A record classified needs-human-input for any other reason was therefore not eligible, contrary to the ADR. Found only because TASK-199 measured the queue before and after a classification change and saw it drop to 0 candidates.

Instance 2, OTGW-firmware. ADR-168 decided the ESP-IDF console must be muted on the PIC path and names the esp32-classic target. Both call sites of platformMuteUart0Console() sat inside #if HAS_RUNTIME_HW_DETECT, which is 1 only on the combo board, so on esp32-classic the mitigation was never compiled in. It shipped that way for about a month and the symptom was firmware log text being transmitted into the PIC.

The shape is the same and it is not what the existing checks look for. adr-lint asks whether the record is well formed. adr-judge asks whether the diff violates the decision. Neither asks whether the decision is implemented everywhere it says it applies. The failure is silent by construction: there is no dead code, no unused symbol, no link error, and the ADR reads perfectly because every sentence in it is true.

Deliberately not proposing a mechanism here. A fully general 'is this decision implemented across its stated scope' is a semantic question and belongs to the LLM tier under ADR-089 if anywhere; a deterministic subset may be reachable through the Enforcement path_glob, by checking that a scope actually resolves to files and that a require_pattern holds under every target the ADR names. Decide that as part of the task, and be willing to conclude that the honest answer is a review-checklist item rather than a tool.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The problem is stated as a check with a decidable outcome, not as advice: given an ADR and a repository, something answers whether the decision is implemented across the scope the ADR names
- [x] #2 Both recorded instances are used as fixtures: the ADR-041 prose-versus-implementation gap and an ADR-168-shaped case where the call site sits behind a guard that excludes a named target
- [x] #3 If the conclusion is that no deterministic check is possible, that conclusion is written down with its reasoning and the review-checklist alternative, and the task closes on that rather than on a half-check that reports green
- [x] #4 Whatever ships does not add a blocking gate that fires on arrival: an imported or legacy record must stay satisfiable by editing it (spec R15)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decision (maintainer, 2026-10-03): a deterministic sub-check plus a review-checklist item for the semantic rest.

What already existed: `adr-audit --whole-codebase` applies forbid_pattern and require_pattern to every tracked file, so 'does the rule hold everywhere in its scope' was already decidable. What was missing: a rule whose path_glob matches no tracked file is checked against nothing and stays green forever. That is the decidable outcome AC#1 asks for: given an ADR and a repository, `adr-judge --check-scope` answers which rules have an empty scope.

Both recorded instances are fixtures (AC#2) and are pinned as out of reach, with their reasons. The ADR-168 shape: the call sits behind `#if HAS_RUNTIME_HW_DETECT`, so the symbol exists and the pattern matches, and only a per-target preprocessor view would see the gap. The ADR-041 shape: five cases in prose, one in code, and no rule naming the other four. Every report carries a `limits` sentence saying that a resolving scope is not proof of implementation, so silence is not read as green (AC#3). The review skill (step 3b) holds the checklist for both shapes.

Advisory only: exit codes are unchanged (ADR-026 contract), and nothing fires on arrival (AC#4). This repository: 17 rule globs, all resolving. Tests: tests/test_enforcement_scope.py (6); the audit, judge, security, adapter and docs suites: 94 passed.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-09-07 20:04
---
CITATION CORRECTION, 2026-09-07, the same one as on TASK-203; both records were filed in the same pass and inherited it.

The description says a semantic scope question "belongs to the LLM tier under ADR-089 if anywhere". ADR-089 is not a decision of this project. `git grep -l 'ADR-089' origin/dev` finds it only in these two backlog records and in `tests/testsets/otgw-firmware/adrs/ADR-089-heap-tier-machine-contract.md`, a fixture corpus from another codebase. `docs/adr` stops at ADR-042.

The tiering decision meant here is ADR-002 (the guardian's cheap declarative tier per commit, LLM tier on a cadence, `docs/adr/ADR-002...md:73`), with ADR-036 for the rule that the LLM tier stays advisory while the declarative gates enforce at commit time.

The deterministic subset this record suggests -- checking a scope claim against the Enforcement `path_glob` -- is unaffected by the correction and remains the more promising half of the idea, since it needs no LLM at all.

Still To Do, not a release blocker.
---
<!-- COMMENTS:END -->
