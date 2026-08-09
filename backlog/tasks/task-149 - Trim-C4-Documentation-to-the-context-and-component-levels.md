---
id: TASK-149
title: Trim C4-Documentation to the context and component levels
status: In Progress
assignee: []
created_date: '2026-08-09 10:35'
updated_date: '2026-08-09 12:31'
labels: []
dependencies: []
references:
  - docs/plans/kiss-simplification-plan.md
priority: low
ordinal: 120500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 4 of docs/plans/kiss-simplification-plan.md. Independent. C4-Documentation/ is 28 hand-written files, ~14k lines, with no generator, no DO-NOT-EDIT marker and no CI keeping it honest - a second prose copy of the code that must be re-verified by hand on every refactor, which is the exact rot adr-kit argues against. Keep c4-context and the component level (structure no single file shows); delete the eighteen c4-code-*.md files whose content the docstrings already carry. Update the document map in c4-component.md and any references from README/docs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 c4-code-*.md files are gone; context and component documents remain and their document map no longer references deleted files
- [ ] #2 No dangling links to C4 files from README.md, docs/ or spec.md
<!-- AC:END -->
