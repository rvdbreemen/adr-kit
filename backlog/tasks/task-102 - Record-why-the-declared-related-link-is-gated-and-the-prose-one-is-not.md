---
id: TASK-102
title: Record why the declared related link is gated and the prose one is not
status: To Do
assignee: []
created_date: '2026-08-03 19:33'
labels:
  - adr
  - lint
  - retrospective
dependencies: []
priority: low
ordinal: 2400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`detect_reference_issues` gates the `related` frontmatter — a dangling target FAILs, a one-sided link FAILs — and deliberately leaves the prose `## Related Decisions` alone. The asymmetry looks like an oversight and is not: `bin/adr accept` lints a single file, so every prose cross-reference in that file resolves to nothing and would fail. The first version of the check did exactly that and produced 57 advisories on a healthy ADR set.

The reasoning is ADR-009's, applied to a second gate: bound a check to the region and vocabulary where a finding is actionable. A machine-written link is a claim the machine can verify; a sentence naming another decision is prose, and gating it punishes writing.

Small consequence, but it is precisely the kind of asymmetry a future maintainer "fixes" — the same 57 advisories, discovered a second time.

Spec: R7, R15's satisfiability constraint. Related: ADR-009.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An ADR records that only declared `related` links are gated, and why prose is out of scope
- [ ] #2 It cites the single-file lint path as the concrete reason, not a general preference
- [ ] #3 It states the reciprocity rule for declared links and what a one-sided link means
- [ ] #4 It connects the reasoning to ADR-009's bounded-heuristic principle rather than restating it from scratch
<!-- AC:END -->
