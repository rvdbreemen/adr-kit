---
id: TASK-208
title: The release driver refuses any release whose notes mention the word TODO
status: Done
assignee: []
created_date: '2026-09-08 04:19'
updated_date: '2026-09-08 04:22'
labels:
  - release
  - driver
dependencies: []
references:
  - scripts/release_phases.py
  - scripts/bump-version.py
  - tests/test_release_driver.py
priority: high
type: bug
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by driving the 0.57.0 release. `scripts/release_phases.py:105-107`:

```python
def _changelog_is_placeholder(ctx) -> bool:
    body = _changelog_section(ctx)
    return (not body.strip()) or "TODO" in body
```

The intent is right: `bump-version.py:201` inserts the literal line `- TODO: describe this release.` and the driver must refuse to publish an unedited placeholder as the GitHub Release body. The test is wrong: it matches the substring anywhere in the section, so any release note that discusses a TODO marker blocks its own release.

That is not hypothetical for 0.57.0. This release ships the placeholder-detection work of TASK-198 and TASK-199, so its notes necessarily quote the markers:

```
appends `- TODO: ...` into any required heading it has to add, which is honest
`- TODO: add verifiable references.`, the acceptance gate set still passes it
the `- TODO:` list item `bin/adr-migrate` writes but not the
`<!-- TODO: ... -->` comment the `/adr-kit:migrate` skill writes, while
and a TODO with the same words.
```

Five occurrences, none a placeholder. `prepare` therefore stops with "CHANGELOG.md's [0.57.0] section is still the placeholder" over notes that are finished, and the only way forward is to degrade the notes until they no longer name the thing the release is about.

The failure is self-inflicted in a precise way: a gate that cannot describe its own subject matter. It has never fired before because no earlier release wrote about TODO markers.

DIRECTION: match the placeholder's SHAPE rather than a word. The placeholder is a top-level list item beginning `- TODO:`; every legitimate mention above is either inside backticks or mid-sentence, so a line whose stripped form starts with `- TODO:` separates them exactly. That also still catches a leftover TODO item an author added themselves, which a check for the exact placeholder string would miss.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The 0.57.0 notes, which quote TODO markers five times, are not reported as a placeholder
- [x] #2 An unedited section carrying the line bump-version.py writes is still reported as a placeholder
- [x] #3 A leftover TODO list item an author wrote themselves is still caught
- [x] #4 An empty section is still reported as a placeholder
- [x] #5 Regression tests cover all four cases and fail against the substring test
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
FOUND BY USING THE TOOL, which is the only way this could have been found: no earlier release wrote about TODO markers, so the substring test had never been wrong before.

The fix matches the placeholder's shape, a line whose stripped form starts with `- TODO:`. That separates the scaffold from every legitimate mention in the 0.57.0 notes, because each of those five is either inside backticks or mid-sentence.

Why not compare against `bump-version.py`'s exact string: it would pass an author who starts from the scaffold and edits it halfway, which is the likeliest way an unfinished note reaches a Release body that cannot be quietly fixed afterwards.

PROVEN FALSIFIABLE rather than merely passing. Reverting the predicate to `"TODO" in body` and re-running fails `test_prepare_lets_a_release_describe_todo_markers`; restoring it passes. 20 tests in `tests/test_release_driver.py` green.

```
before  release.py 0.57.0 --only prepare   rc=1  "still the placeholder"
after   release.py 0.57.0 --only prepare   rc=0  prints the npm approval steps
```

`scripts/release_phases.py` is 331 lines, inside its 400-line ADR-010 budget.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The release driver no longer refuses a release for describing what it ships.

**The defect.** `_changelog_is_placeholder` tested `"TODO" in body`. The intent was right, since `bump-version.py` inserts a `- TODO: describe this release.` item and publishing that verbatim as a GitHub Release body cannot be quietly undone. The test was too broad: any release note discussing a TODO marker blocked its own release.

**Why it surfaced now.** 0.57.0 ships the placeholder-detection work of TASK-198 and TASK-199, so its notes quote `- TODO:` markers five times, none of them a placeholder. `prepare` stopped on finished notes, and the only way forward would have been to degrade them until they no longer named the release's own subject.

**The fix.** Match the shape, a top-level `- TODO:` list item, not the word. Every legitimate mention in these notes is inside backticks or mid-sentence, so the two separate exactly. This still catches a leftover TODO item an author wrote themselves, which comparing against the exact scaffold string would have missed.

**Verified falsifiable.** Reverting the predicate fails the new test; restoring it passes. Four cases pinned: the 0.57.0-shaped notes pass, the unedited scaffold is refused, a half-finished TODO item is refused, an empty section is refused.
<!-- SECTION:FINAL_SUMMARY:END -->
