---
id: TASK-32.3
title: Make ADR enforcement use exact staged Git semantics
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 20:12'
labels:
  - security
  - git
  - staging
  - F-04
  - F-05
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
modified_files:
  - bin/adr-judge
  - bin/adr-judge-precommit
  - bin/adr-mcp
  - templates/githooks/pre-commit
  - .githooks/pre-commit
  - .github/actions/adr-judge/action.yml
  - skills/judge/SKILL.md
  - skills/review/SKILL.md
  - skills/guardian/SKILL.md
  - tests/test_adr_judge_precommit.py
  - tests/test_adr_git_diff_semantics.py
parent_task_id: TASK-32
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resolve source-audit F-04 and F-05 by parsing Git paths without quoting bypasses and evaluating required content from the staged/post-diff snapshot rather than the working tree.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Unicode, whitespace, tab, quote, rename, and delete paths cannot bypass scoped rules.
- [x] #2 require_pattern evaluates the staged/post-diff result for cached diffs and does not depend on unstaged working-tree content.
- [x] #3 Non-Git explicit diff use remains deterministic with documented fallback behavior.
- [x] #4 Partial-stage and Git-quoted-path regression tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory every judge caller and distinguish staged Git invocation from explicit diff-file/MCP use.
2. Replace ad hoc diff-header parsing with Git-compatible quoted-path decoding and explicit old/new path state.
3. Add an explicit staged-snapshot mode used by pre-commit; read blobs from the index and handle added, modified, renamed, and deleted files.
4. Retain a deterministic post-image reconstruction fallback for non-Git explicit diffs where complete enough, otherwise fail closed for require rules rather than reading the working tree.
5. Add Unicode/whitespace/tab/quote/rename/delete and partial-staging regressions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added Git C-quoted path decoding for octal UTF-8 bytes, tabs, quotes, backslashes, spaces, renames, and deleted-file post paths. Diff records now retain old/new/deleted/new-file state instead of only a stripped `+++` string.

Added explicit `--snapshot diff|staged|worktree`. Pre-commit hook and framework wrapper use `staged` and read exact blobs through `git show :path`; PR/review/guardian range workflows use the checked-out post-image; MCP arbitrary diffs use deterministic diff mode. Diff mode reconstructs complete new files and fails closed for modified patches that cannot prove the full post-image. Deleted files fail required rules.

Regression coverage proves both partial-staging directions, staged rename/delete, Git-quoted Unicode scope matching, quoted tab/quote decoding, unquoted spaces, new-file reconstruction, and incomplete explicit-diff fail-closed behavior. Focused judge/MCP/security/performance suite: 93 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved F-04 and F-05. Scoped enforcement now understands Git-quoted paths, and require rules consume the explicitly selected post-change snapshot. Built-in staged callers read the index, so unstaged content can neither hide nor invent a commit violation; arbitrary incomplete diffs fail closed instead of consulting unrelated working-tree state.
<!-- SECTION:FINAL_SUMMARY:END -->
