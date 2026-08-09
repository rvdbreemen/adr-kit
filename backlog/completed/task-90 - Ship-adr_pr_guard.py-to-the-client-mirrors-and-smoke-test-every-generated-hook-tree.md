---
id: TASK-90
title: >-
  Ship adr_pr_guard.py to the client mirrors, and smoke-test every generated
  hook tree
status: Done
assignee: []
created_date: '2026-08-03 18:57'
updated_date: '2026-08-03 20:15'
labels:
  - P0
  - regression
  - hooks
  - client-parity
  - v0.44.0
dependencies: []
priority: high
ordinal: 95500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Every adr-kit hook is dead on Codex and Copilot in the released v0.44.0.** Verified, not inferred:

```
$ echo '{"session_id":"t","cwd":"..."}' | python codex/hooks/adr-hook.py --client codex-cli --event session-start
ModuleNotFoundError: No module named 'adr_pr_guard'
exit=1
```

`codex/hooks/adr-hook.py:17` and `copilot/hooks/adr-hook.py:17` both do `from adr_pr_guard import judge_branch, looks_like_pr_create`, and neither `codex/hooks/adr_pr_guard.py` nor `copilot/hooks/adr_pr_guard.py` exists. The import sits at module scope, outside `main()`'s `except BaseException`, so **every** hook event on those clients dies — not only the PR guard. No session orientation, no per-prompt retrieval, no edit-tier injection.

**Because hooks fail open by design, the user sees nothing.** No error, no context, silence. That is the worst shape this defect could take: adr-kit appears installed and does nothing.

**Root cause is a blind spot, not a typo.** `scripts/client_generation_model.py:35` `HOOK_RUNTIME_FILES` lists eight hook files and omits `hooks/adr_pr_guard.py`. The drift check only compares declared files, so `python scripts/build-client-adapters.py --check` reports `changed=0` and exits 0 over a dead tree. `.github/workflows/validate.yml:149` runs exactly that command, so CI is green.

Introduced by commit `323a38a` (TASK-76, the pre-PR branch guard); `git tag --contains 323a38a` returns `v0.44.0`. Released, on both `main` and `dev`.

**Fix the class, not only the instance.** Adding the filename repairs today's break; a declared-file-list can never see the next module an entrypoint imports but nobody declared. A per-client import smoke test would have caught this on the PR that introduced it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 hooks/adr_pr_guard.py is listed in HOOK_RUNTIME_FILES and mirrored to codex/ and copilot/
- [x] #2 Each generated hooks/adr-hook.py runs a synthetic session-start envelope and exits 0 on all three clients
- [x] #3 A CI step executes every generated hook entrypoint once per client and fails on a non-zero exit, so an undeclared import cannot pass again
- [x] #4 The fix ships as v0.44.1, since v0.44.0 is released with the defect
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`adr_pr_guard.py` joined `HOOK_RUNTIME_FILES` in `scripts/client_generation_model.py`, and both generated trees now carry it.

Reproduced before fixing: a `gh pr create` payload through `codex/hooks/adr-hook.py` and `copilot/hooks/adr-hook.py` gave `rc=1`, 0 bytes, `ModuleNotFoundError: No module named 'adr_pr_guard'` — and because the import is at module scope, that was the answer for *every* event, not only the guard.

The drift check was confirmed to discriminate: deleting `codex/hooks/adr_pr_guard.py` and running `build-client-adapters.py --check` now exits 1; regenerating and re-running exits 0. Before the declaration it reported `changed=0` over the same broken state.

`tests/test_adr_hook_dispatch_matrix.py` adds the invariant rather than the file list: every module the generated entrypoint imports must resolve inside that client's tree. It fails on the pre-fix state for both clients. The same module drives every manifest event through the real process on all three clients — 23 cases, all green.

Shipped in v0.44.1.
<!-- SECTION:FINAL_SUMMARY:END -->
