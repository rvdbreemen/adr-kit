---
id: TASK-113
title: Lint this repository's own ADRs on every pull request
status: Done
assignee: []
created_date: '2026-08-03 19:35'
updated_date: '2026-08-03 20:58'
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
- [x] #1 `validate.yml` runs `python bin/adr-lint docs/adr` as a named step and fails on non-zero
- [x] #2 `--strict` stays at release, per the existing split
- [x] #3 The step is a visible CI step rather than an assertion buried in a test module
- [x] #4 A deliberately broken ADR on a scratch branch is confirmed to fail the new step
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`validate.yml` gained a named step, `Lint this repository's own ADRs`, running `python bin/adr-lint docs/adr`. It runs on push and pull request to dev and main, which the job already did.

AC#4 verified by mutation rather than by assertion. Four break types were introduced into a copy of `docs/adr` and each failed with exit 1:

- duplicate ADR number → `consistency FAIL: duplicate ADR-020 ...`
- missing required section → `completeness FAIL: missing sections: ['Consequences']`
- heading/filename mismatch → `consistency FAIL: heading number 099 != filename 022`
- dangling `related` link → `consistency FAIL: related lists ADR-777, which is not in this directory`

Worth noting what the default set does *not* catch, since it bounds what this step promises: removing `## Decision Contract` passes, because it is an optional MADR section rather than a required one. This step guards structure, not completeness of the contract.

Green on the current set (28 ADRs, 0 advisories), so it lands without a repair round. `--strict` stays at release, and the `branches: [main]` filter on `adr-index-check.yml` was deliberately left alone — `validate.yml` already runs `bin/adr-index --check` on both branches.
<!-- SECTION:FINAL_SUMMARY:END -->
