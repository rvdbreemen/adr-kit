---
id: TASK-225
title: A blocked commit prints why it was blocked
status: Done
assignee: []
created_date: '2026-10-11 16:23'
updated_date: '2026-10-11 16:25'
labels: []
dependencies: []
references:
  - templates/githooks/pre-commit
ordinal: 69000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
templates/githooks/pre-commit:180 runs exec 9>"$ROOT/.git/adr-kit-judge.lock" 2>/dev/null || true. A bare exec with redirections applies them to the shell itself, so stderr goes to /dev/null for the rest of the hook wherever flock exists. A refused commit then prints nothing, including the violation report at :276 (DEF-01). It was reproduced with Codex 0.162.1, Copilot 1.0.95 and OpenCode 1.19.0 on Linux, and in the 2026-10-11 sweep. The lock path also assumes .git is a directory, which it is not in a linked worktree.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A refused commit prints the judge's violation report on stderr when flock is present
- [x] #2 The lock lives at git's own path for it, so a linked worktree works too
- [x] #3 A test runs the real hook with flock on PATH and asserts the report reaches stderr
- [x] #4 templates/githooks/pre-commit and .githooks/pre-commit stay identical, and the generated client copies are regenerated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first with tests/test_pre_commit_reports_refusals.py, both tests failing on the old hook:
- In the main repository, a refused commit printed an empty stderr (DEF-01).
- In a linked worktree, the hook said 'another ADR judge is running' (DEF-12), because $ROOT/.git is a file there.

The fix:
- The 2>/dev/null now sits inside { exec 9>...; }, so it covers only the open.
- The lock lives at git rev-parse --git-common-dir, which is shared by all worktrees.
- When the lock cannot be opened, the hook runs without a lock and no longer reports a rival.

Both tests pass. templates/githooks/pre-commit and .githooks/pre-commit are identical, and the codex/ and copilot/ copies are regenerated (build-client-adapters --check changed=0).
<!-- SECTION:NOTES:END -->
