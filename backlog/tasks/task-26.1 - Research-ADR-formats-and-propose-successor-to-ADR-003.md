---
id: TASK-26.1
title: Research ADR formats and propose successor to ADR-003
status: Done
assignee:
  - Codex
created_date: '2026-07-18 15:34'
updated_date: '2026-07-18 15:55'
labels:
  - research
  - adr
dependencies: []
documentation:
  - docs/research/adr-format-evaluation.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
modified_files:
  - docs/research/adr-format-evaluation.md
  - docs/adr/ADR-003-template-profile-compatibility.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/adr/ADR-INDEX.md
parent_task_id: TASK-26
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Research primary sources for widely used ADR formats and ecosystems, compare their structures and adoption signals, evaluate agent friendliness and deterministic tooling compatibility, then draft a Proposed successor to ADR-003. Preserve ADR history and do not flip ADR-003 until the recommendation is explicitly approved.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Primary-source research covers at least Nygard/adr-tools, MADR, Y-Statements, and other formats with material adoption or tooling relevance.
- [x] #2 The comparison uses explicit criteria for human readability, agent parseability, token cost, evidence quality, status/history support, enforcement extensibility, and migration risk.
- [x] #3 A recommended default and supported-format set are justified with citations and a clear compatibility model.
- [x] #4 The successor ADR passes completeness, evidence, clarity, and consistency review while remaining Proposed pending explicit approval.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Read Accepted ADRs returned by context and map ADR-003 relationships.
2. Research authoritative sources for Nygard/adr-tools, MADR, Y-Statements, and materially relevant alternatives/ecosystems.
3. Score formats against the approved human and agent criteria, distinguish formats from tools, and document adoption evidence without treating popularity proxies as exact usage counts.
4. Write a cited research report and draft ADR-005 as Proposed with at least two alternatives, risks, mitigations, compatibility, and migration details.
5. Run completeness, evidence, clarity, consistency, related-record, and index checks; then complete the approved ADR-003 supersession lifecycle and record the result.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Research found no authoritative global format census; adoption signals and the 2026 empirical comparison identify Nygard and MADR as the leading lightweight candidates. MADR scored highest for adr-kit's agent-reliability criteria; Nygard and canonical remain selectable. ADR-005 quality score: 0.88 (grade A). Strict clarity's ADR/MADR acronym finding was manually assessed as a frontmatter-order false positive after explicit body definitions.

The user's request to switch to MADR followed by explicit approval to execute the expanded plan satisfied the lifecycle approval gate. ADR-005 was accepted and ADR-003 superseded on 2026-07-18. adr-related confirms reciprocal links and no dangling references.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Researched Nygard/adr-tools, MADR, Y-Statements, Tyree/Akerman, arc42, ISO-oriented records, and major ecosystem guidance. Published a cited weighted comparison, selected MADR as the agent-friendly default with Nygard and legacy canonical profiles, accepted ADR-005, superseded ADR-003, and verified reciprocal lifecycle links and the generated index.
<!-- SECTION:FINAL_SUMMARY:END -->
