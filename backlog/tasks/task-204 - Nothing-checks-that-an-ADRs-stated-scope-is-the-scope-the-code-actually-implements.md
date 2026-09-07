---
id: TASK-204
title: >-
  Nothing checks that an ADR's stated scope is the scope the code actually
  implements
status: To Do
assignee: []
created_date: '2026-09-07 05:34'
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
- [ ] #1 The problem is stated as a check with a decidable outcome, not as advice: given an ADR and a repository, something answers whether the decision is implemented across the scope the ADR names
- [ ] #2 Both recorded instances are used as fixtures: the ADR-041 prose-versus-implementation gap and an ADR-168-shaped case where the call site sits behind a guard that excludes a named target
- [ ] #3 If the conclusion is that no deterministic check is possible, that conclusion is written down with its reasoning and the review-checklist alternative, and the task closes on that rather than on a half-check that reports green
- [ ] #4 Whatever ships does not add a blocking gate that fires on arrival: an imported or legacy record must stay satisfiable by editing it (spec R15)
<!-- AC:END -->
