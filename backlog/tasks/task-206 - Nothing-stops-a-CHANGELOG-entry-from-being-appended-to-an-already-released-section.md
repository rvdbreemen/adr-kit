---
id: TASK-206
title: >-
  Nothing stops a CHANGELOG entry from being appended to an already released
  section
status: Done
assignee: []
created_date: '2026-09-07 20:30'
updated_date: '2026-09-08 04:37'
labels:
  - release
  - changelog
  - governance
  - ci
dependencies: []
references:
  - CHANGELOG.md
  - scripts/release_phases.py
  - scripts/bump-version.py
  - .github/workflows/validate.yml
  - tests/test_release_allowlist.py
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
priority: medium
type: feature
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-205 repaired six bullets that had been appended to `## [0.56.0]` after that release was tagged. Nothing prevents the next one. The defect reached `dev` twice, through PR #146 and PR #147, and was found only by a human sweep.

WHY IT IS INVISIBLE IN REVIEW. Both PR diffs show `### Fixed` as unchanged context in the hunk header, so the fragment reads exactly like a correct addition. Only someone who maps the line numbers back to the nearest `## [` heading sees that it is the wrong `### Fixed`. That is not a thing a reviewer does.

WHY IT MATTERS. Section membership is positional. `scripts/bump-version.py:192-207` inserts the new release heading directly under the `## [Unreleased]` marker, `scripts/release_phases.py:95-102` extracts a section from its heading to the next `^## [`, and `release-publish.yml` publishes that section verbatim as the GitHub Release body. An entry under a released heading is therefore lost twice: absent from the next release's notes, and claimed by a release that does not contain it.

MEASURED ON dev AT 150ac81, and this is what shapes the rule:

* 75 release headings, 79 tags. 59 sections can be compared against their tag; 16 cannot, because early releases predate the tagging convention or the tag has no CHANGELOG.md.
* Six sections already differ from their tag today. All six are benign: a factual correction in 0.52.0, a count corrected from "Nine" to "Ten" in 0.46.0, two whitespace reflows in 0.44.1 and 0.43.0, and single-line rewordings in 0.30.2 and 0.21.0. None adds a bullet.
* So a byte-identity rule is not adoptable: it fails on six sections that are correct. Editing a released section is legitimate; APPENDING to one is not.

RULE THAT SURVIVES BOTH MEASUREMENTS, prototyped and falsified before this record was written: for every release section whose tag exists, the count of top-level list items must not exceed the count at that tag. Verified in the scratchpad, comparing 59 sections:

```
current dev (after the TASK-205 repair)   PASS
commit 4a6a7cb (before it)                FAIL  [0.56.0] 13 -> 19 bullets (+6)
```

A first attempt compared bullet text rather than count and produced four false positives, because a reworded first line reads as a new bullet. Counting is what distinguishes correction from addition.

THE PLACEMENT IS THE OPEN QUESTION, not the rule. `.github/workflows/validate.yml:13` uses `actions/checkout@v4` with no `fetch-depth` and no `fetch-tags`, so the gate's `git show vX.Y.Z:CHANGELOG.md` has nothing to read in that job. Whatever ships has to state how it gets the tags, or avoid needing them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The check fails on commit 4a6a7cb, naming ## [0.56.0] and the six bullets it gained, and passes on dev at 150ac81
- [x] #2 Sections whose tag is absent are skipped and counted in the output, never silently ignored
- [x] #3 The six sections that legitimately differ from their tag today do not fail the check
- [x] #4 The failure message names the heading, the bullets gained, and why it matters: the section is published verbatim as the release body
- [x] #5 The check runs somewhere a pull request reaches it, and the record states how it obtains the tags or why it needs none
- [x] #6 If it ships as a script under scripts/, it is added to the ADR-010 allowlist in tests/test_release_allowlist.py and stays within its line budget
- [x] #7 A regression test pins both directions, so reverting the check fails the suite
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Pure rule, git at the edge, wired into the one check that actually blocks.

1. `scripts/check-changelog-sections.py`. `check(current, published_for)` takes a resolver rather than calling git itself, so the rule is testable without a history. The verdict is a bullet COUNT comparison; the bullet TEXT is used only to name the culprits in the message.
2. `tests/test_changelog_sections.py`. Eight unit tests over in-memory fixtures, plus one that runs the live document through the git path and skips where the checkout has no tags.
3. `.github/workflows/validate.yml`. `fetch-depth: 0` on the checkout, and a step running the script. `validate` is the ONLY required status check on `dev`, and it is a single job, so a step inside it is the only placement that blocks the branch where this defect twice landed.
4. `tests/test_release_allowlist.py`. Added to the ADR-010 entrypoint budget list, deliberately not to `packaging/public-artifacts.json`: it is a CI gate, not a shipped artifact.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
THE RULE WAS FALSIFIED BEFORE IT WAS WRITTEN, in both directions, against real commits rather than fixtures:

```
python scripts/check-changelog-sections.py                      rc=0  (dev @ 150ac81)
  Compared 59 released sections against their tag; skipped 16 with no usable tag.

python scripts/check-changelog-sections.py --changelog <4a6a7cb>  rc=1
  FAIL  ## [0.56.0] gained 6 bullet(s) since its tag (13 -> 19)
```

