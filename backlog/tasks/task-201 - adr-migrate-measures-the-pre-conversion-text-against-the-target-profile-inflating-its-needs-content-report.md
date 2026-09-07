---
id: TASK-201
title: >-
  adr-migrate measures the pre-conversion text against the target profile,
  inflating its needs-content report
status: To Do
assignee: []
created_date: '2026-09-06 15:11'
updated_date: '2026-09-07 20:03'
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

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-09-07 20:03
---
THE PROPOSED FIX DOES NOT REMOVE THE OVER-REPORT. Verified 2026-09-07 by printing the role-to-title map rather than by reading the code.

The record proposes resolving the before-text with `detect_profile(before)` instead of the target profile. That corrects which profile is applied, but the delta at `bin/adr-migrate:182-186` compares the two sets by heading TITLE, and `unfilled_required_sections` returns titles (`[title for title, _ in _unwritten_required_sections(...)]`, `bin/adr_format.py:887`). Three required roles are renamed across profiles:

```
role            nygard / canonical          madr
context         ## Context                  ## Context and Problem Statement
decision        ## Decision                 ## Decision Outcome
alternatives    ## Alternatives Considered  ## Considered Options
```

Four roles keep their title (status, consequences, related, references), which is why the defect looks intermittent.

So with the proposed fix, a nygard record whose `## Context` is present but empty yields a before-set holding `Context` and an after-set holding `Context and Problem Statement`. The membership test still passes and the section is still reported as newly unfilled, although it was already unwritten before the run. That is precisely the over-report AC#2 asks to eliminate, and it survives.

DIRECTION, replacing the one in the description: compare by ROLE. Either build both sets from `_unwritten_required_sections` keyed on the role rather than the rendered title, or map source titles to target titles through `PROFILE_HEADINGS` before the difference. The cross-profile fixture AC#2 asks for should use one of the three renaming roles, since a fixture built on `## References` would pass against the broken code.

Severity unchanged and still not a release blocker: over-reporting names a hole the author genuinely has, which is the conservative direction to fail in.
---
<!-- COMMENTS:END -->
