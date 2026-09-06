---
id: TASK-199
title: >-
  Nothing refuses a required section that holds only a migration placeholder at
  accept time
status: To Do
assignee: []
created_date: '2026-09-06 13:48'
labels:
  - bug
  - migrate
  - readiness
dependencies: []
priority: medium
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Measured on a real record: docs/adr/ADR-042 with its `## References` body replaced by the exact line adr-migrate writes, `- TODO: add verifiable references.`, passes the full acceptance gate set that bin/adr accept runs (schema,completeness,audit,evidence,clarity,consistency,policy with --strict) and scores 0.87 grade A in adr-quality, with completeness at 1.0 and evidence reporting references_present: true. The same record with an empty `## References` is blocked: missing sections: ['References (present but empty)'].

That gap is deliberate at arrival. TASK-198 and PR #146 established that an imported record must not fail a blocking gate on import, because a team that hits a wall on import disables the gate; test_adr_policy.py and test_migration_discovery.py pin it. Arrival is not acceptance, though. adr-migrate's `needs content: ## <heading>` report is currently the only signal, and it is printed once, at migrate time, to whoever ran the command. Nothing carries it to the person running adr accept days later.

Readiness and grill are the surfaces where 'imported but unfinished' belongs: bin/adr-readiness already answers 'is this Proposed record ready', the guardian already caches a 24-hour readiness queue, and /adr-kit:grill already walks unresolved items one question at a time. Reporting a placeholder there costs nothing at import and still reaches the operator before the record is frozen. Doing it in completeness would re-open exactly what PR #146 took back out.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 adr-readiness reports a required section whose only content is an adr-kit TODO placeholder, naming the section
- [ ] #2 The arrival policy is untouched: test_adr_policy.py and test_migration_discovery.py still pass unchanged, and adr-lint still exits 0 on such a record
- [ ] #3 A regression test covers a placeholder-only section reaching adr-readiness, and asserts adr-lint stays green on the same record
<!-- AC:END -->
