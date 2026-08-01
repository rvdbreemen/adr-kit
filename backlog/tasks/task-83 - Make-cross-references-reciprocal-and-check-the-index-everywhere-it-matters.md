---
id: TASK-83
title: 'Make cross-references reciprocal, and check the index everywhere it matters'
status: To Do
assignee: []
created_date: '2026-08-01 10:34'
labels:
  - spec-gap
  - R7
  - index
  - lint
dependencies: []
priority: medium
ordinal: 88500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R7. The index half is genuinely met and worth keeping: every `bin/adr` subcommand ends in `_commit_lifecycle_changes`, which snapshots the ADR files plus README.md/ADR-INDEX.md/ADR-INDEX.json, applies the writes and runs `run_index` inside the same rollback-able transaction. Two gaps around it.

**Supersession is the only reciprocal writer.** A new ADR that lists ADR-009 under Related Decisions updates nothing in ADR-009. `bin/adr-related` is read-only: it computes inbound, outbound and dangling links and prints them (`bin/adr-related:250-282`). `bin/adr-lint` has no reciprocity or dangling-related gate — only `detect_supersession_broken`. So the spec's "older ADRs updated too, precisely and reliably, not best-effort" holds for supersession and for nothing else.

R7 also says the LLM decides when a cross-reference is warranted. That is judgement and belongs in the authoring path; what must be mechanical is that a decided reference is *written on both sides* and that a dangling one is caught.

**Index freshness is not checked where it is most likely to rot.** `grep -l 'adr-index|--check'` over `bin/adr-guardian`, `bin/adr-lint`, `templates/githooks/pre-commit` and `skills/guardian/SKILL.md` returns nothing. The guarantee holds only for changes made through the lifecycle CLI; an ADR edited by hand, or written directly by a model with the Write tool, leaves the index stale until CI notices — and the CI check is on this repository, not in the templates a downstream project installs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 When an ADR gains a reference to another, the referenced ADR gains the reciprocal entry through a supported command
- [ ] #2 adr-lint gains a gate for dangling and one-sided Related Decisions, at the appropriate severity
- [ ] #3 The guardian sweep and the pre-commit hook check index freshness, not only the release path
- [ ] #4 A downstream project installing adr-kit gets an index-freshness check in its own CI
- [ ] #5 The authoring path asks the model to decide which cross-references are warranted, and the mechanism writes both sides once decided
<!-- AC:END -->
