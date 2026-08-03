---
id: TASK-90
title: >-
  Ship adr_pr_guard.py to the client mirrors, and smoke-test every generated
  hook tree
status: To Do
assignee: []
created_date: '2026-08-03 18:57'
updated_date: '2026-08-03 18:57'
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
- [ ] #1 hooks/adr_pr_guard.py is listed in HOOK_RUNTIME_FILES and mirrored to codex/ and copilot/
- [ ] #2 Each generated hooks/adr-hook.py runs a synthetic session-start envelope and exits 0 on all three clients
- [ ] #3 A CI step executes every generated hook entrypoint once per client and fails on a non-zero exit, so an undeclared import cannot pass again
- [ ] #4 The fix ships as v0.44.1, since v0.44.0 is released with the defect
<!-- AC:END -->
