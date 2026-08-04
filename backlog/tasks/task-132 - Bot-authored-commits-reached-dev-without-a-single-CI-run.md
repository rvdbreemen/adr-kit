---
id: TASK-132
title: Bot-authored commits reached dev without a single CI run
status: To Do
assignee: []
created_date: '2026-08-04 19:34'
updated_date: '2026-08-04 23:01'
labels:
  - ci
  - process
  - branch-protection
dependencies: []
priority: high
ordinal: 106500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PR #60 was merged into `dev` at 2026-08-04 18:48 UTC carrying two commits that no workflow ever ran against:

- `70b0913` "Potential fix for pull request finding" — Copilot Autofix
- `e1f0fcd` "Fix adr_fixtures import path and bail-out typo per review" — copilot-swe-agent[bot]

`gh api repos/rvdbreemen/adr-kit/commits/e1f0fcd/check-runs` returns **zero check runs**. The green checks that were visible on the PR belonged to `d2932a7`, the head before those commits landed.

One of the two was wrong and broke the branch. `e1f0fcd` rewrote `from adr_fixtures import isolated_copy` to `from tests.adr_fixtures import isolated_copy` in three modules. `tests/` has no `__init__.py`, and pytest's prepend import mode puts the test file's own directory on `sys.path`, so the dotted form raises `ModuleNotFoundError` at collection. Reproduced on a clean worktree of `origin/dev`:

```
ERROR collecting tests/test_adr_audit_command.py
ERROR collecting tests/test_adr_lint_clarity.py
ERROR collecting tests/test_adr_policy.py
E   ModuleNotFoundError: No module named 'tests.adr_fixtures'
3 errors
```

So `dev` sat with three modules uncollectable — every test in them silently not running, which is worse than a red suite because the count still looks plausible.

`docs/RELEASING.md` already says to review commits a PR picks up after its first CI run and confirm CI is green for the final head. That instruction assumes a human is watching at the right moment. The gap is structural: a bot can push to a PR branch after the checks have gone green, and the merge button does not care.

Directions, in rough order of strength:

1. Require the status checks to be **up to date with the head** in branch protection (`strict` required status checks). GitHub then refuses a merge whose checks ran on an older commit. This is the fix that does not rely on anyone noticing.
2. Failing that, a merge-queue or a pre-merge job that re-runs on the merge commit.
3. At minimum, make the import shape explicit so this specific rewrite cannot be proposed again: either add `tests/__init__.py` and use dotted imports everywhere, or state the top-level convention in a comment where a reviewer will read it (done in the fix, but a convention in prose is weaker than a package boundary).

The fix itself is in the PR that restores the working import form. This task is about how it got in.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A commit pushed to a PR branch after checks pass cannot be merged without those checks re-running
- [x] #2 The repository's test-helper import convention is enforced by structure or documented where a reviewer meets it, not only by comment
- [x] #3 A run that fails to collect a module is distinguishable from a run where that module passed
- [ ] #4 dev's required contexts are raised to the same four as main, after the widened workflows have reported on a dev PR at least once
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
INVESTIGATION 2026-08-05 — THE STATED ROOT CAUSE IS FALSE. This record claimed `tests/` has no `__init__.py`, so `from tests.adr_fixtures import` raises ModuleNotFoundError at collection. That is not what happens. Without `__init__.py`, `tests/` is a NAMESPACE package, and `pytest.ini` sets `pythonpath = .`, so the dotted form resolves perfectly well. Primary evidence both ways: CI run 30946844278 shows six green legs on a tree carrying the dotted form; on this development machine `C:/Python312/Lib/site-packages/tests/__init__.py` exists and `import tests` resolves there, because a regular package always beats a namespace portion. So the dotted form works or fails depending on what is installed on the machine running the suite. The fix that landed (reverting to the bare `from adr_fixtures import`) is correct; only the recorded reason was wrong. Three source comments repeated the false version and have been corrected.

AC#1 was already satisfied before this task was written: `dev` and `main` both already require checks. What is missing is the STRICT (up-to-date-with-head) flag, which is AC#4.

AC#2 and AC#3 are done: tests/test_import_convention.py parses the AST of every test module and fails on any `tests.*` import (verified it bites with a probe module), plus a second assertion that fails if `tests/__init__.py` ever appears, since that would make the ban arbitrary. CI now runs `pytest --collect-only -q --strict-markers` as its own named step before the suite, so an uncollectable module is a distinct, named failure rather than an absence hidden behind a plausible pass count.

AC#4 IS DEFERRED AND NEEDS A DECISION. The maintainer authorised the branch-protection change on 2026-08-05, but did so without one consequence that the investigation then found: `adr-judge-self.yml` produces the `ADR Enforcement (declarative)` context and has NO push trigger, and cannot have one — `GITHUB_BASE_REF` is empty on push. Raising dev's required contexts to main's four therefore rejects direct pushes to `dev` permanently; every commit would have to arrive through a pull request. That is a workflow change, not a settings tweak, and the maintainer should confirm it knowing that.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-04 19:41
---
Resolved in the merge-back PR (#62) plus two repository settings changes. Recording what was actually found, because the cause was wider than this task first described.

**Branch protection before:** `main` was protected with reviews and `enforce_admins`, but `required_status_checks` had **zero contexts and `strict: null`** — so no check was ever required to pass. `dev` had **no protection at all**. That is how `e1f0fcd` merged: nothing was checking, and nothing required the checks to belong to the head being merged.

**Applied:** `strict: true` on both branches. On `main` the required contexts are `pytest`, `validate`, `ADR Enforcement (declarative)` and `generated ADR indexes are up to date`. `adr-readiness` is deliberately excluded — it is red by design while Proposed ADRs are open, and a check that is sometimes correctly red cannot be a merge gate.

**The trap I walked into, recorded so the next person does not.** Requiring those four on `dev` made `dev` unmergeable within a minute, because three of the four workflows only trigger on PRs into `main`:

| workflow | check | PR trigger before |
| --- | --- | --- |
| adr-judge-self | ADR Enforcement (declarative) | main only |
| adr-index-check | generated ADR indexes are up to date | main only |
| adr-lint-self | pytest, adr-lint smoke test | main only |
| validate | validate + 6 matrix jobs | dev, main |
| adr-readiness | adr-readiness | dev, main |

A required context that no workflow produces never reports, and the PR waits forever. `dev` is therefore back to `strict: true` with `validate` as its only required context — which alone closes the hole this task is about, since strict is what rejects checks that ran on an older commit.

**Still open, and it is the real coverage finding:** `dev` never ran the ADR gates at all. Only the suite and readiness. #62 widens the three workflows to `branches: [dev, main]`. Once that is merged and those checks have reported on a `dev` PR at least once, raise `dev`'s required contexts to the same four as `main`. Doing it before they exist repeats the lockout.
---
<!-- COMMENTS:END -->
