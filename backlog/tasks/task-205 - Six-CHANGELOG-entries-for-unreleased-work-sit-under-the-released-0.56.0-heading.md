---
id: TASK-205
title: >-
  Six CHANGELOG entries for unreleased work sit under the released [0.56.0]
  heading
status: Done
assignee: []
created_date: '2026-09-07 19:56'
updated_date: '2026-09-07 19:57'
labels:
  - release
  - changelog
  - governance
dependencies: []
references:
  - CHANGELOG.md
  - scripts/release_phases.py
  - scripts/bump-version.py
  - docs/RELEASING.md
  - 'https://github.com/rvdbreemen/adr-kit/issues/120'
priority: high
type: bug
ordinal: 49000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while assessing whether dev warrants a release. Six bullets describing work merged AFTER the v0.56.0 tag were appended to the `### Fixed` list of `## [0.56.0] - 2026-08-27` instead of `## [Unreleased]`, and a seventh user-visible change was never recorded at all.

WHY THIS BLOCKS A RELEASE, not merely untidy: `release-publish.yml` publishes the `## [X.Y.Z]` section verbatim as the GitHub Release body, and `scripts/release_phases.py:95-102` extracts it positionally, from the `## [0.57.0]` heading to the next `^## [`. `scripts/bump-version.py:192-207` INSERTS the new heading directly under the `## [Unreleased]` marker, so only what sits under [Unreleased] is captured. Entries parked under [0.56.0] are therefore stranded twice over: the 0.57.0 release notes omit them, and the already-published 0.56.0 notes claim work that release does not contain.

MEASURED, 2026-09-07:
* `## [0.56.0]` section: 89 lines on origin/main (the published release), 155 lines on this branch.
* `git blame -L 75,140` attributes all 66 added lines to four commits dated 2026-09-06/07, every one of them after the tag `v0.56.0` = 0548ed5, created 2026-08-27T05:22Z.
* 27 lines from PR #146 (TASK-198) are already on origin/dev; 39 from PR #147 (TASK-199) are on this branch. Both PR diffs show `### Fixed` as unchanged context at `@@ -72,...`, i.e. both appended to the released list rather than opening a `### Fixed` under [Unreleased].

THE MISSING ENTRY: PR #139 (commit 9c7adff, closes issue #120) merged 2026-08-27T06:02Z, forty minutes after the tag. It gives `bin/adr accept|reject|propose|supersede|document` a new exit 2 where they exited 0, and documents both refusal conditions in `templates/adr-kit-guide.md`, which `scripts/project_setup.py:26-27` installs into user projects. `git show origin/dev:CHANGELOG.md | grep -i '#120'` finds nothing. PR #140 closed the backlog record without adding one either.

A WORDING DEFECT IN THE MOVED TEXT: the TASK-199 bullet claimed the record was classified `ready-for-confirmation` "with `next_command: null`". On origin/dev `next_commands['ready-for-confirmation']` is `/adr-kit:grill <id>` (`bin/adr_readiness.py:339-343`), so that claim is wrong; what the fix changes is the classification and the finding, not a null command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The six bullets merged after the v0.56.0 tag sit under ## [Unreleased], and the ## [0.56.0] section is byte-identical to the one published on origin/main
- [x] #2 A CHANGELOG entry records the PR #139 / issue #120 lifecycle refusal, naming the exit-code change and the guide update users receive
- [x] #3 The next_command: null claim is corrected to what bin/adr_readiness.py actually returns
- [x] #4 git diff origin/main -- CHANGELOG.md shows additions inside ## [Unreleased] only, in a single hunk
- [x] #5 An [Unreleased] intro states the two upgrade hazards that can turn a green pipeline red
- [x] #6 markdownlint, check-release-version.py, tests/test_docs_claims.py and build-client-adapters.py --check all pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
One edit to CHANGELOG.md, applied on the PR #147 branch so the misplacement never reaches dev.

