---
id: TASK-207
title: >-
  The shipped-action-pins job fails on every release pull request, and misses
  one of the three actions
status: Done
assignee: []
created_date: '2026-09-07 20:42'
updated_date: '2026-09-07 20:45'
labels:
  - release
  - ci
  - install-smoke
dependencies: []
references:
  - .github/workflows/install-smoke.yml
  - packaging/version-sites.json
  - scripts/bump-version.py
  - >-
    docs/adr/ADR-042-drive-the-release-from-the-maintainer-s-machine-and-create-the-tag-from-the-merge.md
priority: high
type: bug
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split from TASK-193 AC#7 when that record closed. Two defects and one unbuilt clause, all in `.github/workflows/install-smoke.yml`.

DEFECT 1, and it fires on the next release. The `shipped-action-pins` job requires every `@vX.Y.Z` pin in `README.md` and `templates/` to name a tag that already exists (`install-smoke.yml:112`, `git rev-parse -q --verify refs/tags/$ref` else `MISSING TAG` and exit 1). On a release pull request that is guaranteed to be false:

* `packaging/version-sites.json` declares `templates/github-workflows/adr-readiness.yml` and the README `adr-judge@v` pin, so `bump-version.py` rewrites both to the version being released.
* `install-smoke.yml:29` lists `templates/github-workflows/**` in its `pull_request` `paths:` filter, so the release pull request triggers the job.
* ADR-042 creates the tag from the MERGE. During the pull request the tag cannot exist.

Never observed because install-smoke landed in 7460f08, after v0.56.0. `gh pr checks 136`, the v0.56.0 release pull request, lists no install-smoke job at all. The 0.57.0 release is the first to reach it. The job is not a required check on `main`, so it does not block the merge; it goes red on the one pull request where a red check is most expensive to interpret, which is how a team learns to ignore a gate.

DEFECT 2. The job covers two of the three shipped composite actions. `templates/github-workflows/adr-index-check.yml:28` pins `@main`, and the discovery grep matches only `@v[0-9]+\.[0-9]+\.[0-9]+`, so that action is never checked. Either the template should carry a version pin declared in the registry, or the criterion should say "every version-pinned shipped action" and the `@main` pins should be justified in one place.

THE UNBUILT CLAUSE, inherited from TASK-193 AC#7. The actions are checked for RESOLVABILITY at the published tag, not EXECUTED there. `uses:` does not accept an expression, so `@${{ github.ref_name }}` is impossible and running an action at the released tag needs a literal pin, which must then be a declared version site and cannot resolve on a `pull_request` run. It would have to be gated on the tag trigger alone. Decide whether that is worth building; concluding it is not, with the reasoning written down, is an acceptable outcome.

A THIRD THING TO CHECK WHILE HERE, unverified: the job's `push: tags:` trigger may be dead for the auto-created tag, because a tag created by a workflow using `GITHUB_TOKEN` does not start new workflow runs. That is the same constraint ADR-042 is built around. If true, the tag-triggered path never runs at all and the job's only live trigger is the pull request.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A pin naming the version this branch is releasing is reported as pending rather than failing, and the release pull request goes green
- [x] #2 A pin naming any other version whose tag does not exist still fails, so the check is not weakened into uselessness
- [x] #3 The behaviour is proven by simulating both cases against the real README and templates, not only by reading the workflow
- [x] #4 adr-index-check is either covered by the pin check or its @main pin is justified in one place the next reader will find
- [x] #5 Whether to execute the composite actions at the released tag is decided and written down, including a reasoned decision not to build it
- [x] #6 Whether the push: tags: trigger ever fires for the auto-created tag is established from run history rather than assumed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PROVEN BY SIMULATION, not by reading the workflow. The loop was extracted verbatim and run against the real repository so `git rev-parse` resolved real tags:

```
A  release PR for 0.57.0, pins at v0.57.0, tag unborn
   adr-readiness@v0.57.0   pending: this release creates it from the merge
   adr-judge@v0.57.0       pending: this release creates it from the merge      rc=0

B  a stray pin that is NOT the release version
   adr-readiness@v0.57.0   pending...
   adr-judge@v9.9.9        MISSING TAG                                          rc=1

C  today, unchanged: the real pins from README.md and templates/
   adr-judge@v0.56.0       ok
   adr-readiness@v0.56.0   ok                                                   rc=0
```

B is the one that matters: the check is not weakened into uselessness. Only the exact version the branch is releasing is excused, and only while its tag does not exist.

The releasing version is read the way `validate.yml:126` already reads it, from the top release heading, so no new dependency enters a job that sets up no Python.

AC#6 SETTLED FROM RUN HISTORY, and it decides AC#5. A tag this project creates starts no workflow runs: `v0.56.0`, created by the `resolve` job, has zero runs against it, while the hand-pushed `v0.55.0` has one. That is the `GITHUB_TOKEN` constraint ADR-042 is built around, now confirmed on this repository's own data.

So the `push: tags:` trigger on this workflow is dead under ADR-042, and that makes AC#5 answerable rather than a matter of taste: a job executing the composite actions at the released tag would need a literal pin, which cannot resolve on a `pull_request` run, leaving the tag trigger as its only path -- and that path never fires. Building it would produce a job that never runs. Decided not to build, reasoning written into the job summary where the next reader meets it.

AC#4 documented rather than changed. `templates/github-workflows/` ships `adr-judge` and `adr-index-check` at `@main` and `adr-readiness` at a version, so the discovery grep sees one of three. A moving ref has nothing to resolve against, so it is genuinely out of scope for a resolve check; whether shipped templates should pin a version at all is a product decision about what users copy, not this job's to make. The summary now says which pins it covers and which it does not, so the gap is visible instead of implied.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The pin check no longer fails on the release it is meant to protect, and the job now states its real scope.

**The defect.** `shipped-action-pins` required every `@vX.Y.Z` pin in the README and templates to name an existing tag. On a release pull request that is guaranteed false: `bump-version.py` rewrites those pins to the version being released, the rewritten template matches the workflow's `paths:` filter, and ADR-042 creates the tag from the merge. The job would have gone red on every release. It was never seen because install-smoke landed after v0.56.0, so the last release pull request had no such job.

**The fix.** A pin naming the version this branch is releasing is reported as pending rather than failing. Any other unborn tag still fails, which is what keeps the check worth having. The releasing version is read from the top CHANGELOG heading, the same idiom `validate.yml` already uses, so no new dependency enters a job that installs no Python.

**Two questions settled with evidence rather than opinion.** A tag this project creates starts no workflow runs: the auto-created `v0.56.0` has zero, the hand-pushed `v0.55.0` has one. That kills the idea of executing the composite actions at the released tag, because a tag-gated job would never fire, and the reasoning now lives in the job summary. The `@main` pins on two of three shipped templates are documented as out of scope rather than silently skipped; changing them decides what users copy, which is not this job's call.

**Verified by simulation** against the real README and templates in three cases: the release pull request passes, a stray pin still fails, and today's pins are unaffected.
<!-- SECTION:FINAL_SUMMARY:END -->
