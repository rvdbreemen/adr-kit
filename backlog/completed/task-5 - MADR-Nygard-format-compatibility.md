---
id: TASK-5
title: MADR / Nygard format compatibility
status: Done
assignee: []
created_date: '2026-05-31 13:20'
updated_date: '2026-06-12 21:26'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Adoption lever: lower switching cost from MADR (2.2k) and Nygard/adr-tools (5.5k). Teach /adr-kit:migrate (and optionally bin/adr-import) to recognize and map MADR headings (Context and Problem Statement, Considered Options, Decision Outcome, frontmatter/* Status:) and Nygard's lighter shape into the canonical seven sections. Add template-profile detection in the schema; adr-audit flags existing MADR/Nygard ADRs. Most design-uncertain, sequenced last.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 migrate recognizes and maps MADR and Nygard formats into the canonical seven sections
- [x] #2 Template-profile detection added to schema; adr-audit flags existing MADR/Nygard ADRs
- [x] #3 MADR + Nygard fixtures migrate to canonical and pass bin/adr-lint
- [x] #4 An ADR is authored for this input-contract change (architecturally significant)
- [x] #5 pytest green, adr-lint clean, docs, version bump, released (user sign-off)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.30.0. adr-audit classifies template profiles (canonical/madr/nygard/unknown, fence-aware linear heuristic) and flags MADR/Nygard files advisorily. Migrate skill gains Pattern G (MADR mapping) and Pattern H (Nygard lift). Optional informational template.profile in config schema. ADR-003 records the input contract. Fixtures for both formats plus hand-migrated lint-clean counterparts; 13 tests. Unblocks task-11 (catalog listing).
<!-- SECTION:FINAL_SUMMARY:END -->
