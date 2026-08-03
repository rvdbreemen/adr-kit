---
id: TASK-101
title: >-
  Record the signer decision, including the refusal that shipped and was walked
  back
status: To Do
assignee: []
created_date: '2026-08-03 19:33'
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
- [ ] #1 An ADR records the resolution order: `--changed-by`, then `lifecycle.signer`, then a git-derived person, then refusal
- [ ] #2 It records the v0.44.0 refusal as the alternative that was tried, and the breakage that rejected it — evidence, not hindsight
- [ ] #3 It states the two invariants: never silent, never a machine, and why each matters for an immutable history
- [ ] #4 It records that the signer is machine-local only, because a project-scoped signer would put one person's name on every teammate's acceptance
- [ ] #5 It records the install and upgrade behaviour: propose a candidate, write nothing until the user chooses
<!-- AC:END -->
