---
id: TASK-33
title: Record v0.34.0 enforcement behavior changes as ADRs
status: Done
assignee: []
created_date: '2026-07-18 22:18'
updated_date: '2026-07-18 22:23'
labels:
  - adr
  - enforcement
dependencies: []
references:
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - bin/adr-lint
  - templates/githooks/pre-commit
  - tests/test_adr_lint_clarity.py
modified_files:
  - >-
    docs/adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md
  - docs/adr/ADR-009-bound-heuristic-gates-to-findings-an-author-can-act-on.md
  - docs/adr/ADR-INDEX.md
  - docs/adr/ADR-INDEX.json
  - docs/adr/README.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
v0.34.0 shipped two changes to enforcement behavior that were treated as bug fixes but are architectural decisions under the project's own code-review Check 7.

1. The pre-commit hook now considers an ADR Kit checkout as a candidate engine root, competing on manifest version with installed plugin caches. This changes which engine judges a commit.
2. The clarity gate now skips an allowlist of universal acronyms, accepts the "expansion (ACRONYM)" word order, and ignores YAML frontmatter. This makes acceptance reachable for records the gate previously could never pass.

Both are after-the-fact ADRs: the behavior is already released, so each carries verified_in pointers to the shipping tests.

The set -e fix in the same release is deliberately out of scope. It restored intended behavior rather than choosing between alternatives.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR-008 records the hook engine-resolution decision with at least two rejected alternatives
- [x] #2 ADR-009 records the heuristic-gate scope decision with at least two rejected alternatives
- [x] #3 Both ADRs pass the acceptance gate set: schema, completeness, audit, evidence, clarity, consistency, policy
- [x] #4 Both ADRs cite the shipping tests and v0.34.0 commits as evidence
- [x] #5 Both generated indexes are regenerated and adr-doctor reports index_ok and lint_ok
- [x] #6 Both ADRs are left Proposed for human review; neither is self-accepted
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added ADR-008 (engine resolution from a version-ranked root set including the checkout) and ADR-009 (bound heuristic gates to actionable findings). Both were authored as after-the-fact records for behavior already shipped in v0.34.0, carry documents_shipped:true with verified_in evidence, and pass the full acceptance gate set. Robert accepted both on 2026-07-18; neither was self-accepted.

Each carries a require_pattern Enforcement rule so the decision cannot silently regress: ADR-008 pins the candidate-root block in templates/githooks/pre-commit, ADR-009 pins CLARITY_ACRONYM_ALLOWLIST in bin/adr-lint. Both dry-run clean.

The set -e fix from the same release was deliberately left undocumented as an ADR: it restored intended behavior rather than choosing between alternatives, which the guide explicitly excludes.
<!-- SECTION:FINAL_SUMMARY:END -->
