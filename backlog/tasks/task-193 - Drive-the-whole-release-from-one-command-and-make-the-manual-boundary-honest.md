---
id: TASK-193
title: Drive the whole release from one command and make the manual boundary honest
status: Done
assignee: []
created_date: '2026-08-26 20:16'
updated_date: '2026-09-07 20:42'
labels: []
dependencies:
  - TASK-190
references:
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
  - docs/RELEASING.md
priority: high
type: feature
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The release is a 158-line prose runbook (`docs/RELEASING.md`) executed by hand. In one week that produced four failures with one root cause: every step is described correctly and nothing enforces it.

1. v0.55.0 was burned. The tag was pushed at the `dev` tip instead of the merged `main` commit, so every version site at that commit still read 0.54.0 and gate 1 refused to publish. A version number was lost.
2. Three npm versions sat staged and unapproved for a week (0.53.0, 0.54.0, 0.55.1). Nothing surfaced that they were waiting.
3. Approval order silently mis-set the npm `latest` tag. Approving 0.55.1, then 0.53.0, then 0.54.0 left `dist-tags.latest = 0.54.0`, because npm sets `latest` to the version published last rather than the highest. `npm install` served 0.54.0. Nothing checked.
4. Eleven documentation claims had gone stale, including `SECURITY.md` naming a supported line twenty-two minor versions old and a README that contradicted itself on the MCP tool count (TASK-190). Nothing read the docs.

GOAL: one command drives the release from the maintainer's machine. The only human steps left are npm's 2FA approval, which npm requires by design, and the decision to start.

DECIDED WITH THE MAINTAINER, 2026-08-26: driven from the maintainer's machine rather than a one-button GitHub workflow; CI tests only the installation variants CI can genuinely test; the tag is created automatically once the release commit lands on `main`.

THE CONSTRAINT THAT SHAPES THE DESIGN, and the reason the obvious approach fails: GitHub does not start workflow runs for events caused by `GITHUB_TOKEN`. A tag pushed by a workflow never triggers `release-publish.yml`, and a PR opened by a workflow never receives the four checks `main` requires (`pytest`, `validate`, `ADR Enforcement (declarative)`, `generated ADR indexes are up to date`, with `enforce_admins: true` and `strict: true`). Verified against the live branch protection. Repository Actions permissions are `default: read` and `can_approve_pull_request_reviews: false`, and no workflow references any secret today.

That is why the driver runs on the maintainer's machine with their own `gh` and `npm` credentials, and why the auto-tag workflow must create the tag and call the publish logic in the same run instead of relying on the tag-push trigger.

Full plan: C:\Users\rvdbr\.claude\plans\eager-floating-nygaard.md
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records the automation-boundary change against ADR-012, naming what is automated, what stays human, and why the driver runs on a machine rather than in Actions
- [x] #2 scripts/release.py drives every phase of docs/RELEASING.md, is idempotent, and each phase is a no-op when its work is already done
- [x] #3 The driver fails when npm dist-tags.latest is not the released version after approval
- [x] #4 The driver verifies each client reports the new version rather than trusting the installer exit code
- [x] #5 A workflow creates the tag on the commit that carries the CHANGELOG version and publishes in the same run, so a tag cannot land on a commit whose version sites disagree
- [x] #6 release-publish.yml is the single INITIATING workflow behind all three release entry points, and the auto-tag path reaches the same publish job through needs: resolve rather than through a second initiating workflow, so the Trusted Publisher identity npm validates stays that filename (ADR-042)
- [x] #7 install-smoke.yml exercises the pre-commit framework install path and states, in the workflow header and the job summary, what it does not cover: the three vendor CLI installs certified through release-candidate.yml per ADR-010, and the OpenCode npm tarball that publish-opencode-npm.yml already validates under Bun
- [x] #8 tests/test_docs_claims.py fails on a version literal in SECURITY.md, a current-version assertion in ROADMAP.md, a wrong README count, and any @v pin that is not a declared version site
- [x] #9 The README OpenCode npm pin is a declared site in packaging/version-sites.json
- [x] #10 The npm approval instructions, including the URL and the ordering warning, appear in the workflow job summary and in the driver output
- [x] #11 python -m pytest -q passes in isolation and scripts/build-client-adapters.py --check reports changed=0
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-08-27 17:40
---
**Verified, 2026-08-27.** Shipped across three PRs: ADR-042 plus the auto-tag `resolve` job in v0.56.0, PR #141 (the driver, the installation smoke, the runbook), PR #142 (AC#3, see below).

AC#5 is proven rather than asserted: `v0.56.0` resolves to `0548ed5`, which is `origin/main`, and the workflow created it. First real use of the mechanism.

AC#3 was NOT met by PR #141 and this is worth recording, because the code read as if it were. `npm_latest_done` existed and was called, but it only chose whether to print the approval instructions; `release.py` returned 0 in both branches. The message printed in the failing state was also wrong: "the package is STAGED, not published" sends the maintainer to npm's approval flow, which cannot fix a dist-tag on an already-approved version. Fixed in PR #142 with three states, verified against the live registry rather than a mock: `release.py 0.55.1 --status` (published, not `latest`) now reports "PUBLISHED, but `latest` names another version" where it previously read "awaiting your 2FA".

