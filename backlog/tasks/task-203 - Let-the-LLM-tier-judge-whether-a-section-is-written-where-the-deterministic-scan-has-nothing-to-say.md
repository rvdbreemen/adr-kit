---
id: TASK-203
title: >-
  Let the LLM tier judge whether a section is written, where the deterministic
  scan has nothing to say
status: In Progress
assignee: []
created_date: '2026-09-06 15:40'
updated_date: '2026-10-03 15:47'
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
- [x] #1 The llm tier can report a required section that is present, not a placeholder, and still says nothing, naming the section and quoting what it found
- [x] #2 bin/adr-readiness stays deterministic and key-free: its byte-stability tests pass unchanged and no model call is reachable from it or from the MCP tool
- [x] #3 The finding is advisory: no exit code changes, and adr-lint still exits 0 on the record
- [x] #4 Cost is stated per run before spending, consistent with the existing guardian llm tier
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decision (maintainer, 2026-10-03): build it, advisory, in the guardian's LLM tier. Governing records: ADR-002 (two-tier cadence; the record's ADR-089 citation was already corrected to ADR-002), ADR-017/036 (host backend, shared resolver), and ADR-038 (unusable answers degrade per ADR). No new ADR was written. The guardian skill is the only caller, and the tool adds no gate, so it falls within ADR-002's semantic tier; flagged for the maintainer in the PR in case a record is still wanted.

Shape: new bin/adr-substance. Per Proposed ADR, it takes the required sections that are written and not a placeholder (Status and Related skipped; missing, empty and TODO sections are left to the deterministic gates). One isolated host-CLI call per ADR via adr_llm.resolve_llm_backend. ADR text is fenced with content-derived sentinels. The model must return {heading, quote, reason}; a finding survives only if the heading was sent and the quote occurs in that section (whitespace-normalised), so it always points at the author's words (AC#1). --estimate prints the call count and calls nothing (AC#4); the guardian skill adds that line to its cost prompt and runs the tool as step 3a-bis.

Exit 0 on findings and on degrade, 2 on a config error, so nothing blocks (AC#3). bin/adr_readiness.py and bin/adr-mcp do not reference it: asserted in a test, and readiness byte-stability is untouched (AC#2). Packaging: packaging/executables.json, mode 100755 for bin and both adapter copies. Tests: tests/test_adr_substance.py (6, with a fake host CLI, no real model) plus the packaging, allowlist, adapter, docs and guardian artifact suites: 66 passed, 3 skipped. On this repository --estimate reports 1 call (ADR-035).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-09-07 20:04
---
CITATION CORRECTION, 2026-09-07. The record cites ADR-089 as the decision that "already decided the shape: declarative per commit, semantic on a cadence". No such ADR exists in this project.

```
git grep -l 'ADR-089' origin/dev
  backlog/tasks/task-203..., backlog/tasks/task-204...
  tests/test_adr_query.py, tests/test_adr_retrieval_health.py
  tests/testsets/otgw-firmware/adrs/ADR-089-heap-tier-machine-contract.md
```

Every hit outside the two backlog records is the OTGW firmware corpus, a test fixture. The highest real decision in `docs/adr` is ADR-042.

THE DECISION THE RECORD MEANS is ADR-002, whose Decision Outcome names the two-tier cadence in those words: "cheap tier (declarative drift via `adr-judge`, stale ...)" at `docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md:73`, with the bi-weekly LLM tier alongside it. ADR-036 carries the companion terms, that the advisory LLM tier is not the enforcement tier at commit time.

This matters beyond tidiness: the argument for putting the semantic judgement on the guardian's LLM tier rests on an existing decision, and a reader who tries to check that reasoning against ADR-089 finds a heap-memory contract for a firmware project. Cite ADR-002.

The proposal itself is unaffected and still open. Not a release blocker.
---
<!-- COMMENTS:END -->
