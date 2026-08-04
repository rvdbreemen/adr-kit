---
id: TASK-101
title: >-
  Record the signer decision, including the refusal that shipped and was walked
  back
status: Done
assignee: []
created_date: '2026-08-03 19:33'
updated_date: '2026-08-03 20:57'
labels:
  - adr
  - lifecycle
  - retrospective
dependencies: []
priority: medium
ordinal: 2300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
v0.44.0 shipped a lifecycle that refused to run at all unless `lifecycle.signer` was configured by hand. A fresh clone, a container and a CI runner each failed on the very first command, `bin/adr new` included. That refusal was reasoned from R8.1's "no default that names the tool" — and it was stricter than R8.1 asks: `git config user.name` is a value a human configured on this machine, the opposite of the toolkit signing for itself.

The walk-back is now in the code and in the spec (R8.2), with two properties held: a derived actor is announced on stderr, because a name landing in an immutable history should never arrive unseen; and a machine identity — `*[bot]`, `github-actions`, `runner`, `jenkins`, `root`, `user`, `unknown`, `adr-kit` — falls through to the refusal, because R8 asks which *human* accepted.

No ADR records any of it. This is exactly the shape ADRs exist for: a decision, its consequence in production, and the correction. Written down, the next person can see why the line sits where it does. Undocumented, someone re-tightens it and breaks a fresh clone again.

Spec: R8, R8.1, R8.2. Tests: `tests/test_adr_signer_discovery.py`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records the resolution order: `--changed-by`, then `lifecycle.signer`, then a git-derived person, then refusal
- [x] #2 It records the v0.44.0 refusal as the alternative that was tried, and the breakage that rejected it — evidence, not hindsight
- [x] #3 It states the two invariants: never silent, never a machine, and why each matters for an immutable history
- [x] #4 It records that the signer is machine-local only, because a project-scoped signer would put one person's name on every teammate's acceptance
- [x] #5 It records the install and upgrade behaviour: propose a candidate, write nothing until the user chooses
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ADR-027 written and Proposed, passing all gates.

The record carries the v0.44.0 refusal as an alternative that was **tried in production**, not one that was imagined — which is the part that makes it useful. It optimised for never writing a wrong name and achieved that by never writing anything, including from `bin/adr new`, a command that creates a Proposed record and attributes no decision at all.

Two properties are stated as the decision rather than as implementation detail: never silently (a derived actor is announced with its source and the command that would change it) and never a machine (10 identities fall through to the refusal).

One limit the task did not ask for and the ADR states anyway: the machine-identity list is a **denylist**, so a bespoke service account is adopted as a person. The announcement is the mitigation — the name is shown at the moment it is used, so an incorrect derivation is visible and correctable rather than silent.

Acceptance is the maintainer's action.
<!-- SECTION:FINAL_SUMMARY:END -->
