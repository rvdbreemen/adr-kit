---
id: TASK-126
title: The latency corpus has no entry for bin/adr-discover
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
labels:
  - performance
  - coverage
  - adr-015
dependencies: []
priority: medium
ordinal: 105500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`tests/fixtures/cli/latency-corpus.json` is the ADR-015 fixture that pins CLI latency. `bin/adr-discover` is not in it, so its cost is unmeasured and unbounded.

ADR-015 chose a fixture contract precisely so the measurement survives slow CI runners and future tools. A tool that is absent from the corpus is outside that contract without anyone deciding it should be.

Add the entry, and add a test that fails when a `bin/` entrypoint exists with no corpus row -- otherwise the next tool lands outside the contract the same silent way.

Evidence: `tests/fixtures/cli/latency-corpus.json`; `bin/adr-discover`; ADR-015.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bin/adr-discover has a corpus entry with a measured budget
- [ ] #2 A test fails when any bin/ entrypoint has no corpus row
<!-- AC:END -->
