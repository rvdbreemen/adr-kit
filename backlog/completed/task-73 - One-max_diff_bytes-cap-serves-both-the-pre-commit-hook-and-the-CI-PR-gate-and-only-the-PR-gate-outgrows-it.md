---
id: TASK-73
title: >-
  One max_diff_bytes cap serves both the pre-commit hook and the CI PR gate, and
  only the PR gate outgrows it
status: Done
assignee: []
created_date: '2026-07-31 06:10'
updated_date: '2026-07-31 20:53'
labels:
  - judge
  - ci
  - release
dependencies: []
references:
  - docs/adr/.adr-kit.json
  - .github/actions/adr-judge/action.yml
  - schemas/adr-kit-config.schema.json
  - >-
    docs/adr/ADR-015-enforce-a-two-second-deterministic-latency-budget-as-a-test-fixture-contract.md
modified_files:
  - bin/adr-judge
  - codex/bin/adr-judge
  - copilot/bin/adr-judge
  - schemas/adr-kit-config.schema.json
  - codex/schemas/adr-kit-config.schema.json
  - copilot/schemas/adr-kit-config.schema.json
  - .github/actions/adr-judge/action.yml
  - docs/adr/.adr-kit.json
  - docs/RELEASING.md
  - README.md
  - CHANGELOG.md
  - tests/test_adr_runtime_config.py
priority: medium
ordinal: 78500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`judge.max_diff_bytes` is a single number applied to two workloads with different shapes, and the release PR is the one that keeps outgrowing it.