1. Cut the six bullets at lines 75-140 (PR #147's four at 75-112, a stray blank at 113 that was splitting the Markdown list, PR #146's two at 114-140). The `## [0.56.0] > ### Fixed` list then resumes at the genuine `#119` entry, exactly as on origin/main.
2. Open a `### Fixed` under `## [Unreleased]` and paste them back in merge order: the new PR #139 / issue #120 entry, then PR #146's two, then PR #147's four.
3. Correct the `next_command: null` claim inside PR #147's first bullet while pasting.
4. Add a six-line intro under `## [Unreleased]` naming the two upgrade hazards, since the 0.56.0 section sets that precedent and both hazards can redden a consumer's pipeline.
5. Assert rather than eyeball: the script refuses to run unless every anchor line it cuts between is the line it expects.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
VERIFIED WITH COMMANDS, not by reading the diff. The transformation script asserted all nine anchor lines before touching the file, so a shifted line number would have aborted rather than cut the wrong range.

```
0.56.0 section identical to origin/main   True (89 vs 89 lines)
git diff origin/main -- CHANGELOG.md      1 hunk: @@ -4,7 +4,130 @@
Unreleased headings                       ['### Added', '### Changed', '### Fixed']
Unreleased bullets                        12
MD012 double blank lines                  0
trailing whitespace                       0
markdownlint-cli2 CHANGELOG.md            0 issues in 0 files
check-release-version.py --expect v0.56.0 rc=0, all publish surfaces agree
tests/test_docs_claims.py                 7 passed
build-client-adapters.py --check          changed=0, written=0
```

The byte-identity check on the `## [0.56.0]` section is the load-bearing one: it proves the release already published was restored to what it actually shipped, rather than merely looking untouched in a diff.

WHY THE #120 ENTRY IS WORDED AS A REFUSAL, not a bug fix: the change gives five lifecycle commands an exit code they did not have. A reader upgrading needs to know their pipeline can now stop, and what to write to unblock it, so the entry names the `## Status History` block as the remedy rather than only describing the defect.

The `next_command: null` correction was verified against the source rather than against the PR body, which is where the wrong claim came from: `bin/adr_readiness.py:339-343` maps `ready-for-confirmation` to `/adr-kit:grill <id>`, and a live run before the change printed `next_command: '/adr-kit:grill ADR-001'`. Two sources disagreed and the code won.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Moved six CHANGELOG bullets out of the published `## [0.56.0]` section into `## [Unreleased]`, added the entry that was missing entirely, and corrected one false claim in the moved text.

**What was wrong.** `release-publish.yml` publishes the `## [X.Y.Z]` section verbatim as the GitHub Release body, and `bump-version.py` inserts that heading directly under the `## [Unreleased]` marker, so section membership is positional. Six bullets for work merged after the v0.56.0 tag had been appended to the released section's `### Fixed` list instead. They would have been stranded twice: absent from the 0.57.0 notes, and falsely claimed by a 0.56.0 release that does not contain them. The published 0.56.0 section had grown from 89 lines to 155.

**What changed.** The 66 misplaced lines now sit under a new `### Fixed` in `[Unreleased]`, in merge order. A new entry records PR #139 (issue #120): five lifecycle commands now exit 2 where they exited 0, and `templates/adr-kit-guide.md`, which is installed into user projects, documents both refusal conditions. The TASK-199 bullet no longer claims `next_command: null`, because `bin/adr_readiness.py:339-343` maps that classification to `/adr-kit:grill <id>`. An intro paragraph names the two hazards that can turn a consumer's green pipeline red on upgrade.

**Verification.** The `## [0.56.0]` section is byte-identical to origin/main's (89 lines both sides), and `git diff origin/main -- CHANGELOG.md` is a single hunk at line 4, so every addition is inside `[Unreleased]`. markdownlint reports 0 issues; `check-release-version.py --expect v0.56.0`, `tests/test_docs_claims.py` (7 passed) and `build-client-adapters.py --check` (changed=0) all pass.

**Risk and follow-up.** No code changed, so no runtime risk. The underlying cause is unaddressed: nothing stops the next PR from appending to a released section, because no gate compares a released section against its published tag. Worth a follow-up task; the check is cheap, since `release_phases.py` already has the section-extraction regex this would reuse.
<!-- SECTION:FINAL_SUMMARY:END -->
