---
id: TASK-159
title: 'Guardian sweep: robust diff base and refuse tier flags on a per-ADR stamp'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 15:24'
updated_date: '2026-08-09 15:33'
labels:
  - bug
  - guardian
dependencies: []
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two sweep hazards from the review. (a) Step 3b's judge command pipes git diff HEAD~10 HEAD; in a repo or shallow clone with fewer than 11 commits git fails to stderr, the judge reads an EMPTY diff, exits 0, and the skill stamps every due ADR ok without judging - the same false-ok class as the degradation finding TASK-157 fixed. Step 2a has the same construct with HEAD~5. (b) stamp llm --adr X --verdict ok silently accepts and drops --suggest/--audit/--coverage: the per-ADR branch returns before the tier writes and the trend append, so data the caller believes recorded vanishes with exit 0. Review finding NF3+NF4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The sweep derives its diff base robustly (falls back to the root commit when HEAD~N does not exist) and treats a failed or empty diff as no-verdict: abort, stamp nothing, say why
- [x] #2 stamp llm --adr with any tier-level flag (--suggest, --audit, --coverage, --lint, --violations, --retire, --retire-seen) is refused with exit 2 naming the conflict
- [x] #3 Tests cover both
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Sweep skill (2a, 3a, 3b) now derives BASE once via git rev-parse --verify HEAD~N falling back to the root commit, with the failure mode named in place: HEAD~N in a young or shallow repo piped an EMPTY diff into a judge that then exits 0, stamping ok on nothing - the same false-completeness class as the degradation guard. cmd_stamp refuses tier-level flags (--suggest/--audit/--coverage/--lint/--violations/--retire/--retire-seen) on a per-ADR stamp with exit 2 naming the conflict, instead of accepting and silently dropping them; test proves no state is written.
<!-- SECTION:FINAL_SUMMARY:END -->