**Hit on the v0.43.0 release PR (#53).** The `ADR Enforcement (declarative)` gate failed with:

```
diff is 2281314 bytes and exceeds judge.max_diff_bytes=2097152;
enforcement was not performed.
```

Not a violation — the cap. Measured with the cap lifted: the same diff scans in **4.5 s and reports 0 violations, 0 advisory**. The gate would have passed.

**Why this recurs rather than being a one-off.** The pre-commit hook judges one commit. The CI gate judges `origin/main...HEAD`, which for a release PR is the whole development branch. This repository additionally ships three mirrored client distributions, so most changes are counted roughly three times: of the 2,281,314-byte PR diff, 383,640 bytes (17%) is `codex/` and `copilot/` alone. Any release of meaningful size will exceed a cap tuned for a single commit.

The cap has already been raised once — the schema default is 1 MiB and this repository's config carried 2 MiB. Raising it again to 8 MiB unblocked v0.43.0, but that is treating the symptom.

**Why the cap is right to exist.** It fails closed rather than passing silently, which is the correct choice: a diff that was never scanned must not report success. That property should be kept. The problem is only that one threshold serves a fast local hook (which never sees a diff this size, and is bound by ADR-015's latency budget) and a CI gate (which routinely does, and is not user-facing latency).

**Directions worth weighing, not a prescription:**

- Separate thresholds per invocation, e.g. an explicit `--max-diff-bytes` the CI action passes, leaving `judge.max_diff_bytes` as the commit-path number.
- Judge the PR diff excluding generated mirrors, since `codex/` and `copilot/` are byte-identical copies of `bin/` and a violation there is already caught in the source copy plus by the adapter drift check. This shrinks the input by ~17% and removes triple-counting, but needs care: the enforcement globs deliberately cover all three distributions.
- Leave one number and document a release-sized default, accepting that it will need occasional review.

Whichever is chosen, the fail-closed behaviour and the actionable error message should survive it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A release-sized PR diff no longer fails the CI enforcement gate on size alone, without disabling the cap
- [x] #2 The pre-commit path keeps a threshold appropriate to a single commit; raising the CI limit does not silently raise the local one
- [x] #3 A diff that genuinely was not scanned still fails closed with an actionable message; no code path reports success for an unscanned diff
- [x] #4 The chosen approach is written down where a maintainer will find it during a release, since this has now bitten once at v0.43.0
- [x] #5 If generated mirrors are excluded from the judged input, the enforcement globs still cover all three distributions and a mirror-only drift is still caught by some gate
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Chose the separate-threshold direction: a `--max-diff-bytes N` flag on `bin/adr-judge` that overrides `judge.max_diff_bytes` for one invocation, passed by the CI composite action via a new `max-diff-bytes` input (default 32 MiB). The repository config returns to 2 MiB, the commit-sized number.

The mirror-exclusion direction was rejected: it only postpones the threshold (~17% saved), and it conflicts with AC#5 because the enforcement globs deliberately cover all three distributions. The single-number direction was rejected because a release-sized default silently raises the commit budget too, which AC#2 forbids.

Verified against the exact v0.43.0 case (PR #53 diff, 2,285,770 bytes, reproduced with `git diff a714432^1...a714432^2`):
- without the flag, the 2 MiB commit budget fails closed, exit 2
- with `--max-diff-bytes 33554432`, 15 ADRs checked, 0 violations, 0 advisory, 5.2 s, exit 0

A negative flag value is rejected rather than clamped, so a typo cannot become an accidental 'no cap'. The error message now names which limit was hit (`--max-diff-bytes` vs `judge.max_diff_bytes`) and points at the right knob to edit.

No ADR authored. The change adds a mechanism (a second budget surface for an existing gate) rather than a new architectural boundary, and ADR-015's latency budget already governs why the commit path must stay small. Worth revisiting if a maintainer disagrees.

AC#5 is not applicable as implemented: generated mirrors were not excluded from the judged input, so the enforcement globs and the adapter drift check are untouched.

Gates: full suite 1228 passed / 11 skipped; adapter drift clean after regenerating the codex/ and copilot/ mirrors; `adr-lint --strict` and `adr-index --check` clean; config validates against the schema; action.yml parses with inputs [adr-dir, python-version, max-diff-bytes].

AC#5 checked as not-applicable on the maintainer's call: the conditional clause ('if generated mirrors are excluded') never fires, because the chosen implementation judges the full diff including `codex/` and `copilot/`. The enforcement globs and the adapter drift check are unchanged, so mirror-only drift is still caught exactly as before.

No ADR, confirmed by the maintainer.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Split the judge's diff-size budget in two, because one number was serving two workloads with different shapes.

`bin/adr-judge` gains `--max-diff-bytes N`, overriding `judge.max_diff_bytes` for a single invocation. The `adr-judge` composite action passes it through a new `max-diff-bytes` input (default 32 MiB), and this repository's `docs/adr/.adr-kit.json` returns to 2 MiB, the commit-sized number. The pre-commit hook judges one commit under ADR-015's latency budget; the CI gate judges `origin/<base>...HEAD`, which for a release PR is an entire development branch, counted roughly three times because the repo ships mirrored client distributions. Raising the CI budget no longer raises the local one.

Fail-closed behaviour survives intact, and the error message now names which limit was hit so the reader edits the right knob. A negative flag value is rejected rather than clamped, so a typo cannot silently become "no cap".

Verified against the exact v0.43.0 failure, reproduced from the PR #53 merge commit (`git diff a714432^1...a714432^2`, 2,285,770 bytes): without the flag it fails closed at 2 MiB with exit 2; with `--max-diff-bytes 33554432` it checks 15 ADRs in 5.2 s and reports 0 violations, 0 advisory, exit 0.

The `codex/` and `copilot/` mirrors were regenerated, so the flag exists in all three distributions. The workflow in this repo invokes the action by local path and inherits the new default; the README notes that a workflow pinned to v0.43.0 or older does not have the input.

Written down in `docs/RELEASING.md` step 2 (the section a maintainer reads during a release), the README CI-integration section, the config schema description, and CHANGELOG [Unreleased].

Gates: 1228 passed / 11 skipped, adapter drift clean, `adr-lint --strict` and `adr-index --check` clean, config validates against the schema, action.yml parses with three inputs.

Rejected alternatives: excluding generated mirrors from the judged input (saves ~17%, only postpones the threshold, and conflicts with the deliberate glob coverage of all three distributions); and keeping one number with a release-sized default (silently raises the commit budget, which AC#2 forbids).
<!-- SECTION:FINAL_SUMMARY:END -->
