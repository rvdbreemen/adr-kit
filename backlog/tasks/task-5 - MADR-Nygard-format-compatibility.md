---
id: TASK-5
title: MADR / Nygard format compatibility
status: To Do
assignee: []
created_date: '2026-05-31 13:20'
updated_date: '2026-06-12 21:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Adoption lever: lower switching cost from MADR (2.2k) and Nygard/adr-tools (5.5k). Teach /adr-kit:migrate (and optionally bin/adr-import) to recognize and map MADR headings (Context and Problem Statement, Considered Options, Decision Outcome, frontmatter/* Status:) and Nygard's lighter shape into the canonical seven sections. Add template-profile detection in the schema; adr-audit flags existing MADR/Nygard ADRs. Most design-uncertain, sequenced last.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 migrate recognizes and maps MADR and Nygard formats into the canonical seven sections
- [ ] #2 Template-profile detection added to schema; adr-audit flags existing MADR/Nygard ADRs
- [ ] #3 MADR + Nygard fixtures migrate to canonical and pass bin/adr-lint
- [ ] #4 An ADR is authored for this input-contract change (architecturally significant)
- [ ] #5 pytest green, adr-lint clean, docs, version bump, released (user sign-off)
<!-- AC:END -->
