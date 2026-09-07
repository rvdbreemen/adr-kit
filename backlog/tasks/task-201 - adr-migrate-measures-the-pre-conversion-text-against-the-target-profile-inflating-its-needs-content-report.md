---
id: TASK-201
title: >-
  adr-migrate measures the pre-conversion text against the target profile,
  inflating its needs-content report
status: To Do
assignee: []
created_date: '2026-09-06 15:11'
labels:
  - bug
  - migrate
dependencies: []
priority: low
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bin/adr-migrate:184-185 computes the delta as unfilled_required_sections(after, to_profile) minus unfilled_required_sections(before, to_profile). The second call applies the TARGET profile to the PRE-conversion text. On a cross-profile conversion the source headings still carry source-profile names, so most of them do not match and are silently skipped (bin/adr_format.py: an unmatched heading is continued past, it does not raise), which under-reports the 'before' set and therefore over-reports the delta.

The effect is bounded today because the reported set is used only to print 'needs content: ## <heading>' lines, so the failure mode is naming a hole the author already had rather than one the migration opened. That is exactly the distinction the delta exists to draw, so the code contradicts its own comment.

The fix is to resolve the before-text with its own detected profile (detect_profile(before)) rather than the target. Found while implementing TASK-199; not fixed there because it needs its own cross-profile fixture to prove, and TASK-199's change surface was already two coupled files.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The before-set is computed with the profile the pre-conversion text actually has
- [ ] #2 A cross-profile fixture proves the delta no longer names a section that was already unwritten before the run
<!-- AC:END -->
