---
id: TASK-227
title: Edit-time ADR context reaches apply_patch edits in Codex and OpenCode
status: Done
assignee: []
created_date: '2026-10-11 16:34'
updated_date: '2026-10-11 16:48'
labels:
  - hooks
  - codex
  - opencode
dependencies: []
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Codex 0.162.1 reports every edit as tool_name apply_patch with the patch in tool_input.command (observed payload: '*** Begin Patch / *** Update File: bin/adr_llm.py / ... / *** End Patch'). hooks/adr_hook_core.py _safe_edit_path reads only file_path, filePath, path and notebook_path, so evaluate returns noop and Codex never gets pre-edit or post-edit ADR context (DEF-31). tests/test_hook_protocol.py:145-156 sends apply_patch with a file_path Codex never sends, so the gap passed CI. OpenCode 1.19.0 has the same tool, with the patch in args.patchText, and rewrites write and edit calls to apply_patch when write is not enabled (observed in the 1.19.0 binary). opencode/plugin.ts:420 and :438 return before calling the hook core because toolPath finds no file path (DEF-38).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The hook core reads the target paths from an apply_patch patch in tool_input.command or tool_input.patchText: Add File, Update File, Delete File and Move to headers
- [x] #2 A multi-file patch queries every in-workspace path, bounded at the query limit of 32; paths outside the workspace are dropped as before
- [x] #3 Content lines that only look like headers do not count as paths
- [x] #4 The OpenCode plugin forwards apply_patch calls that carry patchText
- [x] #5 Tests use the observed Codex and OpenCode payload shapes and fail on the old code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first: the 7 new hook-core tests in tests/test_hook_protocol.py fail on the old code (kind noop for every Codex and OpenCode patch shape), and the OpenCode plugin test fails for apply_patch with the plugin fix reverted while its filePath case passes. Codex 0.162.1 fires the kit's hooks for apply_patch under its own Edit|MultiEdit|Write matcher (observed with that matcher, diag2 run), so the matcher was not the gap; the hook core was.

The hook core now reads the header lines of an apply_patch patch from tool_input.command (Codex) or tool_input.patchText (OpenCode 1.19.0, observed in the binary): Add File, Update File, Delete File and Move to. Hunk lines start with +, -, a space or @@, so they never match. Paths outside the workspace are dropped as before. A patch's files are ranked in one query: the hook shows at most the configured limit either way, and one index load per file cost about ten times as much (114 ms against 11 ms for 8 files on this repository). The query takes at most 32 paths of at most 240 characters and raised on more, which would have emptied the context for the whole edit; the hook now stays within both bounds (a mutation without the bound loses ADR-001). The OpenCode plugin forwards apply_patch calls that carry patchText.

Found on the way: the OpenCode smoke's editSystem assertion passes on prompt context alone, because its fixture ADR uses flow-style lists that the index drops (adr-lint rejects them) and scopes nothing; the new plugin test uses an ADR scoped to src/** so only the edit can bring it in. One run failed that new test's filePath case: the hook's duplicate_event keyed the previous event of session 'before' from an earlier run, because the signature names neither the workspace nor the input. That is TASK-228, together with the PR guard bypass it causes.
<!-- SECTION:NOTES:END -->
