---
id: TASK-175
title: Prepare upstream OpenCode migration fix for legacy name-column failures
status: In Progress
assignee: []
created_date: '2026-08-16 20:33'
updated_date: '2026-08-16 20:35'
labels:
  - opencode
  - upstream
  - sqlite
  - migration
dependencies: []
references:
  - 'https://github.com/anomalyco/opencode/issues/40470'
  - 'https://github.com/anomalyco/opencode/issues/32430'
  - 'https://github.com/anomalyco/opencode/pull/37707'
  - 'https://github.com/anomalyco/opencode/pull/41610'
priority: high
type: bug
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate and, if necessary, improve the upstream OpenCode fixes for startup failures reporting no such column: name. Cover both legacy __drizzle_migrations journals and legacy workspace tables, avoid duplicating an existing upstream fix, and offer a tested contribution upstream.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The legacy Drizzle journal path no longer queries a missing name column and maps known created_at entries safely.
- [ ] #2 The workspace-name migration preserves existing names and defaults missing legacy names without querying a missing column.
- [ ] #3 Focused migration tests and relevant Windows checks pass.
- [ ] #4 The upstream contribution clearly references existing PRs #37707 and #41610 and does not duplicate accepted work.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: OpenCode
created: 2026-08-16 20:35
---
Decision 2026-08-16: do not create a duplicate PR. Existing PR #37707 covers legacy Drizzle journals without a name column, and PR #41610 covers the legacy workspace-name migration. Their focused migration tests are reported passing; the overall Windows check on #41610 failed in an unrelated app UI test. Local Windows reproduction evidence was posted to both PRs. Task remains In Progress pending upstream maintainer action.
---
<!-- COMMENTS:END -->
