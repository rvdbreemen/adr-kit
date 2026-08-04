---
id: TASK-128
title: test_codex_payload_is_synced failed once in a full run and is not reproducible
status: To Do
assignee: []
created_date: '2026-08-04 18:31'
labels:
  - tests
  - flake
  - isolation
dependencies: []
priority: low
ordinal: 98500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Observed once, on 2026-08-04, in a full local run on Windows:

```
FAILED tests/test_agent_installer.py::test_codex_payload_is_synced
1 failed, 1575 passed, 13 skipped in 654.26s
```

The test runs `scripts/sync-agent-plugins.py --check` against the **real** repository tree, so it is sensitive to anything another test writes there.

What was ruled out afterwards, in this order:

- Rerun in isolation: passes.
- Whole `tests/test_agent_installer.py` module: 39 passed.
- Every module that collects before it (`tests/test_a*.py`, 1137 tests): all passed.
- `codex/hooks/hooks.json` on disk versus `HEAD`: byte-identical, 2537 bytes, LF both sides. Git flags the file modified but `git diff` is empty — a line-ending attribute artefact, not content.
- `build-client-adapters.py --check`: `changed=0, written=0`.
- The immediately preceding full run of the same tree: 1575 passed, no failure.

So it is not a stale tree and not a straightforward ordering dependency within the modules that precede it. What remains is a test that asserts on shared mutable state — the checked-out repository — while other tests in the same run may write to it. That is worth removing regardless of whether this particular failure ever returns: a test whose subject is the working tree cannot be run safely alongside tests that modify it, and the failure it produces names the wrong thing.

Direction: give the sync check its own copy of the tree, or assert on a snapshot taken at session start rather than on the live directory. Then a genuine desync still fails, and a neighbouring test writing a file does not.

If it recurs, capture the `--check` output — it names the file that differs, which this run did not preserve.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The sync check runs against a copy or a snapshot, not the live working tree
- [ ] #2 A deliberate desync still fails the test
- [ ] #3 A neighbouring test writing into the tree cannot fail it
<!-- AC:END -->
