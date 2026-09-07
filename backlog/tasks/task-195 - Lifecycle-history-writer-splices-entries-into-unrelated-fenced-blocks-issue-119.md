---
id: TASK-195
title: >-
  Lifecycle history writer splices entries into unrelated fenced blocks (issue
  #119)
status: Done
assignee: []
created_date: '2026-08-26 21:01'
updated_date: '2026-09-07 20:01'
labels: []
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/issues/119'
  - bin/adr
  - bin/adr_catalog.py
priority: high
type: bug
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub issue #119. Reproduced 2026-08-26 against the repository checkout; every claim in the report holds.

`HISTORY_START_RE` (`bin/adr:73`) matches a `status_history:` block whether or not it is wrapped in a ```yaml fence. The writer `append_status_history` (`bin/adr:246-252`) assumes the fence exists and locates its insertion point with `body.find("```", start.end())` - the next triple backtick ANYWHERE in the rest of the document. Every ADR in this project ends with a fenced ```json Enforcement block, so on an unfenced record the entry is spliced into that block instead.

REPRODUCTION, two byte-identical fixtures differing only in the fence:

```
ADR-020 (unfenced)  accept -> exit 0, "accepted:"
                    ## Status History  : 1 entry  (the original, unchanged)
                    ## Enforcement     : 1 entry  (spliced before the ```json fence)
                    ADR-INDEX.json     : "Proposed"
ADR-021 (fenced)    accept -> exit 0, "accepted:"
                    ## Status History  : 2 entries (correct)
                    ## Enforcement     : 0
                    ADR-INDEX.json     : "Accepted"
```

Both frontmatters read `status: "Accepted"` afterwards. The index disagrees with the frontmatter on the unfenced one.

WHY THE INDEX GOES STALE, and why that is the severe part: `bin/adr_catalog.py:357-359` takes the LAST entry of the `## Status History` section in preference to the frontmatter, which is the correct precedence - a history block is the audit trail. The misplaced entry is outside that section, so the newest transition the reader sees is the stale one. Per `templates/adr-kit-guide.md`, only Accepted ADRs are injected into agent context, so a decision the maintainer just signed silently stops reaching any agent. Exit code 0 throughout.

SCOPE: not supersede-only. `set_status_line` and `append_status_history` are both called from the shared `mutate_status` (`bin/adr:351-372`), so accept, reject, propose, supersede and document are all affected. Verified with `accept`.

SECOND FAILURE MODE, from the same root: when the document contains no later fence at all, `find` returns -1, control falls through to the section fallback (`bin/adr:254-267`) and a SECOND `## Status History` section is appended, inverting chronology.

DIRECTION: the search for the insertion point must be bounded to the history block itself rather than to the rest of the document, and the unfenced shape must be handled as a first-class case rather than falling through to the append path. The reader is the more permissive of the two and is the one shipped templates match, so the writer is what should change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An unfenced status_history block receives the new entry inside the ## Status History section, with the same result as the fenced form
- [x] #2 No lifecycle command can write a status_history entry outside the ## Status History section, whatever fenced blocks the document contains later
- [x] #3 A document with no later fence gains no second ## Status History section
- [x] #4 ADR-INDEX.json agrees with the frontmatter status after every lifecycle command, on both fenced and unfenced records
- [x] #5 Regression tests cover the fenced form, the unfenced-with-later-fence form and the unfenced-with-no-fence form, and fail against the current writer
- [x] #6 python -m pytest -q passes
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-09-07 20:01
---
CLOSING THE RECORD, 2026-09-07. Fixed in 6b31ed1 and shipped in v0.56.0; the record was never updated. Issue #119 was closed 2026-08-27T05:12Z.

RE-VERIFIED HERE rather than taken from the issue being closed:

```
git merge-base --is-ancestor 6b31ed1 origin/main       yes (shipped, not just on dev)
pytest tests/test_adr_lifecycle.py -q                  36 passed in 17.49s
```

The fix is visible in the writer itself: `bin/adr` now bounds the search to the block with `body.find("```", start.end(), section_end)` instead of scanning the whole remaining document. That single bound is what kept the entry out of the `## Enforcement` JSON.

AC#5 is the criterion worth naming, because it is the one that makes this stay fixed. `test_history_entry_lands_inside_the_section_whatever_fences_follow` is parameterised over all three shapes the record described -- unfenced with a later fence, fenced with a later fence, unfenced with no fence at all -- and asserts both that the section holds two entries and that nothing after it contains `changed_via`. The third shape covers the second failure mode, the appended duplicate `## Status History` that inverted chronology.

AC#6: the full suite was not re-run here (~11 minutes). It ran green in CI on the pull request that carried the fix and on every run since. The targeted file above is the one that would fail if the writer regressed.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Bounded the status-history writer to the section the reader parses, closing GitHub issue #119.

**The defect.** `append_status_history` located its insertion point with `body.find("```")` over the whole remaining document. On a record whose `status_history` block carries no fence, which is the shape the shipped agent template emits, the entry landed in the next fenced block, in this project the `## Enforcement` JSON. The frontmatter read `Accepted` while `ADR-INDEX.json` went on reporting `Proposed`, with exit code 0 throughout. Since only Accepted ADRs are injected into agent context, a decision the maintainer had just signed silently stopped reaching any agent. A second shape, no later fence at all, appended a duplicate `## Status History` section and inverted chronology.

**The fix.** The search is bounded to the history block (`body.find("```", start.end(), section_end)`), and the unfenced shape is handled as a first-class case rather than falling through to the append path. The reader was already the more permissive of the two and matches the shipped templates, so the writer is what changed. All five lifecycle commands benefit, since `accept`, `reject`, `propose`, `supersede` and `document` share one mutation path.

**Tests.** `test_history_entry_lands_inside_the_section_whatever_fences_follow` is parameterised over the three shapes and asserts the section holds the new entry and that nothing below it does. Re-verified 2026-09-07: 36 passed in `tests/test_adr_lifecycle.py`.

Shipped in v0.56.0 (commit 6b31ed1, confirmed an ancestor of `origin/main`). The record stayed In Progress for eleven days after the work landed; closed on evidence during a release-readiness sweep.
<!-- SECTION:FINAL_SUMMARY:END -->
