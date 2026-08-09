---
id: TASK-52.1
title: Approve index-first retrieval architecture and establish baselines
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 18:55'
labels:
  - adr
  - architecture
  - agent-retrieval
  - benchmark
milestone: Index-first ADR retrieval
dependencies: []
references:
  - TASK-30
  - TASK-52
  - bin/adr-context
  - tests/testsets/otgw-firmware/adrs
  - ADR-014
documentation:
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
modified_files:
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
  - docs/adr/ADR-INDEX.json
  - docs/adr/ADR-INDEX.md
  - docs/adr/README.md
parent_task_id: TASK-52
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define the durable architectural contract for using the generated ADR graph as ADR Kit's runtime selective-context engine. Ground the decision in current source behavior, TASK-30 evidence, ADR-004/005/007, the adr-kit dogfood set, and the larger OTGW fixture corpus. Preserve human lifecycle authority through a Proposed ADR and one-question grilling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Proposed ADR records the problem, selected architecture, at least two viable alternatives, consequences, risks, mitigations, related decisions, and concrete repository evidence.
- [x] #2 The ADR explicitly preserves Markdown as decision authority, generated JSON as runtime projection, deterministic local operation, fail-open context injection, and fail-closed judge enforcement.
- [x] #3 Human choices for schema evolution, retrieval metadata, lifecycle-state handling, ranking, fallback, and rollout are captured through one-question grilling.
- [x] #4 Baseline retrieval accuracy, historical leakage, index size, and end-to-end timing are recorded for the adr-kit set and a larger representative corpus.
- [x] #5 The ADR remains Proposed until all readiness findings are resolved and the user gives explicit same-session acceptance.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Created ADR-014 as Proposed and populated it from repository facts. Current readiness is needs-human-input with seven Open Questions, no mechanical findings, no blocking implementation link, and strict lint passes with one advisory. Baseline on 2026-07-23: 14 ADRs median 548.7 ms across three CLI samples; 169-record corpus median 2609.6 ms; generated graph 14,553 bytes before the content refresh.

Grill decision 1 resolved on 2026-07-23: human approved schema v2 as the generated default, v1 reader compatibility for one minor-release window, preservation of existing result fields during that window, and no in-place schema-v1 extension. ADR-014 updated; readiness now reports six unresolved human decisions.

Grill decision 2 resolved on 2026-07-23: human approved flat `topics`, `aliases`, `components`, and `symbols` retrieval metadata; scalar `context_scope` (`global` or `selective`); an optional `## Decision Contract` with Must, Must Not, Exceptions, and Verification; and Enforcement `path_glob` as the sole path-applicability authority. The duplicate compatibility question was reconciled with decision 1. ADR readiness now reports four unresolved human decisions.

Grill decision 3 resolved on 2026-07-23: human approved Accepted ADRs as governing results; Proposed ADRs as clearly labelled, non-governing advisory context; Superseded ADRs as excluded by default with successor redirection; and Rejected or Deprecated ADRs as available only through an explicit historical query. ADR-014 remains Proposed and readiness now reports three unresolved human decisions.

Grill decision 4 resolved on 2026-07-23: human approved visible Markdown fallback for missing, invalid, unsupported, or stale indexes during normal queries; bounded fail-open fallback for hooks; and strict failure/reporting with no silent fallback in CI, diagnostics, or explicit strict-index mode. ADR-014 remains Proposed and readiness now reports two unresolved human decisions.

Grill decision 5 resolved on 2026-07-23: human approved deterministic positive-evidence ranking; exact path, symbol, and component matches before topic, alias, title, Decision Contract, and decision summary; no lifecycle, recency, or relationship-count relevance boost; at most two one-hop supporting ADRs; explained matched fields; and ADR ID as the stable final tie-breaker. ADR-014 remains Proposed and readiness now reports one unresolved human decision.

