---
id: TASK-68
title: >-
  bin/adr supersede destroys the original acceptance date of pre-status_history
  ADRs
status: Done
assignee: []
created_date: '2026-07-30 21:58'
updated_date: '2026-07-30 23:07'
labels:
  - adr
  - lifecycle
  - data-loss
dependencies: []
references:
  - 'bin/adr:556-621'
  - docs/adr/ADR-001-llm-gates-opt-in.md
  - .claude/adr-kit-guide.md
modified_files:
  - bin/adr
  - tests/test_adr_lifecycle.py
  - templates/adr-kit-guide.md
priority: high
ordinal: 73500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Superseding an ADR that has no `## Status History` block permanently erases the date it was accepted. Accepted ADRs are supposed to be immutable historical record; this silently deletes a fact from one.

**Reproduced 2026-07-30** superseding ADR-001 by ADR-017. Before:

```
date: "2026-05-31"          # frontmatter
Accepted, 2026-05-31        # Status section
```

After `python3 bin/adr supersede ADR-001 --by ADR-017`, the string `2026-05-31` occurred **zero** times in the file.

**Three writes combine to lose it, none of them wrong alone:**

1. `bin/adr:594` — `old_data["date"] = args.date` overwrites frontmatter `date`. This is correct in isolation: ADR-003 shows `date` means "date of the current status" (it carries 2026-07-18, its supersession, while its history holds 2026-06-12 for the acceptance).
2. `set_status_line` (`bin/adr:188`) replaces the Status line, which for a pre-convention ADR is the *only* other place the acceptance date lived.
3. `append_status_history` (`bin/adr:204`) finds no existing block, so it creates one containing solely the new `Superseded` entry — there is nothing to preserve the earlier transition.

ADRs that already carry a `status_history` block are unaffected: their earlier entries survive, which is why ADR-003 looks correct and this went unnoticed.

**Blast radius.** Every ADR authored before the status_history convention. In this repository ADR-001 was the case; consuming projects that adopted adr-kit early have the same shape.

**Current state.** ADR-001 was repaired by hand: the recovered entry carries `changed_by: unknown` and `changed_via: unrecorded`, because the actor genuinely was never recorded and guessing one would be worse than the gap. The workaround is documented in `.claude/adr-kit-guide.md`.

**Suggested direction** (not prescriptive): before mutating, if the body has no `status_history` block, parse the existing Status line and seed the new block with that transition first. The status word and date are both present in the line being replaced. Where the line does not parse, refuse and say so rather than writing a lossy history — a supersession that quietly drops history is worse than one that stops and asks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Superseding an ADR that has no `## Status History` block preserves its original status and date as the first entry of the newly created block
- [x] #2 The recovered entry does not invent an actor: an unrecorded `changed_by` is represented as such, not as `adr-kit` or the current user
- [x] #3 Where the pre-existing Status line cannot be parsed into a status and a date, the command refuses with a clear message instead of writing a history that silently omits the earlier transition
- [x] #4 A regression test supersedes a fixture ADR that has a Status line but no status_history block, and asserts the original date still appears in the result
- [x] #5 ADRs that already carry a status_history block keep their existing behaviour, with a test pinning it
- [x] #6 The same audit is applied to the other mutating lifecycle paths (`mutate_status` at bin/adr:235 drives accept, reject and propose through the identical set_status_line + append_status_history pair)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented by the lifecycle-integrity agent; I verified it end to end before closing rather than taking the report on trust.

**The fix.** The sequencing was the trap: `append_status_history` runs *after* `set_status_line`, so parsing the body from inside it would have seeded the new transition and lost the original anyway. The seed is computed from the pre-mutation `(data, body)` and threaded in explicitly.

- `bin/adr:237` `read_status_line` — parses status word and date out of the Status line.
- `bin/adr:251` `prior_transition` — Status line first, frontmatter `status`/`date` for whichever half the prose omits, refusal when neither yields both.
- `bin/adr:282` `ensure_status_history` — no-op when a block exists; otherwise seeds the recovered entry, and skips it when the prior transition equals the one about to be appended.
- Called before any mutation at all three sites: `mutate_status` (drives accept/reject/propose), `command_document`, and `command_supersede` (both files seeded before either is written).

**Independently verified**, on a scratch set shaped exactly like ADR-001 was — `Accepted, 2020-01-15` with no `## Status History` block:

```
status_history:
  - date: 2020-01-15
    status: Accepted
    changed_by: unknown
    reason: Recovered from the record as it stood before this transition; ...
    changed_via: unrecorded
  - date: 2026-07-31
    status: Superseded
    ...
```

`2020-01-15` survives, and the actor is `unknown` rather than invented — matching the hand repair applied to the real ADR-001.

**A deliberate deviation from this task's suggested direction, and it is the right call.** The description proposed parsing the Status line and refusing when that fails. The implementation uses the Status line first and falls back to frontmatter, because a Status-line-only rule refuses recoverable records: a MADR `**Status:** Accepted` line does not parse, yet frontmatter carries both `status` and `date`. AC #3's refusal path is still reachable and tested, just narrower.

**Scope was widened correctly beyond the ACs.** `command_document` was a third caller with the same gap, found and fixed. `mutate_status` is covered parametrized over propose/accept/reject.

**Teeth confirmed** by the implementer and consistent with my own end-to-end run: stubbing `ensure_status_history` to a no-op fails 4 of the new tests, while the 2 behaviour-preservation pins keep passing — which is the correct signature.

**A new behaviour worth knowing:** a backdated `--date` can now produce `audit FAIL: entry 2 is earlier than its preceding entry`, where a single-entry history could not be out of order. Truthful history over gate-pleasing, but it is new.

**Follow-on found while verifying this.** The generated history was valid for adr-kit's own mini-parser but not for a real YAML parser: `changed_by: User: Test` is unparseable, and it took the whole block down. That turned out to already affect three shipped ADRs. Filed and fixed as TASK-70.

`templates/adr-kit-guide.md` — the canonical, shipped copy — still documented hand-editing the old ADR, which is exactly the lossy path this task removes. Rewritten to name the commands, state that either order works, and record what the tooling can and cannot recover. Note that `.claude/adr-kit-guide.md` is gitignored (`.gitignore:23`), so documenting only there would have shipped nothing; the agent caught that I had made exactly that mistake.

Verification: `bin/adr-lint --strict docs/adr` 17/17 PASS, 0 FAIL. `tests/test_adr_lifecycle.py` + `tests/test_adr_lint.py` 39 passed. Client mirrors regenerated through `scripts/build-client-adapters.py`; `--check` reports changed=0.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
