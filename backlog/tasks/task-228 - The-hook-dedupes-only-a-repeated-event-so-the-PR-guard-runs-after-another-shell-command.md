---
id: TASK-228
title: >-
  The hook dedupes only a repeated event, so the PR guard runs after another
  shell command
status: Done
assignee: []
created_date: '2026-10-11 16:49'
updated_date: '2026-10-11 16:50'
labels:
  - hooks
  - pr-guard
dependencies: []
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
hooks/adr-hook.py:115 drops an event when duplicate_event says the session's previous event had the same signature, before the PR guard runs. hooks/adr_hook_core.py:186-214 builds that signature from the event, the tool name, the file path, the prompt and the agent id. It names neither the shell command nor the workspace, and an apply_patch edit has no file path. Bash has a PreToolUse hook and no PostToolUse hook (hooks/hooks.json, codex/hooks/hooks.json), so in the usual flow, git push followed by gh pr create, the second command has the same signature as the first: the hook exits 0 without running the PR guard (reproduced at the duplicate_event level). Consecutive apply_patch edits to different files are duplicates of each other for the same reason. The state file is keyed by session id alone in the OS temp directory, so a session id reused in another workspace is matched against that workspace's event; this made a plugin test fail once. tests/test_adr_pr_guard.py's end-to-end test sends no session_id, which skips the dedupe entirely.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A repeated identical event is still a duplicate
- [x] #2 Two different shell commands in a row are not duplicates, and gh pr create after git push reaches the PR guard
- [x] #3 Consecutive apply_patch edits to different files are not duplicates
- [x] #4 The same session id in another workspace is not a duplicate
- [x] #5 Tests send a session id, as real clients do, and fail on the old code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first: with the old signature, duplicate_event called for PreToolUse Bash 'git push -u origin feature' and then 'gh pr create --fill' in one session returned False and then True, so hooks/adr-hook.py returned before _pr_guard. Both new tests fail on the old code: tests/test_adr_pr_guard.py runs the real hook twice in one session (git push, then gh pr create) and expects the guard's 'ADR check skipped' notice; tests/test_hook_protocol.py checks that a repeated patch is a duplicate while a patch to another file, or the same session id in another workspace, is not.

The signature now names the workspace, the event, the tool name, a SHA-256 of the canonical tool input, the prompt and the agent id. A client that runs the hook from two registrations delivers one payload twice, which still matches; any other event does not. The commit floor and CI were never bypassed; the guard in front of them was, in the usual commit, push, PR flow. Hashing at most 64 KiB adds well under a millisecond.
<!-- SECTION:NOTES:END -->