A FIRST ATTEMPT WAS WRONG AND THE MEASUREMENT CAUGHT IT. Comparing bullet TEXT rather than count reported four false positives on the current, correct document: 0.52.0, 0.46.0, 0.30.2 and 0.21.0 each had a bullet whose first line was reworded after the tag, which reads as a new bullet. Had that shipped, the gate would have failed every pull request from day one and been disabled within a week. Counting is what distinguishes correcting a released note from appending to one.

THE TEST FOUND A REAL DEFECT IN THE SCRIPT. `report(..., stream=sys.stdout)` binds the default at import, so it kept writing to the stream captured then and `capsys` read nothing. Now resolved at call time. Worth recording because the function looked correct and the output appeared on screen; only an assertion on the captured text disagreed.

WHY THE UNIT TESTS INJECT A RESOLVER INSTEAD OF USING GIT. The complete suite runs on `actions/checkout@v4` with no `fetch-depth`, so a test that shelled out for tags would pass here and skip or fail on the runner. That is the exact shape of environment-dependent breakage that has cost this project several release pull requests. The rule is tested deterministically; the git plumbing runs in the workflow step, which checks out with `fetch-depth: 0` and exits 2 rather than 0 if the tags are missing -- a gate that cannot compare must not report success.

PLACEMENT, and why not the obvious alternatives. `install-smoke.yml` already fetches tags and already checks shipped `@vX.Y.Z` pins against them, which is the same family of check, but its `pull_request` trigger carries a `paths:` filter that a CHANGELOG-only change does not match -- it would never fire on the pull requests that matter. A new job in `validate.yml` would not help either: branch protection names contexts per job, and `validate` is the only required check on `dev`. So the step lives inside that job, and the job's checkout gained `fetch-depth: 0`, which five other workflows in this repository already use.

SIXTEEN SECTIONS CANNOT BE CHECKED and are reported as skipped every run. They predate the tagging convention or their tag carries no CHANGELOG.md. That is stated rather than quietly excluded, because a check that says it looked when it did not is the failure this file exists to prevent.

KNOWN HOLE, deliberate: deleting one bullet and adding another in the same section nets zero and passes. Catching it needs text comparison, which is what produced the four false positives. The defect being guarded is purely additive.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-09-08 04:37
---
COVERAGE WIDENED, 2026-09-08, before the 0.57.0 release. The first version resolved only the `v{X}` tag spelling and reported 16 sections as unskippable. That number was itself an overstatement of what cannot be checked, which is the failure mode this whole file exists to prevent.

```
git tag | 65 spelled v0.56.0
         | 14 spelled adr-kit--v0.1.0
```

Resolving both:

```
before   compared 59, skipped 16
after    compared 70, skipped  6
```

Eleven more sections are now genuinely guarded. Still falsifiable in both directions against real commits: rc=0 on the current document, rc=1 on 4a6a7cb naming `## [0.56.0]` and its six added bullets. Nine tests green, 198 lines, inside the 300-line entrypoint budget.

Credit where due: the two-spelling problem came out of a parallel investigation rather than from my own reading, and I confirmed it against `git tag` before acting on it.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A released CHANGELOG section may now be corrected but not appended to, enforced on every pull request.

**The defect.** `release-publish.yml` publishes a `## [X.Y.Z]` section verbatim as its GitHub Release body, and section membership is positional: `bump-version.py` inserts the next release heading directly under the `## [Unreleased]` marker. A bullet written under a released heading is therefore lost twice, absent from the next release's notes and falsely claimed by a release that does not contain it. It reached `dev` through two separate pull requests and was found only by a human sweep, because both diffs carry `### Fixed` as unchanged context and read like correct additions.

**The rule, and why it counts rather than compares.** For every release section whose tag exists, the number of top-level bullets must not exceed the number at that tag. Editing a released section is legitimate and this project does it: of the 59 sections that can be compared, six differ from their tag today, and every one is a correction. A byte-identity rule fails all six; comparing bullet text fails four, because a reworded first line reads as new. The count separates correction from addition.

**Falsified in both directions** against real commits: `rc=0` on `dev` at 150ac81 (59 compared, 16 skipped for lack of a usable tag), `rc=1` on 4a6a7cb naming `## [0.56.0]` and the six bullets it gained.

**Placement.** A step inside the `validate` job, whose checkout gained `fetch-depth: 0`. That job is the only required status check on `dev`, which is the branch the defect twice reached. `install-smoke.yml` was the tempting home since it already resolves shipped tags, but its `paths:` filter means a CHANGELOG-only pull request never triggers it.

**Tests.** Nine, eight of them over in-memory fixtures through an injected resolver so they do not depend on a git history the test matrix does not fetch. One writing the report was what caught a late-binding defect in the script itself.

**Risks and holes, stated.** Sixteen sections cannot be compared and are reported as skipped on every run rather than silently passed. Deleting one bullet while adding another nets zero and passes; catching that needs the text comparison that produced the false positives, and the defect being guarded is purely additive. The `validate` job now clones full history, which costs some seconds on every push.
<!-- SECTION:FINAL_SUMMARY:END -->
