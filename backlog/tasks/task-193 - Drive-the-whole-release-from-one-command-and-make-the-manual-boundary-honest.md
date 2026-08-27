---
id: TASK-193
title: Drive the whole release from one command and make the manual boundary honest
status: In Progress
assignee: []
created_date: '2026-08-26 20:16'
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
- [ ] #1 An ADR records the automation-boundary change against ADR-012, naming what is automated, what stays human, and why the driver runs on a machine rather than in Actions
- [ ] #2 scripts/release.py drives every phase of docs/RELEASING.md, is idempotent, and each phase is a no-op when its work is already done
- [ ] #3 The driver fails when npm dist-tags.latest is not the released version after approval
- [ ] #4 The driver verifies each client reports the new version rather than trusting the installer exit code
- [ ] #5 A workflow creates the tag on the commit that carries the CHANGELOG version and publishes in the same run, so a tag cannot land on a commit whose version sites disagree
- [ ] #6 release-publish.yml stays the Trusted Publisher workflow identity while its publish job is reusable by the auto-tag path
- [ ] #7 A smoke job exercises the pre-commit framework install, the three composite actions at the published tag, and the OpenCode tarball, and names what it does not cover
- [ ] #8 tests/test_docs_claims.py fails on a version literal in SECURITY.md, a current-version assertion in ROADMAP.md, a wrong README count, and any @v pin that is not a declared version site
- [ ] #9 The README OpenCode npm pin is a declared site in packaging/version-sites.json
- [ ] #10 The npm approval instructions, including the URL and the ordering warning, appear in the workflow job summary and in the driver output
- [ ] #11 python -m pytest -q passes in isolation and scripts/build-client-adapters.py --check reports changed=0
<!-- AC:END -->
