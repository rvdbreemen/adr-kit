---
id: TASK-222
title: >-
  Propose the ADRs the 2026-10-11 defect sweep needs, and grill the open
  decisions
status: In Progress
assignee: []
created_date: '2026-10-11 13:35'
updated_date: '2026-10-11 14:29'
labels: []
dependencies: []
references:
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
  - >-
    docs/adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
  - >-
    docs/adr/ADR-021-let-the-session-scoped-hooks-regenerate-a-stale-adr-index.md
  - 'https://github.com/rvdbreemen/adr-kit/issues/190'
ordinal: 66000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The 2026-10-11 defect sweep (26 confirmed defects, reproduced against f2f6fe2) names nine decisions B1-B9 in its plan. Classify each per the grill protocol (consequential and hard to reverse => ADR, otherwise not-an-adr), draft the needed ones as Proposed records with bin/adr new, link them with bin/adr relate, and settle the human decisions one question at a time with bin/adr answer. Never accept: acceptance is the maintainer's explicit act (ADR-011, ADR-027). Evidence for every claim is in the sweep's FINDINGS.md and evidence folder.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of B1-B9 is classified as ADR or not-an-adr, with the reason recorded
- [ ] #2 Every needed ADR exists as a Proposed record created by bin/adr new, with links written by bin/adr relate on both sides
- [x] #3 No Accepted ADR's decision text is edited; amendments are new records that say Amends ADR-NNN
- [x] #4 bin/adr-lint --strict docs/adr and bin/adr-index --check docs/adr pass
- [x] #5 Every question put to the maintainer is recorded with its answer through bin/adr answer; unresolved ones stay as unchecked Open Questions
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Classification of B1-B9 per the grill protocol (consequential and hard to reverse => ADR):
- B1 + B7 => ADR-044 (one interpreter/engine resolver; the commit gate's behaviour when nothing resolves; the MCP launcher). One cause behind DEF-02, DEF-21, DEF-25.
- B2 + B4 => ADR-045 (canonical diff acquisition; renames, binary-marked files and deletions get explicit verdicts). DEF-03, DEF-04, DEF-05, DEF-13.
- B3 => ADR-046 (one glob dialect for judge, index, query and hooks). DEF-10.
- B5 => not-an-adr: ADR-021 already requires the staleness message instead of silence; a missing or corrupt index is the branch it missed (hooks/adr_hook_core.py:794-806 says so), the subdirectory root is a bug, and a missing-engine notice is fail-open hygiene under ADR-004.
- B6 => not-an-adr: where the plugin declares its MCP server is a reversible packaging choice; the durable part (how it starts) is in ADR-044.
- B8 => not-an-adr: refusing unknown tool arguments is tool-layer input validation; ADR-016's tolerance covers named protocol fields only (MRTR, logLevel), not tool arguments.
- B9 => depends on a human fact: if the 2026-07-23 decision meant two supporting ADRs per response, ADR-014's text needs an amending ADR; if it meant per primary result, the code is wrong and the fix is not-an-adr.
Declared links (bin/adr relate) are deferred to acceptance: relate appends a status_history entry to the Accepted side (probed: ADR-008 got 'changed_by: User: Claude, reason: Related to ADR-044'), which would leave proposal-only lines in immutable histories if a proposal is rejected. The records cite their relations in prose, which ADR-028 allows.

Grill results, 2026-10-11 (all answered by User: Robert van den Breemen, recorded with bin/adr answer):
- ADR-044 Q1: refuse when nothing resolves in a project with Accepted enforcement (recommended). Q2: probing launcher for the MCP server, shipped after windows-latest proves it (recommended).
- ADR-045 Q1: renames judged as new content at the destination. Q2: binary-marked files judged as text. Q3: deletion complies; a rule that needs its files to exist declares must_exist: true (all recommended).
- ADR-046 Q1: the judge's dialect is authoritative. Q2: case-sensitive on git's recorded path. Q3: brackets stay literal; this reversed the agent's first recommendation after finding framework route paths ([id].tsx) and 0 of 26 path_globs using a class.
- B9: the 2026-07-23 decision meant two supporting ADRs per response; ADR-047 amends ADR-014's wording, no engine change.
State: ADR-044..047 are Proposed and ready-for-confirmation; adr-lint --strict and adr-index --check pass; full suite (xdist) 1980 passed, 11 skipped. Not done, by design: acceptance (human-gated, needs an explicit yes per record), declared links (bin/adr relate, at acceptance), commit and push.

AC #2 stays open on purpose: the four records exist (bin/adr new), but their declared links are deferred to acceptance, because bin/adr relate appends a status_history entry to the Accepted side. The relations are cited in prose meanwhile (ADR-028 allows that). Close AC #2 when the records are accepted and related.

2026-10-11: the four Proposed records, the regenerated index and this task are committed on branch adr/defect-sweep-proposals and pushed for review as a draft PR against dev. Before the commit: adr-judge on the staged diff 0 violations; adr-lint and adr-lint --strict pass; adr-index --check changed False; adr-context --check-probes 3/3; build-client-adapters --check changed=0. Acceptance and the relate links remain open (AC #2).
<!-- SECTION:NOTES:END -->
