---
id: TASK-67
title: Acceptance lint cannot resolve cross-ADR references (single-path scoping)
status: Done
assignee: []
created_date: '2026-07-30 21:52'
updated_date: '2026-07-30 23:07'
labels:
  - adr
  - lint
  - lifecycle
dependencies: []
references:
  - 'bin/adr:440-469'
  - 'bin/adr-lint:836-899'
modified_files:
  - bin/adr
  - bin/adr-lint
  - tests/test_adr_lifecycle.py
  - tests/test_adr_lint.py
  - templates/adr-kit-guide.md
priority: medium
ordinal: 72500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr accept` runs its strict lint against a single ADR file, so the consistency gate can never resolve any reference that points at another ADR.

**Reproduced 2026-07-30** while accepting ADR-017:

```
$ python3 bin/adr accept ADR-017          # supersedes: ["ADR-001"] in frontmatter
adr: acceptance blocked: strict lint failed: {"advisory": 0, "fail": 1, ...}

$ python3 bin/adr-lint --strict docs/adr/ADR-017-....md
  consistency FAIL: supersedes target ADR-001 not found

$ python3 bin/adr-lint --strict docs/adr   # same ADR, whole directory
  All linted ADRs pass at the configured severity.
```

**Cause.** `bin/adr:461` passes `str(path)` — one file — to `adr-lint`. `detect_frontmatter_consistency` (`bin/adr-lint:836`) builds its `records` map from exactly the files it was handed, then at lines 871-892 looks up `supersedes` and `superseded_by` targets inside that map. With one record, every cross-reference resolves to `None` and reports "not found".

**Scope is wider than supersession.** Any consistency check that reads another ADR's frontmatter is dead at accept time. `supersedes`/`superseded_by` are the two visible today; the same map is the lookup for anything added later.

**Not currently blocking.** The lifecycle has a working path: accept the successor while `supersedes` is still empty, then `bin/adr supersede OLD --by NEW`, which writes both sides in one transaction and runs no strict lint. That is the order ADR-017 was accepted in. So this is a latent trap, not a broken workflow — it only bites someone who fills `supersedes` in by hand before accepting, and the error message ("target not found") points at the ADR rather than at the scoping.

**Design question to answer first.** Naively passing the directory instead of the file is wrong: an unrelated failing ADR elsewhere in the set would then block this acceptance. The fix needs the whole set as *lookup context* while reporting on one file only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `bin/adr accept` succeeds on an ADR whose frontmatter already declares a valid `supersedes` target, without needing the accept-then-supersede ordering
- [x] #2 Findings reported by the acceptance lint still concern only the ADR being accepted; an unrelated failing ADR elsewhere in the directory does not block the acceptance
- [x] #3 A regression test covers both: cross-reference resolves, and an unrelated broken ADR in the same directory does not leak into the verdict
- [ ] #4 If the chosen fix is to keep the ordering requirement instead of widening the lookup, `bin/adr accept` says so in its error message rather than reporting 'target not found'
- [x] #5 The supersession workflow in .claude/adr-kit-guide.md is corrected once the fix lands: if `bin/adr accept` learns to resolve cross-references, the accept-first ordering caveat is removed; if the ordering stays, it is kept and the error message is improved to match
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-30 21:57
---
Documented the workaround in `.claude/adr-kit-guide.md` (Supersession section) on 2026-07-30, rather than leaving the trap undocumented while this task is open. Two things were added there:

1. The supersession steps now name `bin/adr accept` and `bin/adr supersede` explicitly, with the accept-first-then-link ordering and the reason it is load-bearing.
2. A second, separate defect found in the same run: when the superseded ADR has **no** `## Status History` block, `bin/adr supersede` drops its original acceptance date. `command_supersede:594` overwrites frontmatter `date` with the supersession date, `set_status_line` replaces the Status line that held it, and the freshly created history block contains only the Superseded entry. On ADR-001 the string `2026-05-31` went to zero occurrences in the file; it was restored by hand with `changed_by: unknown`.

