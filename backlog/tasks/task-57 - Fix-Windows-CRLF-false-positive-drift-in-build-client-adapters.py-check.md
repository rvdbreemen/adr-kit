---
id: TASK-57
title: Fix Windows CRLF false-positive drift in build-client-adapters.py --check
status: Done
assignee: []
created_date: '2026-07-26 13:57'
updated_date: '2026-07-30 20:44'
labels:
  - bug
  - release
  - windows
dependencies: []
references:
  - scripts/build-client-adapters.py
  - docs/RELEASING.md
priority: medium
ordinal: 57500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found during the v0.42.0 release (TASK-56). On a Windows checkout with core.autocrlf, `python scripts/build-client-adapters.py --check` reports drift on 13 generated files (codex/, copilot/, hooks/hooks.json, templates) while `git diff` is empty: the generator emits LF, git materializes CRLF in the working copy, and the check compares raw bytes on disk.

Consequences:
- The release runbook's step-2/step-4 gate fails spuriously on the certification machine (which is Windows per the hook reference corpus), forcing the maintainer to trust Linux CI instead of the local gate.
- Running the suggested fix command rewrites all 13 files as LF, which then shows as phantom modifications until the next checkout — noise that can mask real drift.

Fix direction: normalize line endings before comparing in --check (e.g. compare `content.replace(b"\r\n", b"\n")` on both sides), or have the writer honor the existing working-copy ending. Keep the byte-exact comparison for content, only relax the EOL dimension. Add a regression test that a CRLF-materialized adapter tree passes --check.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 --check passes on a Windows checkout where git materialized CRLF and content is otherwise identical
- [ ] #2 --check still fails on real content drift (existing behaviour preserved)
- [ ] #3 Regression test covers the CRLF-materialized tree case
- [ ] #4 Release runbook needs no Windows-specific caveat afterwards
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed in `scripts/client_generation.py` with two regression tests.

**Reproduced first.** The bug did not reproduce on a plain `--check` run, because `.gitattributes` pins `bin/*`, `scripts/*.py`, `.githooks/*`, `templates/githooks/*`, `codex/bin/*` and `copilot/bin/*` to `eol=lf`. It does **not** pin `hooks/hooks.json`, `codex/hooks/*`, `copilot/hooks.json` or the `codex/templates/*` and `copilot/templates/*` trees — exactly the files the report named. Materialising CRLF into `codex/hooks/hooks.json` reproduced it immediately: exit 1, "Client adapter drift", with byte-identical content.

**Fix.** New `_same_content(actual, expected)` helper replaces the bare `actual == content` comparison in the drift loop. It tries byte equality first, and only if that fails compares with `\r\n` collapsed to `\n`. Content is still compared byte for byte, so a single changed character is still drift; only the EOL dimension is relaxed, which is what the task asked for.

**Binary guard.** Normalisation is refused when either side contains a NUL byte — the same binary heuristic git uses. This matters concretely: `hooks/bin/windows-x64/` ships prebuilt `.exe` and `.pdb` files, and a `0D 0A` pair inside a binary is data, not a line ending. Collapsing it would make two genuinely different binaries compare equal, turning a drift-detection fix into a drift-detection hole.

**Verified** against all three cases, isolated from a concurrent agent that was editing `bin/adr-mcp` (its mirrors legitimately drifted at the time, which initially made my first test read as a failure — the harness now filters those paths):

| case | drift reported | expected |
|---|---|---|
| CRLF, content identical | none | none |
| real content change | `codex/hooks/hooks.json` | detected |
| real change *and* CRLF | `codex/hooks/hooks.json` | detected, not masked |

**Tests added** to `tests/test_client_adapter_generation.py`: one that materialises the whole generated tree as CRLF and asserts zero drift, then adds a real edit and asserts it is still caught; and one unit test pinning `_same_content` behaviour including the binary refusal and the missing-file case. Suite: 11 passed.

**Criterion 4 needed no work.** `docs/RELEASING.md` carries no Windows or CRLF caveat — the maintainer had simply been distrusting the local gate and relying on Linux CI. That workaround is now unnecessary rather than documented away.

Same family as TASK-64 (Windows non-ASCII path handling): platform-specific text behaviour that a Linux-only CI run cannot surface.
<!-- SECTION:FINAL_SUMMARY:END -->
