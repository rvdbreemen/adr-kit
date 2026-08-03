---
id: TASK-103
title: >-
  Make plan-exit reach the branch that handles it, and drive the dispatch layer
  in the test
status: To Do
assignee: []
created_date: '2026-08-03 19:33'
labels:
  - hooks
  - bug
dependencies: []
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R3 does not happen at all. An agent leaves plan mode and nothing asks whether the plan makes an undocumented decision — the cheapest moment to notice one, and the only moment where the answer can still shape the implementation instead of justifying it.

**Cause.** `hooks/manifest.json` sets `"id": "plan-exit", "command": "plan-exit"` while its sibling sets `"id": "pr-create", "command": "pre-tool-use"`. `run-hook.cmd` passes the command verbatim as `--event`, `normalize()` lets that argument win over the payload, and `re.sub(r'[^a-z]','','plan-exit')` is `planexit`, which is absent from `EVENT_ALIASES` — so `evaluate()` falls through to `return "", "noop"`. Measured: `--event plan-exit` returns 0 bytes; the identical payload with `--event pre-tool-use` returns the full injection.

**Why no test caught it.** `tests/test_adr_plan_exit_hook.py::_envelope` calls `core.normalize(payload, client, None)` with event `None`, so the payload wins and the failing step is never exercised. Twenty-four tests pass over a dead path, and the CHANGELOG credits the feature, so nobody is looking.

No ADR needed: this is the fourth instance of a pattern ADR-004 already governs.

Reported by a subagent; **verify by reproduction before fixing**, since it is going into a release.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The failure is reproduced first: `--event plan-exit` returns 0 bytes on a payload where `--event pre-tool-use` returns an injection
- [ ] #2 Either `"planexit": "PreToolUse"` joins `EVENT_ALIASES` or the manifest entry takes `"command": "pre-tool-use"` like `pr-create` does; the generated trees are regenerated
- [ ] #3 A dispatch-level test pipes a payload through `hooks/adr-hook.py --client <c> --event <manifest command>` for every event in `manifest.json` and asserts non-empty output where the fixture warrants it
- [ ] #4 `docs/client-support.md:14` stops asserting `Plan exit | supported (ExitPlanMode)` while it is false
<!-- AC:END -->