Also found in PR #142: `npm view <pkg> versions --json` returns a bare string rather than a list for a package with exactly one version, which silently turns a membership test into a substring match. Handled, with a test.

Evidence: `python -m pytest -q` 1861 passed / 12 skipped in 788s, run in isolation. `build-client-adapters.py --check` changed=0. `adr-lint --strict` clean. All 14 PR checks green including the two new install-smoke jobs.
---

created: 2026-08-27 17:40
---
**The two criteria left open, and why.**

**AC#6 — met in substance, not by the mechanism it names.** The criterion assumed a second workflow that creates the tag and calls a reusable publish job. The implementation has no second workflow: `release-publish.yml` gained a `push: branches: [main]` trigger and a `resolve` job that creates the tag and falls through to the same `publish` job. One file, so the Trusted Publisher identity is preserved trivially rather than carefully.

That turned out to be load-bearing, not merely simpler. npm validates a Trusted Publisher against the CALLING workflow's filename, not the reusable one it invokes, so an auto-tag workflow calling a reusable publish job would have presented the wrong identity and the staging step would have been rejected. This was recorded as an answered Open Question on ADR-042.

Recommend closing AC#6 as satisfied by a different mechanism, and amending its wording rather than building the shape it describes.

**AC#7 — two of three clauses met; the third needs a maintainer decision.**

Met: the pre-commit framework install path (`pre-commit try-repo` against a fixture repository, previously untested), and the job names what it does not cover — the three vendor CLIs, in the workflow header and in the job summary.

Not met as written: the composite actions are checked for RESOLVABILITY at the published tag (the tag exists, and `action.yml` is still present at it), not EXECUTED at that tag. The obstacle is a GitHub limitation, not an oversight: `uses:` does not accept an expression, so `@${{ github.ref_name }}` is impossible. The only way to run an action at the released tag is a hardcoded literal pin — which then has to be a declared version site so `bump-version.py` moves it, and which cannot resolve on a `pull_request` run because the tag does not exist yet. It would have to be gated on the tag trigger alone.

Also not covered, deliberately: the OpenCode tarball. `publish-opencode-npm.yml` already validates it under Bun before staging, so a second copy would be another place to keep in step without adding coverage. Documented in the workflow header.

Recommend either amending AC#7 to what was built, or opening a separate task for the tag-gated execution job. Not decided here.
---

created: 2026-08-27 17:57
---
**Follow-up, PR #143.** Re-reading PR #142 against the bug it fixed rather than against its own tests found two more of the same shape.

1. The exit code was still untested. #142's tests asserted `npm_published`, the text of `npm_wrong_latest` and the bare-string quirk, but nothing asserted `main()` returns 1 — a predicate present, correct, called, and wired to nothing, which is exactly the defect being fixed. The `--status` test uses 9.9.9, never published, so the failing branch was unreachable through the CLI. Now asserted for all four states and proven falsifiable: reverting `return 1` to `return 0` fails the test, restoring it passes.

2. An unreachable registry was reported as a reading. `_dist_tags` returned `{}` both for "npm answered with no tags" and "npm did not answer", so a network failure printed "awaiting your 2FA" — a guess presented as a fact, and the one a maintainer would act on. It now returns None for no-answer and has its own state, exit 1.

The four states are decided once in `npm_state` rather than by two predicates called in sequence at each call site, which is what keeps the report and the exit code from disagreeing.

Also caught: `tests/test_python_compatibility.py` globs `scripts/*.py`, so a new module has to satisfy the Python 3.10 grammar guard as well as the ADR-010 budget list. Green.

**Merge-gate note worth keeping.** `dev` requires only `validate`, which runs a filtered test list; the six `python-compatibility` matrix jobs that run the complete suite are not required there. `--auto` can therefore merge before the full suite finishes, which is what happened on #142. #143 was merged only after all six were green. `gh pr merge --disable-auto` is refused once a PR has merged, so the choice has to be made when the PR is opened.
---

author: Claude
created: 2026-09-07 20:04
---
RE-CHECKED 2026-09-07 during a release-readiness sweep. Nothing changed since the 2026-08-27 notes; this records the verification and the one new data point.

AC#5 IS NOW PROVEN TWICE. The auto-tag path created `v0.56.0` = `0548ed5` = `origin/main` (`gh run list --workflow release-publish.yml`, run 33042302516, event `push`, headBranch `main`, success). That was the first real use; it has since been the only path used.

AC#6 remains met in substance by a single workflow rather than the two the criterion describes: `.github/workflows/release-publish.yml:24-28` triggers on push to `main`, the `resolve` job at :44 creates the tag, and `publish` at :96-97 depends on it. The recommendation in the previous comment stands -- amend the wording to what was built, because npm validates a Trusted Publisher against the CALLING workflow's filename, which makes the two-workflow shape actively wrong rather than merely more complex.

