---
id: "ADR-042"
title: "Drive the Release From the Maintainer's Machine and Create the Tag From the Merge"
status: "Accepted"
date: "2026-08-26"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-010"
  - "ADR-012"
  - "ADR-013"
  - "ADR-039"
topics:
  - "release"
  - "automation boundary"
  - "distribution"
  - "npm"
aliases:
  - "release driver"
  - "auto-tag"
  - "one-command release"
components:
  - "release driver"
  - "tag creation"
symbols:
  - "scripts/release.py"
  - "release-publish.yml"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-042 Drive the Release From the Maintainer's Machine and Create the Tag From the Merge

## Status

Accepted, 2026-08-26.

## Status History

```yaml
status_history:
  - date: 2026-08-26
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-08-26
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-012
    changed_via: adr-kit lifecycle
  - date: 2026-08-26
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-010
    changed_via: adr-kit lifecycle
  - date: 2026-08-26
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-013
    changed_via: adr-kit lifecycle
  - date: 2026-08-26
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-039
    changed_via: adr-kit lifecycle
  - date: 2026-08-26
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-012 chose "the documented-runbook-plus-tag-triggered-gate" and named
`docs/RELEASING.md` the authoritative runbook. That runbook is 158 lines of
prose executed by a human. In the week of 2026-08-20 to 2026-08-26 it produced
four failures with one shared cause: every step is described correctly and
nothing enforces it.

**One version number was destroyed.** Tag `v0.55.0` was pushed at the `dev`
tip: `git rev-parse v0.55.0^{}` resolves to `77278c1`, the tip of `origin/dev`,
not a release commit. Every version site at that commit still read `0.54.0`, so
gate 1 of `release-publish.yml` refused to publish. Run
[32908217579](https://github.com/rvdbreemen/adr-kit/actions/runs/32908217579)
failed after 8 seconds with `Expected release version: 0.55.0` and exit 1. The
gate worked; the tag was already public and could not be moved, so the release
shipped as `0.55.1`.

**Three npm versions sat staged and unapproved for a week.** 0.53.0 (staged
2026-08-25), 0.54.0 (staged 2026-08-20) and 0.55.1 (staged 2026-08-26) all
waited on a manual approval that no artefact surfaced. The instruction exists,
at `docs/RELEASING.md:283`, in a document nobody re-reads at the moment it
becomes relevant.

**Approval order silently mis-set the `latest` dist-tag.** Approving 0.55.1 at
20:09:57, then 0.53.0 at 20:10:30, then 0.54.0 at 20:10:58 left
`dist-tags.latest = 0.54.0`, because npm sets `latest` to the version published
last rather than the highest. `npm install @rvdbreemen/adr-kit-opencode`
served 0.54.0 while 0.55.1 was the release. Nothing checked, and the runbook
does not mention ordering at all.

**Eleven documentation claims had gone stale** (TASK-190). `SECURITY.md:43`
told a security reporter that `v0.33.x` was the latest supported line, twenty-two
minor versions behind, and contradicted the policy sentence directly above it.
`README.md` called the MCP server "five-tool" in five places while saying
"Seven tools, all key-free" at line 439. `templates/github-workflows/adr-readiness.yml`
pinned an action at `@v0.37.0` and was declared in no registry, so it shipped an
eighteen-versions-old pin to every user who copied the template. Nothing read
the documentation.

None of these is a mistake of understanding. Each is a step a careful person
performs correctly ninety per cent of the time, which over a release is not
good enough.

## Decision Drivers

* A tag must be impossible to place on a commit whose version sites disagree
  with it. This is the failure that cost `v0.55.0`.
* The manual boundary must be *stated where the work happens*, not only in a
  runbook. npm's 2FA cannot be automated and should not be hidden.
* Whatever drives the release must be able to trigger the four checks `main`
  requires. Verified against the live branch protection: `pytest`, `validate`,
  `ADR Enforcement (declarative)` and `generated ADR indexes are up to date`,
  with `enforce_admins: true` and `strict: true`.
* GitHub does not start workflow runs for events caused by `GITHUB_TOKEN`. A
  bot-pushed tag never triggers a tag-push workflow, and a bot-opened pull
  request never receives those four checks, so it can never merge. The
  repository's Actions permissions are `default: read` with
  `can_approve_pull_request_reviews: false`, and no workflow references any
  secret today.
* ADR-010 already decided that the three certified CLI clients are certified
  from externally retained Windows evidence, because the vendor CLIs are not
  installable on a GitHub runner. Any claim to "test every installation
  variant" in CI would be false.
* Adding a credential is a cost, not a neutral choice: a GitHub App or personal
  access token becomes a long-lived secret with write access to a public
  repository, and it has to be rotated and owned by someone.

## Considered Options

* **Option A — a driver on the maintainer's machine, plus a workflow that
  creates the tag from the merge.**
* **Option B — a one-button release in GitHub Actions**, triggered by
  `workflow_dispatch` and authenticated with a GitHub App or personal access
  token so its pull requests and tags trigger checks.
* **Option C — do nothing**: keep the prose runbook and rely on the gates to
  catch mistakes after they happen.

## Decision Outcome

Chosen option: **Option A**, because it is the only one that both removes the
failure class and adds no new long-lived credential to a public repository.
The maintainer's own `gh` and `npm` credentials already trigger checks, which
is precisely what `GITHUB_TOKEN` cannot do, so the driver needs no secret to do
work a bot could not do at all.

The tag stops being a thing a human types. `release-publish.yml` gains a push
trigger on `main`: it reads the top CHANGELOG heading and, when no tag for that
version exists, creates it **on that commit** and continues into the publish
path it already runs. A tag can then only ever name the commit that carries the
version, which makes the `v0.55.0` failure structurally impossible rather than
merely caught.

The tag creation lives in `release-publish.yml` rather than in a workflow of
its own for a reason established under Open Questions: npm validates the
Trusted Publisher against the filename of the workflow that *initiates* the
run, not the reusable workflow containing the publish command. A separate
`release-tag.yml` would initiate under its own name and npm would refuse the
OIDC exchange. Keeping `release-publish.yml` as the initiator leaves the trust
relationship untouched and needs no reusable-workflow refactor.

This amends ADR-012's "Automation boundary" section rather than superseding the
whole decision. ADR-012's publish surface, version-consistency invariant and
release flow all stand unchanged; what changes is which of its steps a human
performs.

The boundary after this decision:

| Step | Who |
|---|---|
| Deciding to release, and the version number | Human |
| Bump, regenerate, gates, branch, pull request | Driver |
| Merging to `main` | Human approval, then auto-merge on green |
| Creating the tag | Workflow, from the merge commit |
| GitHub Release, npm staging | Workflow |
| **npm 2FA approval** | **Human, and unautomatable** |
| Sync back to `dev`, local install | Driver |

### Confirmation

Verified by the tests and commands named under Verification below, and on the
first real release after this ADR: `git rev-parse v<x>^{}` must equal
`git rev-parse origin/main`, and `npm dist-tag ls` must name the released
version as `latest`.

## Decision Contract

### Must

* The release tag is created by `release-publish.yml` from the commit whose
  CHANGELOG heading names that version, in the same run that publishes.
* `release-publish.yml` remains the workflow that initiates every npm staging
  run, because npm's Trusted Publisher is validated against the initiating
  filename. Any new workflow that reaches the npm staging path breaks it.
* `scripts/release.py` is idempotent: every phase checks whether its work is
  already done, so an interrupted release is resumed by re-running it.
* After npm approval, the driver reads `npm dist-tag ls` and fails when
  `latest` is not the released version.
* The driver verifies each client reports the new version by reading it back,
  rather than trusting an installer exit code.
* Any instruction that remains manual is printed where the work happens: in the
  workflow job summary and in the driver's final output, including the npm
  approval URL and the warning that approval order sets `latest`.
* A CI job that exercises installation variants names the variants it does not
  cover, so a green result is not read as full coverage.

### Must Not

* No release step may depend on `GITHUB_TOKEN` opening a pull request or
  pushing a tag and expecting checks to run. They will not run.
* The driver must not merge to `main` by bypassing branch protection; it opens
  a pull request and lets the required checks gate it.
* No new long-lived credential is added to the repository for the release path.
* npm publication must not be automated past the 2FA approval, and no code may
  present the package as published before that approval lands.

### Exceptions

* The three certified CLI installs stay outside the CI smoke job and remain
  certified through `release-candidate.yml` on externally retained evidence,
  per ADR-010.
* The per-machine prepared-directory publish remains a local step, unchanged
  from ADR-012, because it mutates per-user client installs.

### Verification

* `tests/test_docs_claims.py` — documentation claims and undeclared version
  pins.
* `tests/test_release_driver.py` — driver phase idempotence.
* `tests/test_release_allowlist.py` — the driver's line budget under ADR-010.
* `python scripts/check-release-version.py --expect v<x>` on the `main`
  checkout before the tag exists.

## Consequences

### Positive

* The tag cannot land on the wrong commit. The failure that cost `v0.55.0` is
  removed by construction rather than caught after the fact.
* The `latest` dist-tag defect becomes a failing check instead of a silent
  wrong answer to every `npm install`.
* Documentation claims are held by tests. The guard added for the README count
  found a fifth occurrence a manual sweep had missed, on its first run.
* No new secret. The release path keeps working with credentials that already
  exist and are already owned by a person.

### Negative

* **The release needs a machine with `gh` and `npm` authenticated.** It cannot
  be started from a phone or from the GitHub web interface. Accepted because
  the alternative is a long-lived write-scoped credential on a public
  repository, and because releases are deliberate acts.
* **A driver is code that can rot**, and it duplicates in Python what
  `docs/RELEASING.md` states in prose. *Mitigation*: the runbook stays the
  specification and the driver's phases mirror its steps one-for-one, so a
  divergence is visible in review rather than hidden.
* **Automatic tagging removes a pause** in which a human could still change
  their mind after the merge. *Mitigation*: the decision point moves earlier,
  to approving the release pull request, which is where the four checks already
  gate it.
* **The installation smoke job will be read as more than it is.** *Mitigation*:
  the Must clause requires it to name what it does not cover.

## Pros and Cons of the Options

### Option A — driver on the maintainer's machine plus tag-from-merge

* Good, because the maintainer's credentials trigger the required checks, which
  is the one thing `GITHUB_TOKEN` cannot do.
* Good, because it adds no long-lived secret to a public repository.
* Good, because the tag becomes a derived fact rather than a typed one.
* Bad, because it requires an authenticated machine, so a release cannot be cut
  from anywhere.
* Bad, because the driver is a second expression of the runbook and the two can
  drift.

### Option B — one-button release in GitHub Actions

* Good, because a release could be started from anywhere, including a phone.
* Good, because the whole process would be visible in a single run log.
* Bad, because it does not work without a GitHub App or personal access token:
  a `GITHUB_TOKEN` pull request never receives `pytest`, `validate`,
  `ADR Enforcement (declarative)` or `generated ADR indexes are up to date`, so
  auto-merge waits forever.
* Bad, because it turns "you only do the 2FA" into "you also create, own and
  rotate a write-scoped credential", which is a larger manual surface than the
  one it removes.
* Bad, because a write-scoped token on a public repository is a standing risk
  that the maintainer-machine path does not carry.

### Option C — do nothing

* Good, because the gates already caught the `v0.55.0` mistake before anything
  was published, which is the outcome they exist for.
* Bad, because catching is not preventing: the cost was a burned public version
  number, and the same mistake is available on every release.
* Bad, because it leaves the npm ordering defect, the unapproved-staging
  silence and the documentation rot entirely unaddressed. Three of the four
  failures were not caught by any gate.

## Open Questions

- [x] Does npm's Trusted Publisher relationship survive the publish job being — **Answered 2026-08-26 by User: Robert van den Breemen:** No. npm validates the CALLING workflow's filename, not the reusable workflow that runs the publish command; npm's own documentation says validation 'checks the calling workflow's name instead of the workflow that actually contains the publish command'. This repository already proves it: the trust is registered for release-publish.yml while the npm stage publish call runs inside the called publish-opencode-npm.yml, and staging succeeded on run 32933199425. A separate release-tag.yml would therefore initiate the run under its own name and npm would refuse the OIDC exchange. Resolution: do not add a separate tag workflow. Give release-publish.yml a push trigger on main, have it create the tag when the top CHANGELOG heading names a version with no tag, and continue into the existing publish path in the same run. The initiating workflow stays release-publish.yml, so the Trusted Publisher relationship is untouched and no reusable-workflow refactor is needed.
  invoked through `workflow_call`? npm matches the trust relationship against
  the workflow filename that *initiates* the run, and it is configured for
  `release-publish.yml` (`docs/RELEASING.md:256-266`). If `release-tag.yml`
  calls a reusable publish workflow, npm may see `release-tag.yml` as the
  identity and refuse the OIDC exchange, which would break staging on the
  automatic path. Resolve before accepting: either confirm the reusable-call
  case keeps the caller's identity, or register a second Trusted Publisher for
  `release-tag.yml`, or have `release-tag.yml` create the tag only and accept
  that the publish path still needs a human-pushed tag.

## Related Decisions

* **ADR-012 (Release to the Three Coding-Agent Marketplaces From the Public
  Repository)**: this ADR amends its "Automation boundary" section. ADR-012's
  publish surface, version-consistency invariant and release flow are unchanged.
* **ADR-010 (Certify Three Native CLI Clients Through One Outcome Contract)**:
  the reason the installation smoke job stops short of the three CLI installs.
* **ADR-013 (Declare Version Sites in One Registry and Bump by Writing)**: the
  driver writes versions only through that registry, and the undeclared
  readiness-template pin is the defect that motivates the new guard.
* **ADR-039 (Add a Native OpenCode Plugin Without Expanding the Certified CLI
  Gate)**: the npm package whose approval is the remaining human step.

## References

* `docs/RELEASING.md` — the runbook this decision keeps as the specification.
* `docs/RELEASING.md:283` — the npm approval instruction that no artefact
  surfaced at the moment it mattered.
* `.github/workflows/release-publish.yml:20-21` — the tag-push trigger.
* `templates/github-workflows/adr-readiness.yml:16` — the undeclared action pin.
* Failed publish run:
  <https://github.com/rvdbreemen/adr-kit/actions/runs/32908217579>
* TASK-188 (the v0.55.1 release), TASK-190 (the documentation sweep), TASK-193
  (this work).
* npm 2FA requirements for `npm stage approve`:
  <https://docs.npmjs.com/cli/v11/commands/npm-stage>

## Enforcement

```json
{
  "llm_judge": false,
  "llm_judge_reason": "the machine-checkable surface is asserted by named tests rather than by a diff shape: tests/test_docs_claims.py, tests/test_release_driver.py, tests/test_release_workflow_identity.py and tests/test_release_allowlist.py hold the contract, and the npm Trusted Publisher invariant cannot be expressed as a per-file pattern because it is a property of which workflow initiates a run",
  "require_pattern": [
    {
      "pattern": "on:\\s*\\n(?:.*\\n)*?\\s+push:",
      "path_glob": ".github/workflows/release-publish.yml",
      "message": "release-publish.yml must keep its push trigger: ADR-042 has it create the release tag from the merged main commit and publish in the same run, and it must stay the initiating workflow because npm validates the Trusted Publisher against that filename."
    }
  ]
}
```
