---
id: TASK-193
title: Drive the whole release from one command and make the manual boundary honest
status: In Progress
assignee: []
created_date: '2026-08-26 20:16'
updated_date: '2026-08-27 17:40'
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
- [ ] #6 release-publish.yml stays the Trusted Publisher workflow identity while its publish job is reusable by the auto-tag path
- [ ] #7 A smoke job exercises the pre-commit framework install, the three composite actions at the published tag, and the OpenCode tarball, and names what it does not cover
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
<!-- COMMENTS:END -->
