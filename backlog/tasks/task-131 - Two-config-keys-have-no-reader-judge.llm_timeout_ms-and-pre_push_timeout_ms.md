---
id: TASK-131
title: 'Two config keys have no reader: judge.llm_timeout_ms and pre_push_timeout_ms'
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
labels:
  - config
  - dead-code
dependencies: []
priority: medium
ordinal: 99500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`judge.llm_timeout_ms` and `pre_push_timeout_ms` are declared in the config schema and read by nothing. Grep the tree: no call site resolves either key.

A setting that accepts a value and ignores it is worse than a missing one. The user changes it, observes no effect, and concludes the timeout cannot be changed -- or worse, concludes it was changed and plans around a bound that is not in force.

Either wire each key to the code path it names, or remove it from the schema and say so in the changelog. Removal is the likely right answer for `judge.llm_timeout_ms`, which duplicates `judge.llm_timeout_seconds` in different units.

Evidence: `schemas/adr-kit-config.schema.json`; no reader for either key anywhere under `bin/`, `hooks/`, `templates/`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each key is either read by the code path it names or absent from the schema
- [ ] #2 A test asserts that every key the schema declares has a reader, so the next orphan is caught by the gate rather than by a sweep
<!-- AC:END -->