Grill decision 6 resolved on 2026-07-23: human approved top-1 at least 90%, top-3 at 100%, zero historical/no-match leakage, 30-sample query p95 at or below 250 ms through 200 ADRs and 500 ms through 1,000 ADRs, hook p95 at or below 250 ms with a 500 ms semantic hard timeout, graph size at or below 2 KiB per ADR plus 16 KiB and 25% of source Markdown, and zero numbered-Markdown opens for healthy normal queries. ADR readiness is now `ready-for-confirmation`; strict seven-gate lint passes while Proposed.

Acceptance preflight found that the binding gate name `index-first-retrieval` has no literal verification anchor in non-document source yet. ADR-014 itself requires that anchor before acceptance, and Accepted binding ADR consistency would otherwise fail after the status transition. Final acceptance is therefore paused rather than creating an invalid Accepted record.

The acceptance blocker is resolved: TASK-52.2 delivered schema-v2 retrieval metadata and TASK-52.3 delivered the executable index-first query gate. The literal `index-first-retrieval` anchor is present in non-document source, the generated graph is current, ADR-014 strict seven-gate lint passes, adr-doctor reports zero required failures and no ADR findings, and readiness remains `ready-for-confirmation` with no open questions. ADR-014 intentionally remains Proposed until the user gives the separate final explicit `yes` after this completed implementation summary.

Final human lifecycle approval was received explicitly in the active grill session on 2026-07-23. `adr accept ADR-014` transitioned the record to Accepted and recorded Robert as the actor. Post-transition verification passes: strict schema/completeness/audit/evidence/clarity/consistency/policy lint reports PASS with no findings; `adr-readiness` classifies ADR-014 as `accepted` with no open questions or advisories; `adr-doctor --check` reports zero required failures and zero ADR findings; the generated index is current and adapter generation has zero drift. Optional doctor degradations for unconfigured local judgment and absent generated project guidance are unrelated to ADR validity.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Codex
created: 2026-07-23 17:55
---
Grill decision 1 resolved on 2026-07-23: human approved schema v2 as the generated default, v1 reader compatibility for one minor-release window, preservation of existing result fields during that window, and no in-place schema-v1 extension. ADR-014 updated; readiness now reports six unresolved human decisions.
---

author: Codex
created: 2026-07-23 18:05
---
Grill decision 2 approved and recorded. ADR-014 remains Proposed; four one-question grill decisions remain (authority, fallback, ranking, and measured acceptance thresholds).
---

author: Codex
created: 2026-07-23 18:08
---
Grill decision 3 approved and recorded. Remaining decisions: graph fallback behavior, relevance ranking, and measured acceptance thresholds.
---

author: Codex
created: 2026-07-23 18:11
---
Grill decision 4 approved and recorded. Remaining decisions: deterministic relevance ranking and measured acceptance thresholds.
---

author: Codex
created: 2026-07-23 18:13
---
Grill decision 5 approved and recorded. Only the measured acceptance-threshold contract remains unresolved.
---

author: Codex
created: 2026-07-23 18:18
---
All grill content decisions are resolved. Acceptance preflight is paused on the missing real `index-first-retrieval` source anchor; the ADR remains Proposed and internally consistent.
---

author: Codex
created: 2026-07-23 18:53
---
Implementation preflight is now complete. TASK-52.2 and TASK-52.3 are Done; the previously missing binding-gate anchor exists and verifies. Awaiting the final explicit acceptance confirmation required by the grill workflow.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the human-gated architecture decision for index-first selective ADR retrieval. ADR-014 captures the approved schema-v2 compatibility window, retrieval metadata and Decision Contract structure, lifecycle authority, visible fallback and strict-index behavior, positive-evidence ranking, bounded related context, and measurable accuracy/performance/size thresholds. The previously missing binding verification anchor was implemented through TASK-52.2 and TASK-52.3 before acceptance. Following explicit same-session human confirmation, ADR-014 transitioned from Proposed to Accepted. Post-transition strict seven-gate lint, readiness, doctor, generated-index, and adapter-drift checks all pass; the parent TASK-52 remains open for the separately scoped integration, hook alignment, health checks, and release work.
<!-- SECTION:FINAL_SUMMARY:END -->
