---
id: TASK-113
title: Lint this repository's own ADRs on every pull request
status: To Do
assignee: []
created_date: '2026-08-03 19:35'
labels:
  - ci
  - lint
dependencies: []
priority: medium
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A structurally broken ADR — missing required section, filename/heading mismatch, duplicate number — can merge to dev or main and survive until the Monday guardian cron or the next release.

**Coverage as measured.** `python bin/adr-lint docs/adr` appears in CI only at `adr-guardian-audit.yml:53` (weekly cron) and, with `--strict`, in the two release workflows. `adr-lint-self.yml` lints `examples/` and a FAIL fixture, never `docs/adr`. Two partial backstops exist: `tests/test_adr_cross_references.py` shells out to the linter on every dev and main PR but discards the exit code and asserts only that `REFERENCE*` findings are empty; `tests/test_adr_lint_clarity.py` does assert `returncode == 0` under the full acceptance gate set — for ADR-006 and ADR-007 only, hardcoded. So 2 of 19 shipped ADRs carry a strict exit-code gate at PR time and 17 do not.

Green today: the default gate set exits 0 over 19 ADRs with 0 advisories, so this lands without a repair round.

Do **not** also drop the `branches: [main]` filter on `adr-index-check.yml`. `validate.yml:151` already runs `bin/adr-index --check docs/adr` on push and PR to both dev and main; that would be duplicate coverage, not a fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `validate.yml` runs `python bin/adr-lint docs/adr` as a named step and fails on non-zero
- [ ] #2 `--strict` stays at release, per the existing split
- [ ] #3 The step is a visible CI step rather than an assertion buried in a test module
- [ ] #4 A deliberately broken ADR on a scratch branch is confirmed to fail the new step
<!-- AC:END -->