That second defect is arguably its own task — it is data loss in an immutable record rather than a lint-scoping problem, and it will hit every pre-status_history ADR that gets superseded. Split it out if this task's fix does not naturally cover it.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved by widening the lookup, not by keeping the ordering. **AC #4 does not apply** — the "target not found" message is gone because the lookup now resolves.

**Why widening rather than a better message.** Single-file scoping rejected a *valid* state, not merely a legal one described badly. `bin/adr supersede` accepts a `Proposed` successor and writes both sides of the link; after that, `bin/adr accept` was unconditionally blocked. Keeping the ordering would have preserved a real workflow bug and only reworded it.

**Implementation.**

- `bin/adr-lint:401` `_path_key` and `:416` `merge_lookup_context` — corpus assembly, identity by resolved and case-folded path.
- `bin/adr-lint:872` `detect_frontmatter_consistency` gains `report_files`: `files` is the lookup corpus, `report_files` narrows which records may *produce* a finding. Gate presence moved to the reported set, since that is a per-record property rather than a cross-reference.
- `bin/adr-lint:1601` new opt-in `--context-dir`; `:1668` wires corpus versus targets. Plain `adr-lint <file>` is unchanged, so no other caller shifts.
- `bin/adr:549` — `bin/adr accept` passes `--context-dir <adr_dir>`.

The path dedupe is load-bearing: the context directory contains the target, and without resolved-path identity the same file counts twice and manufactures a `duplicate ADR-NNN` finding against the very ADR being accepted. Pinned by a test.

**Verified independently on a scratch set** rather than taken from the report:

- ADR-002 with `supersedes: ["ADR-001"]` already populated → `accepted: ADR-002-...md`. This is the exact invocation that previously failed.
- AC #2, the real risk of widening: added a deliberately malformed ADR-004 (5 lint findings against it), then accepted an *unrelated* ADR-003 → `accepted`. The broken ADR does not leak into the verdict.
- AC #1 also holds for the loss case that motivated this: superseding a pre-history ADR now preserves its acceptance date (TASK-68, verified in the same run).

A half link still blocks, correctly, and now says what is actually wrong: hand-writing `supersedes` without touching the old ADR yields `consistency: supersedes ADR-001 but ADR-001.superseded_by is not ADR-002`.

**AC #5, documentation.** `templates/adr-kit-guide.md` is the canonical shipped copy and it still described hand-editing the old ADR. Rewritten to name `bin/adr accept` and `bin/adr supersede`, state that steps 3 and 4 may run in either order, explain why the commands beat five coupled hand edits, and record the one thing they cannot recover. Worth noting: `.claude/adr-kit-guide.md` is gitignored (`.gitignore:23`), so my earlier documentation of the ordering caveat lived only in an untracked file and would have shipped nothing — the implementing agent caught that and corrected me.

**One unrequested change, flagged so it can be reverted on its own.** `bin/adr:557` now appends the failing findings to the acceptance error rather than only the counts, turning `strict lint failed: {"advisory": 0, "fail": 1, ...}` into the same plus the actual finding. That opacity is what made this defect hard to diagnose in the first place. It required one added assertion in an existing test — the only pre-existing test line modified.

**Behaviour changes worth knowing.** `bin/adr accept` now reads every ADR in the directory for lookup (negligible at 17 files; the repo gate scan is unchanged because `_wanted_gates` is scoped to reported records). Duplicate ADR numbers do not newly block acceptance — tested rather than assumed: a duplicate of the target's own number is rejected earlier by `find_adr_file`, and an unrelated duplicate keys its finding to the other number and is caught by `adr-index` as before.

Verification: `bin/adr-lint --strict docs/adr` 17/17 PASS, 0 FAIL. `tests/test_adr_lifecycle.py` + `tests/test_adr_lint.py` 39 passed (was 24). Teeth confirmed by removing `--context-dir` from the accept path (both TASK-67 tests fail) and by reducing `_path_key` to `str(path)` (the dedupe pin fails with exactly the manufactured duplicate finding).</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
