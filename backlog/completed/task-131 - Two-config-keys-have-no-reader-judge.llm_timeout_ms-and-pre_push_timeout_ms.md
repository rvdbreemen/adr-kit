---
id: TASK-131
title: 'Two config keys have no reader: judge.llm_timeout_ms and pre_push_timeout_ms'
status: Done
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-05 05:58'
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
- [x] #1 Each key is either read by the code path it names or absent from the schema
- [x] #2 A test asserts that every key the schema declares has a reader, so the next orphan is caught by the gate rather than by a sweep
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Nine orphan keys, not the two this record named. The sweep found judge.llm_timeout_ms, judge.pre_push_timeout_ms, policy.regex_compile_checks, policy.pattern_warnings and all five of context.weights. context.weights was the surprise: bin/adr-context:377 still accepts a weights argument and score_record ignores it entirely, so the whole block has been inert since the index-first scorer landed in v0.40.0.

AC#1 -- all nine removed from the schema. Removal alone would have failed every existing .adr-kit.json that sets one, so adr_config.RETIRED_KEYS accepts and ignores them instead: the value was already inert, and breaking the file over it is the worse trade. retired_keys_present() reports which ones a config still carries.

That fix had a hole, caught by the repository's own audit test rather than by inspection: bin/adr-lint validates the same file with a real jsonschema engine that knows nothing about RETIRED_KEYS, and this repo's own docs/adr/.adr-kit.json set seven of the nine, so adr-lint --gates all exited 2. Lint now prunes the retired paths before validating, and a test asserts a config carrying them lints clean.

AC#2 -- tests/test_config_schema_has_readers.py fails when any declared key has no reader. Verified it bites with a probe key. A follow-up from Copilot found a real defect in the first version: it keyed by bare property name, so `enabled` under suggest, watch and inject collapsed to one entry and the gate silently checked fewer paths than it claimed. Now keyed by dotted path.

This repository's own config was cleaned of all seven it carried, because a kit that ships a rule should be the first thing that obeys it.
<!-- SECTION:FINAL_SUMMARY:END -->
