---
id: TASK-197
title: >-
  Lifecycle commands lose a transition the Status line carries but the reader
  does not extract (issue #120)
status: In Progress
assignee: []
created_date: '2026-08-27 05:53'
labels: []
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/issues/120'
  - bin/adr
  - templates/adr-kit-guide.md
priority: high
type: bug
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub issue #120. Reproduced 2026-08-27, but only after a first fixture gave a false negative - worth recording, because the shape of the Status line is the whole defect.

WHAT HAPPENS. `ensure_status_history` (bin/adr:372) runs before `set_status_line` precisely so an ADR that predates the status_history convention does not lose its earlier transition when the line is overwritten. It returns early in two cases: a history block already exists (:388), or the recovered transition equals the pending one (:391, commented "Same status on the same day: there is no earlier transition to keep").

`read_status_line` extracts only the LEADING word and the FIRST date. On a real record whose Status line reads

    Superseded by ADR-088, 2026-08-07. Originally Accepted, 2026-05-08.

it returns ("Superseded", "2026-08-07"). That equals the pending transition of a `supersede` repair, so the early return fires, nothing is seeded, and `set_status_line` then replaces the whole line - STATUS_RE captures group 2 as `[^\n]*`.

REPRODUCTION, exit 0, reports `superseded:`:

    'Originally Accepted'  0 occurrences
    '2026-05-08'           0 occurrences
    status_history         1 entry: 2026-08-07 / Superseded

The May acceptance and its attribution are gone, and the history now asserts the ADR's first-ever transition was Superseded.

THE FALSE NEGATIVE, AND WHY IT MATTERS. A first fixture using `Accepted, 2026-05-08. Decision Maker: ...` recovered correctly: two entries, with `changed_by: unknown` and an honest note that the actor was never recorded. The recovery mechanism works. The defect fires only when the leading transition happens to equal the pending one, which is exactly the case a maintainer hits when repairing a record that already claims the transition it is being given.

THE DOCUMENTED CONTRACT DOES NOT COVER THIS. `templates/adr-kit-guide.md` promises: "If the Status line does not yield both a status and a date, the command refuses instead of writing a history that silently omits the earlier transition." Here the line yields both - just not both TRANSITIONS. The promise is written for an unparseable line, not for a line carrying more than the reader reads. The comment at :392 is an inference that holds for one transition and fails for two.

DECIDED WITH THE MAINTAINER, 2026-08-27: option C plus B as a backstop. Always preserve the literal Status line text in the seeded entry's reason, so nothing is lost even when the prose is not parsed into structure; and refuse when the line carries a second date the recovered transition does not account for, because that is the case where the tool demonstrably does not know what it is discarding. Rejected: parsing every transition out of prose, because each shape missed is silent loss again.

The reason field is safe to carry arbitrary prose: history_entry runs it through _yaml_scalar, which quotes anything containing ": " - the guard TASK-70 added after three ADRs in this repository broke their own history block that way.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A seeded recovery entry carries the literal Status line text, so an unparsed transition survives in the record even when it is not structured
- [ ] #2 A Status line carrying a second date the recovered transition does not account for makes the command refuse, naming the file and the line rather than rewriting it
- [ ] #3 The refusal message tells the maintainer what to do instead, since the case it fires on is a legitimate repair
- [ ] #4 The case that already worked keeps working: a line whose leading transition differs from the pending one still seeds a recovered entry
- [ ] #5 The reason field survives a Status line containing a colon-space without breaking the status_history block
- [ ] #6 Regression tests cover the equal-transition-with-extra-history case, the ordinary recovery case and the quoting case, and fail against the current code
- [ ] #7 python -m pytest -q passes
<!-- AC:END -->
