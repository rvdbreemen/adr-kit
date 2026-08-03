---
id: "ADR-008"
title: "Resolve the Enforcement Engine from a Version-Ranked Root Set Including the Checkout"
status: "Accepted"
date: "2026-07-18"
binding: false
gate: null
documents_shipped: true
verified_in:
  - "tests/test_packaging_contract.py"
supersedes: []
superseded_by: null
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-008 Resolve the Enforcement Engine from a Version-Ranked Root Set Including the Checkout

## Status

Accepted, 2026-07-18.

## Status History

```yaml
status_history:
  - date: 2026-07-18
    status: Proposed
    changed_by: Claude
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-07-18
    status: Proposed
    changed_by: Claude
    reason: Behavior shipped in v0.34.0; hook selected the checkout engine on commit 3961e72
    changed_via: adr-kit lifecycle
  - date: 2026-07-18
    status: Accepted
    changed_by: Robert van den Breemen
    reason: "Human approval: records the v0.34.0 engine-resolution decision after review"
    changed_via: adr-kit lifecycle
  - date: 2026-07-20
    status: Accepted
    changed_by: Codex
    reason: Reverified checkout-engine packaging coverage after native plugin-root hook migration; decision unchanged
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

The pre-commit hook does not contain the enforcement engine. It resolves
`bin/adr-judge` at commit time and delegates to it. Until v0.34.0 the candidate
set was exactly three installed plugin caches: Claude Code, Codex, and Copilot.
The hook picked whichever manifest declared the highest version. A working
checkout of ADR Kit was never a candidate, even when the developer was standing
in one.

This is deliberate for ordinary projects. It is wrong for exactly one project:
ADR Kit itself, whose checkout is by construction ahead of any published
release. The result is a guaranteed version skew between the hook script in the
repository and the engine that executes it.

The skew produced a concrete failure while releasing v0.34.0. The repository's
own `.githooks/pre-commit` invoked the engine with `--snapshot staged`, a flag
introduced by TASK-32.3. The resolved engine was the installed Copilot payload
at version 0.33.0, which does not accept it:

```
adr-judge: error: unrecognized arguments: --snapshot staged
```

The judge exited 2 and the release commit was refused. The hook was calling a
contract that its own repository had defined but that the selected engine
predated.

The same class of failure reaches contributors. Anyone who clones ADR Kit to
work on the engine is judged by a stale release rather than by the code they
are editing, so a contributor cannot exercise the enforcement change they just
wrote. The failure mode is silent in the good case and confusing in the bad
one: the hook reports a violation, or fails to report one, on behalf of an
engine that is not the one under review.

## Decision Drivers

* A change to the enforcement engine must be exercised by the hook in the same
  checkout, or the engine cannot be developed against its own gate.
* Ordinary projects must keep the existing behavior. Their checkout contains no
  engine and must continue to resolve an installed plugin.
* Resolution must stay deterministic and explainable. A developer must be able
  to answer "which engine judged this commit" without reading the hook.
* The hook must not gain a second selection mechanism. One rule is easier to
  reason about than a rule plus an exception.
* Resolution must not require configuration, because the hook runs before any
  project-specific setup is guaranteed to exist.

## Considered Options

* Add the checkout as another candidate root, ranked by manifest version like
  every other root.
* Prefer a checkout unconditionally over any installed plugin.
* Add an environment variable such as `ADR_KIT_ENGINE` that names the engine
  path explicitly.
* Do nothing, and require contributors to reinstall the plugin from their
  checkout before each commit.

## Decision Outcome

Chosen option: **add the checkout as another candidate root, ranked by manifest
version like every other root**, because it removes the skew without
introducing a second selection rule.

The hook resolves the repository root with `git rev-parse --show-toplevel` and
appends it to the candidate list only when that root contains both
`bin/adr-judge` and `.claude-plugin/plugin.json`. Those two files together
identify an ADR Kit checkout; a project that merely happens to have a `bin`
directory does not qualify. The existing loop then reads each candidate's
manifest and keeps the highest version, so the checkout wins when it is ahead
and an installed plugin still wins when the checkout is behind.

For every project that is not ADR Kit, the guard fails and the candidate list
is unchanged. The decision therefore changes behavior in one repository and is
inert everywhere else.

### Confirmation

Confirm the decision by observing which engine the hook selects. On the
v0.34.0 release commit in this repository the hook reported:

```
[adr-kit] Engine: D:/Users/.../adr-kit/bin/adr-judge (manifest version 0.34.0)
```

naming the checkout rather than the installed 0.33.0 payload, and the judge
then completed with `0 violations`. In a project without an engine, the
candidate guard is false and resolution is unchanged.

## Consequences

### Positive

* A change to the engine is judged by that change, so enforcement work can be
  developed and reviewed inside its own gate.
* The failure that blocked the v0.34.0 release cannot recur: the hook and the
  engine now come from the same commit.
* Contributors do not need to reinstall a plugin to get an accurate local
  verdict.
* Ordinary projects are unaffected, because the guard requires an engine and a
  Claude plugin manifest in the repository root.

### Negative

* A contributor with an edited, broken engine in their checkout is now judged
  by that broken engine. This is the intended trade: the checkout is what they
  are asking to be judged by. `ADR_KIT_HOOK_DISABLE=1` remains the escape.
* The hook runs one additional `git rev-parse` per commit. The cost is
  negligible next to reading the staged diff, and the call is already made
  later in the script.
* A checkout whose manifest version is lower than an installed plugin is still
  ignored, which can surprise someone testing a downgrade. The reported engine
  line makes the choice visible.

## Pros and Cons of the Options

### Add the Checkout as a Version-Ranked Candidate

* Good, because it reuses the existing ranking rule instead of adding a second
  mechanism, so "highest manifest version wins" remains the whole story.
* Good, because the two-file guard makes it inert for ordinary projects.
* Bad, because version ranking can still select an installed plugin over a
  checkout that deliberately declares an older version.

### Prefer a Checkout Unconditionally

* Good, because a contributor's local engine always wins, with no version
  reasoning at all.
* Bad, because it breaks the single ranking rule and makes the hook's choice
  depend on where the commit happens rather than on what is newest.

### Name the Engine Through an Environment Variable

* Good, because it is explicit and covers engines outside any known layout.
* Bad, because it must be set correctly on every machine and in every shell
  that commits, so the default path stays broken and the failure returns
  whenever the variable is missing.

### Do Nothing

* Good, because it keeps the hook unchanged.
* Bad, because it leaves the engine undevelopable against its own gate and
  makes every release depend on the maintainer remembering to reinstall.

## Related Decisions

* ADR-004 makes `bin/adr-judge` at pre-commit the single fail-closed
  enforcement floor. This decision determines which copy of that floor runs.
* ADR-001 keeps cost-bearing model behavior opt-in. Engine resolution is
  deterministic and adds no model call.
* ADR-006 prepares platform-local marketplaces for installed clients. That
  decision governs installed payloads; this one governs which payload the hook
  selects.

## References

* `templates/githooks/pre-commit` and `.githooks/pre-commit`, the candidate
  root block guarded on `bin/adr-judge` and `.claude-plugin/plugin.json`.
* `tests/test_packaging_contract.py`, which pins both hook copies as shipped
  executable entry points.
* Commit `3961e72` (v0.34.0), which introduced the candidate root.
* `docs/reviews/2026-07-18-source-audit/FINDINGS.md`, which records the
  `--snapshot staged` enforcement contract this skew violated.

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "_self_root",
      "path_glob": "templates/githooks/pre-commit",
      "message": "The shipped hook must keep the checkout as a candidate engine root (ADR-008)."
    }
  ]
}
```
