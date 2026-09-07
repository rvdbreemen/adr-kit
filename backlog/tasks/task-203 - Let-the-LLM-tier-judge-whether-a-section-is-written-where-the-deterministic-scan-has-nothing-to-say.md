---
id: TASK-203
title: >-
  Let the LLM tier judge whether a section is written, where the deterministic
  scan has nothing to say
status: To Do
assignee: []
created_date: '2026-09-06 15:40'
labels:
  - enhancement
  - readiness
  - llm
dependencies: []
priority: medium
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 added SECTION_PLACEHOLDER_ONLY, which fires on a literal adr-kit placeholder: a '- TODO:' line or an '<!-- TODO: -->' comment. That is a marker check, not a reading. A section holding 'TBD', 'see above', 'n/a for now', or three sentences of vacuous prose is indistinguishable from a written one to every deterministic surface adr-kit has, and those are the shapes a human actually leaves behind. When the deterministic signals are silent, silence is the wrong answer twice: once because nothing is wrong, once because nobody looked.

An LLM can answer that question and nothing else in the toolkit can. ADR-089 already decided the shape: declarative per commit, semantic on a cadence. The guardian's bi-weekly llm tier already runs adr-suggest and adr-judge --llm, already confirms cost before spending, and already defaults llm_autorun to false. 'Is this required section actually answered?' is a third question of the same kind, asked in the same place.

It must NOT go into bin/adr-readiness. Three reasons, each independently sufficient:
- The readiness report is asserted byte-stable across two runs (tests/test_adr_readiness.py:112 and :294 compare json.dumps(..., sort_keys=True)). A model breaks determinism by construction.
- The MCP server is key-free by design and adr-suggest is deliberately not exposed there (ADR-036). readiness is exposed.
- readiness runs inside the guardian's 10-second subprocess timeout (bin/adr-guardian:1086) and that refresh returns 0 on every failure (:1088-1094). A model call there would blow the timeout and silently freeze the SessionStart queue for 24 hours while looking healthy.

Cost shape to respect: since the batching reversal in ADR-017 the judge is one isolated call per ADR, so a sweep over --all-proposed is linear in the number of Proposed records, not one call.

Hard constraint inherited from TASK-198: it reports, it never refuses on arrival. An imported record must not fail a blocking gate, because a team that hits a wall on import disables the gate.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The llm tier can report a required section that is present, not a placeholder, and still says nothing, naming the section and quoting what it found
- [ ] #2 bin/adr-readiness stays deterministic and key-free: its byte-stability tests pass unchanged and no model call is reachable from it or from the MCP tool
- [ ] #3 The finding is advisory: no exit code changes, and adr-lint still exits 0 on the record
- [ ] #4 Cost is stated per run before spending, consistent with the existing guardian llm tier
<!-- AC:END -->
