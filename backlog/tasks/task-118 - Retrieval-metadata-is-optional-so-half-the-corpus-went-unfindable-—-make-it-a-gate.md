---
id: TASK-118
title: >-
  Retrieval metadata is optional, so half the corpus went unfindable — make it a
  gate
status: Done
assignee: []
created_date: '2026-08-03 21:38'
updated_date: '2026-08-03 23:44'
labels:
  - retrieval
  - lint
  - adr
dependencies: []
priority: medium
ordinal: 4100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while fixing a probe failure, not by looking for it.

**12 of 28 shipped ADRs had no `topics`, no `aliases` and no `components` at all** — including ADR-004, which defines the entire context-injection architecture. A query saying `fail open lifecycle hook context injection` returned ADR-015, ADR-018 and ADR-027 and *not* ADR-004, the decision that query is literally about.

The cause is structural, not clerical. Retrieval metadata is optional frontmatter, `bin/adr new` scaffolds it empty, and no gate ever asks. Nothing fails, nothing warns, and the record simply stops being findable — silently, and worse over time: every well-annotated ADR added later pushes the bare ones further down, so the corpus degrades exactly as it grows. The oldest and most foundational records are the ones that lose.

The 12 were annotated by hand as part of TASK-110's probe repair, and `adr-context --check-probes` recovered. That fixes today's set and does nothing about tomorrow's.

Two further findings from the same repair, both worth keeping:

- **Components must name what an ADR *defines*, not what it touches.** ADR-004 was first given `adr-context` and `adr-index` because it reads them; that made it outrank ADR-018 on a vector-retrieval query. Narrowed to `lifecycle hooks` and `adr-judge`, which is its actual surface.
- **The probe fixture encoded a stale expectation.** `index-first-query-engine` asked for ADR-018 on the query `schema v2 selective ADR retrieval metadata`, which describes ADR-007's graph schema rather than ADR-018's vector layer. Corrected to ADR-007, and a new `vector-layer-semantic-retrieval` probe now covers ADR-018 with a query that actually describes it.

Note the ordering against TASK-94: semantic retrieval reduces how much this metadata matters, because a vector match does not need shared vocabulary. It does not remove it — the store embeds title, topics, aliases, components and decision, so a record with three empty fields is embedded from less text and stays weaker. This is worth doing regardless of when the vector layer lands.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A lint finding reports an Accepted ADR with no topics, no aliases and no components; decide FAIL or ADVISORY and state the reason in the commit
- [x] #2 The finding is satisfiable by editing the record, per spec R15 — it names what is missing rather than scoring the record
- [x] #3 `bin/adr new` prompts for or scaffolds non-empty retrieval metadata, so a new ADR does not start unfindable
- [x] #4 A test asserts that an ADR with all three fields empty produces the finding, and that one with any of them populated does not
- [x] #5 The guidance states that components name what the ADR defines, not everything it touches — with ADR-004 as the worked example
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**The check already existed, and finding out why it never fired was the task.**

`check_retrieval_metadata` has been in `bin/adr-lint` all along with four escape conditions. I measured which one each of the twelve bare records used, rather than guessing: **all twelve escaped through `binding is not True`**, and every one of them was `binding: false`.

That precondition made the check almost inert. Being non-binding means a decision does not gate code; it does not mean it should be invisible. An Accepted ADR nobody can retrieve is a decision that will be re-made, which is the failure R0 exists to prevent.

**Two changes, and the second matters as much as the first:**

1. The `binding` precondition is gone.
2. The finding moved from `policy` — a gate not in `DEFAULT_GATES` — into `completeness`. An advisory in a gate nobody runs is silence, not an advisory. That is the mechanism by which twelve records went unfindable for months with no report.

AC#1's decision: **ADVISORY by default**, FAIL under `context.retrieval_completeness: strict`. Findability is a quality property, not a correctness one, and a hard failure would block acceptance of an otherwise sound record. Being *seen* was the missing half, not being blocking.

The two exemptions that genuinely mean "findable another way" are kept: `context_scope: global` is injected regardless of the query, and a populated Decision Contract gives the ranker text to match on.

AC#3: `bin/adr new` names the three fields it cannot fill without inventing them — the signer pattern, propose never assume — including the rule authors get wrong. That rule is not academic: giving ADR-004 the components it merely *reads* made it outrank ADR-018 on a vector-retrieval query.

**Two tests changed rather than the code.** The retrieval-health test pinned the finding to `--gates policy` and now asserts on the finding's level rather than the exit code, since its fixture is a minimal stub that trips other gates too. The migration test asserted a migrated Nygard record lints clean; it now asserts that the one surviving advisory is the honest one — an imported record has no retrieval metadata, migration deliberately never invents any, so the finding is the migrating team's to-do list.

Full suite: 1538 passed, 13 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
