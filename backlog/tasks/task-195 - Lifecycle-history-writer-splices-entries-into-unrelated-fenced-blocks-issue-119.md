---
id: TASK-195
title: >-
  Lifecycle history writer splices entries into unrelated fenced blocks (issue
  #119)
status: In Progress
assignee: []
created_date: '2026-08-26 21:01'
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
- [ ] #1 An unfenced status_history block receives the new entry inside the ## Status History section, with the same result as the fenced form
- [ ] #2 No lifecycle command can write a status_history entry outside the ## Status History section, whatever fenced blocks the document contains later
- [ ] #3 A document with no later fence gains no second ## Status History section
- [ ] #4 ADR-INDEX.json agrees with the frontmatter status after every lifecycle command, on both fenced and unfenced records
- [ ] #5 Regression tests cover the fenced form, the unfenced-with-later-fence form and the unfenced-with-no-fence form, and fail against the current writer
- [ ] #6 python -m pytest -q passes
<!-- AC:END -->
