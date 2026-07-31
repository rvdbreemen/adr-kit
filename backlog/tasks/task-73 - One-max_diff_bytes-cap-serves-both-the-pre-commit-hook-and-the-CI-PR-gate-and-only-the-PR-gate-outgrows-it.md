---
id: TASK-73
title: >-
  One max_diff_bytes cap serves both the pre-commit hook and the CI PR gate, and
  only the PR gate outgrows it
status: To Do
assignee: []
created_date: '2026-07-31 06:10'
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
  - schemas/adr-kit-config.schema.json
  - bin/adr-judge
  - .github/actions/adr-judge/action.yml
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
- [ ] #1 A release-sized PR diff no longer fails the CI enforcement gate on size alone, without disabling the cap
- [ ] #2 The pre-commit path keeps a threshold appropriate to a single commit; raising the CI limit does not silently raise the local one
- [ ] #3 A diff that genuinely was not scanned still fails closed with an actionable message; no code path reports success for an unscanned diff
- [ ] #4 The chosen approach is written down where a maintainer will find it during a release, since this has now bitten once at v0.43.0
- [ ] #5 If generated mirrors are excluded from the judged input, the enforcement globs still cover all three distributions and a mirror-only drift is still caught by some gate
<!-- AC:END -->
