---
id: TASK-200
title: >-
  The guardian queue's age signal is always 0 because readiness never emits a
  date
status: Done
assignee: []
created_date: '2026-09-06 15:11'
updated_date: '2026-10-03 16:07'
labels:
  - bug
  - readiness
  - guardian
dependencies: []
priority: medium
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bin/adr_guardian_queue.py:34-36 reads item.get('date'), but readiness_for_record (bin/adr_readiness.py:345-373) emits 'evaluated_on' and no 'date' key. _parse_date therefore gets None and _age_days returns 0 for every record. Confirmed twice: a live report run in this session and the committed docs/adr/.adr-kit-readiness.json both show 'age 0 days' on every entry.

Two consequences. The 'age N days' reason string printed at bin/adr_guardian_queue.py:87 is always 'age 0 days', which is noise occupying one of the two reason slots the SessionStart block shows (hooks/adr_hook_core.py:279). And the age element of the _rank tuple (bin/adr_guardian_queue.py:102) is inert, so an ADR that has been Proposed for six months ranks identically to one filed this morning: the queue cannot prioritise staleness even though its ranking claims to.

tests/test_adr_guardian_queue.py builds its items by hand with an explicit 'date' key (_item at line 34), which is why the unit tests pass while production never sees one. Found while implementing TASK-199; deliberately not fixed there, because deciding what the date should mean (filed, last edited, last status change) is a design question rather than a typo.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 readiness emits a date field per record, and the queue's age reason reflects it
- [x] #2 A test exercises the age signal through build_readiness_report rather than a hand-built item dict, so the two halves cannot drift apart again
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced 2026-10-03: `adr-readiness --all-proposed --format json --today 2026-10-03` has no date key, and `rank_proposed` gives ADR-035 'age 0 days'. The recorded cause is correct but incomplete. The date already exists: bin/adr_catalog.py:337 resolves it (latest status-history date, else the frontmatter date) and :401 stores it, but readiness_for_record never copied it into its output. So the 'design question' was already answered by the catalog.

Fix: readiness emits `date` (bin/adr_readiness.py); the schema allows string or null; adapters regenerated. MCP golden frame 8 regenerated deliberately: the payload is identical apart from `date`, checked by comparing with `date` removed. New end-to-end test in tests/test_adr_guardian_queue.py: two records with the same signals, the older ranks first with 'age 19 days'. Related suites: 147 passed.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-09-07 20:03
---
RECORD CORRECTION, 2026-09-07, from a release-readiness sweep. The defect reproduces exactly as written; one supporting detail in the evidence does not.

The record says "the committed `docs/adr/.adr-kit-readiness.json`". That file is not committed and never was:

```
git ls-files --error-unmatch docs/adr/.adr-kit-readiness.json   not tracked
git check-ignore -v docs/adr/.adr-kit-readiness.json            .gitignore:64
```

It is a local artefact, last written 2026-08-02 on this machine. That does not weaken the finding -- a live report run in this session showed the same `age 0 days` -- but it does change who can reproduce it: a reader cannot open the file in the repository, they have to run the report. Worth stating, because "committed" invites the next person to look for evidence that is not there.

The cause itself is unchanged and still reproduces: `bin/adr_guardian_queue.py:34-36` reads `item.get('date')` while `readiness_for_record` (`bin/adr_readiness.py:345-373`) emits `evaluated_on` and no `date` key, so `_parse_date` gets None and `_age_days` returns 0 for every record.

Still open, still not a release blocker: the failure is one wasted reason slot in the SessionStart block and an inert ranking term, and it ships in v0.56.0 already. The design question named in the record -- what `date` should mean, filed or last edit or last status change -- is the real gate on this work and is unanswered.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged in PR #161. adr-readiness now passes through the date the catalog already resolves (the latest status change, else the frontmatter date), so the guardian queue ranks by real age. An end-to-end test drives build_readiness_report into rank_proposed. The MCP golden frame was regenerated on purpose; it differs only by `date`.
<!-- SECTION:FINAL_SUMMARY:END -->