AC#7 unchanged: the pre-commit framework install path is exercised, the job names what it does not cover, and the composite actions are checked for resolvability at the published tag rather than executed there. `uses:` does not accept an expression, so executing at the released tag needs a hardcoded literal pin that cannot resolve on a `pull_request` run. Still a maintainer decision: amend AC#7, or split the tag-gated execution job into its own task.

ONE FINDING FROM DRIVING IT, worth recording because the runbook does not mention it. Executed in a scratch clone with the push URL neutered, `python scripts/release.py 0.57.0` bumps 21 files and exits 1 on the CHANGELOG placeholder, which is by design. Running the same command again then exits 1 in preflight on the now-dirty tree (`release_phases.py:61-66`, and `preflight_done` always returns False at :55-56). The driver's own message says "run this command again - everything else is already in place", which is not literally followable: the notes have to be written AND committed first. `docs/RELEASING.md:129-159` does not say so either. A one-line fix to the error text, or a task of its own.

Also cosmetic, not blocking: `--status` reports `syncback done` and `npm awaiting your 2FA` for an unreleased version, because those done-predicates cannot distinguish "not started" from "done" (`release_phases.py:245-246`, `release_npm.py:56-61`).
---

author: Claude
created: 2026-09-07 20:42
---
CLOSED 2026-09-07. Two criteria reworded to what was built, and the clause that was neither built nor buildable as written is carried by its own record.

AC#6 REWORDED, and the record's own explanation corrected. Comment 2 said "the implementation has no second workflow". That is wrong: `publish-opencode-npm.yml` IS a second workflow, reusable, invoked from `release-publish.yml:223-226`. What has no second instance is the INITIATING workflow -- one file carries all three entry points (`push: branches: [main]`, `push: tags:`, `workflow_dispatch`), and `publish` runs from `needs: resolve`. That distinction is the whole point, because npm validates a Trusted Publisher against the calling workflow's filename. The reworded criterion states the mechanism and cites ADR-042 rather than asserting npm's rejection behaviour as observed fact: the positive half is proven by run 32933199425, the counterfactual is not.

AC#7 REWORDED DOWN to the two clauses that are honestly met, with the composite-action clause moved to its own record. It was not merely 'met differently'. Verified here, and it matters before the next release:

```
bump-version.py writes  templates/github-workflows/adr-readiness.yml -> adr-readiness@v0.57.0
                        README.md:674                                -> adr-judge@v0.57.0
install-smoke.yml:29    pull_request paths includes templates/github-workflows/**
install-smoke.yml:112   git rev-parse --verify refs/tags/$ref  -> MISSING TAG -> exit 1
```

So the pin-resolve job fails on every release pull request, because ADR-042 creates the tag from the MERGE. It has never been seen because install-smoke landed in 7460f08, after v0.56.0: `gh pr checks 136` on the v0.56.0 release pull request lists no install-smoke job at all. The 0.57.0 release is the first one that would hit it.

The job also covers only two of the three shipped composite actions -- `templates/github-workflows/adr-index-check.yml:28` pins `@main`, so the discovery grep never sees it.

Nothing else is outstanding. AC#5 is proven twice over: the auto-tag path created v0.56.0 = 0548ed5 = origin/main (run 33042302516, event push, headBranch main, success), and it has been the only path used since.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
One command now drives the release, and the manual boundary states honestly what it leaves to a person.

**What shipped.** `scripts/release.py` runs every phase of `docs/RELEASING.md` in order and is idempotent: each phase asks the repository whether its work is done, so an interrupted release resumes rather than restarts. `release-publish.yml` gained a `push: branches: [main]` trigger and a `resolve` job that derives the tag from the canonical CHANGELOG version and creates it on the merge commit, so a tag can no longer name a commit whose version sites disagree with it. That is the failure that burned v0.55.0. The driver exits non-zero when npm's `dist-tags.latest` is not the released version, and reports an unreachable registry as its own state rather than guessing, which is what left 0.55.1 released while `latest` read 0.54.0 for a week. `tests/test_docs_claims.py` holds four documentation claims nothing read before.

**Two criteria were reworded rather than built.** AC#6 assumed two workflows with a reusable publish job; one workflow with a `resolve` job is not merely simpler but load-bearing, because npm validates a Trusted Publisher against the calling workflow's filename. AC#7 asked for three clauses and two are met; the third is carried forward as its own record.

**What the closing sweep found, and why it matters before the next release.** The `shipped-action-pins` job fails on every release pull request. `bump-version.py` writes `@v0.57.0` into the README and a shipped template, that path matches install-smoke's `paths:` filter, and the job requires the tag to exist, while ADR-042 creates it from the merge. It has never been seen because install-smoke landed after v0.56.0, so `gh pr checks 136` shows no such job on the last release pull request. The 0.57.0 release is the first to hit it.

**One usability defect in the driver, also unreported until now.** After `prepare` exits on the CHANGELOG placeholder, its own message says to run the command again; preflight then refuses the now-dirty tree. The notes must be written *and committed* first, which `docs/RELEASING.md` does not say either.
<!-- SECTION:FINAL_SUMMARY:END -->
