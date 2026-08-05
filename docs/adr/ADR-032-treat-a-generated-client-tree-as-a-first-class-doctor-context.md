---
id: "ADR-032"
title: "Treat a Generated Client Tree as a First-Class Doctor Context"
status: "Proposed"
date: "2026-08-05"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
topics:
  - "doctor"
  - "client generation"
  - "mirrors"
  - "diagnostics"
aliases:
  - "generated tree doctor"
  - "mirror doctor context"
  - "doctor degradation"
components:
  - "adr-doctor reporting contract"
  - "generated client tree identity"
symbols:
  - "generated_tree_owner"
  - "client_root"
  - "RUNTIME_SUPPORT_FILES"
context_scope: "selective"
---

<!-- markdownlint-disable MD025 -->

# ADR-032 Treat a Generated Client Tree as a First-Class Doctor Context

## Status

Proposed, 2026-08-05.

## Status History

```yaml
status_history:
  - date: 2026-08-05
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: The doctor now runs from codex and copilot; what it may report there, and what it must never write, needs to be stated rather than inferred from code.
    changed_via: adr-kit
```

## Context and Problem Statement

`bin/adr-doctor` could not run from `codex/` or `copilot/` at all. It died at
import with `ModuleNotFoundError: No module named 'adr_settings'`, because
`COPY_ROOTS` carries four roots and none of them brings the eight modules `bin/`
imports from outside `bin/`. Of the 25 extensionless entrypoints in each mirror
it was the only failure.

Making the imports resolve is necessary and not sufficient. Two of the checks
compute `plugin_root / client` to find a client's owned configuration, which
hard-wires the assumption that `plugin_root` is the canonical payload root. It
is not, in a mirror: `codex/` **is** the plugin root for the Codex client --
`codex/.mcp.json` sits there, not at `codex/codex/.mcp.json`. Measured before
the fix, with the imports satisfied by hand, the doctor reported six failures
against paths that were never meant to exist.

So fixing the import error alone would have satisfied "the doctor runs from a
generated tree" while making it lie in six places. That is worse than the crash,
because a crash is obviously wrong and a confident wrong answer is not.

A third property matters and is easy to miss: the doctor's **default** mode is a
repair mode. `bin/adr-doctor:126` makes repair the default, and the init skill
runs `adr-doctor --fix-index docs/adr/`. Its generated-adapters check calls
`generate(plugin_root, check=False)` when it finds drift -- which, pointed at a
mirror, would have the doctor write into the tree it is inspecting.

What is genuinely new here is a reporting semantic, not a file list: a generated
client tree is a context in which most of the doctor's client checks are not
merely failing but *inapplicable*. Nothing in the repository states what the
doctor may claim there, so the behaviour would otherwise have to be inferred
from reading the code.

## Decision Drivers

* A diagnostic that reports a failure for something that cannot apply is worse
  than one that says nothing: it teaches people to ignore the report.
* The doctor is ADR-010's measurement surface for the three-client outcome
  contract, so what it reports is part of that contract, not an implementation
  detail.
* A repair-by-default tool pointed at a distribution artefact must not modify it,
  and that property should be asserted rather than assumed.
* The identity test has to be positive -- "this tree IS a Codex payload" -- not
  "my import failed", or the degrade path fires for unrelated reasons.

## Considered Options

* **Declare a generated tree a first-class doctor context**, with per-client
  re-rooting and an explicit `unsupported` status for what cannot apply.
* **Degrade the whole doctor** to a minimal mode when it detects a mirror,
  reporting almost nothing.
* **Leave the doctor unsupported in mirrors**, documenting that it must be run
  from the payload root.

## Decision Outcome

Chosen option: **declare a generated tree a first-class doctor context**,
because a user who installed the Codex payload has exactly one client and is
entitled to a real answer about it.

Three rules follow.

**Identity is positive.** A canonical payload root always carries
`clients/workflows.json`: it is the generator's own input, and the public
payload ships `clients` as a whole include root, so an installed payload has it
too. Its absence, combined with a client-specific plugin manifest, identifies a
generated tree. `RUNTIME_SUPPORT_FILES` therefore must never mirror
`clients/workflows.json` -- that absence is the marker.

**A mirror reports on its own client only.** The owning client's checks run
normally and report `healthy` or a real failure. The other two clients report
`unsupported`, not `failed`: they are not broken, they are not installed here.

**A mirror is never written to.** The generated-adapters check returns
`unsupported` before importing the generator at all, because a mirror carries no
canonical inputs to diff and repair mode would otherwise write into the tree
under inspection.

Degrading the whole doctor was rejected because it discards the answer the user
actually wants. Leaving it unsupported was rejected because the doctor is how a
user finds out their install is broken, and telling them to run it from a root
they do not have is not an answer.

### Confirmation

The doctor is driven from each generated tree as a subprocess against a
throwaway project, and the resulting JSON is asserted: `required_failures` is 0,
`generated-adapters` is `unsupported` and not required, the owning client's
`mcp-launcher` and `hook-package` are `healthy`, and the other two clients'
are `unsupported`. A SHA-256 snapshot of the tree taken before and after a
repair-mode run and a `--fix` run must be identical.

## Decision Contract

### Must

* Every module a `bin/` entrypoint imports must resolve inside the client tree
  it was mirrored into, verified transitively rather than one hop deep.
* A generated client tree must be identified by the absence of
  `clients/workflows.json` plus a client-specific plugin manifest, never by a
  failed import.
* A check that cannot apply in a generated tree must report `unsupported` with
  `required` false, and must say why.
* Running the doctor from a generated tree, in any mode including repair, must
  leave every file in that tree byte-identical.

### Must Not

* `clients/workflows.json` must not be mirrored into a generated client tree.
* The generator's own source must not be imported at module scope by anything a
  `bin/` entrypoint reaches, because it is deliberately not mirrored.
* A mirror must not report `failed` for a client that is simply not installed
  there.

### Exceptions

* `client_generation` may be imported lazily, inside the function that has
  already established the tree is not a mirror.

### Verification

* `adr-doctor-generated-tree-v1`

## Consequences

### Positive

* A user who installed only the Codex payload gets a real diagnosis of that
  install, from the payload they have.
* The import invariant becomes transitive, which closes the class of defect that
  produced both this outage and the v0.44.1 one -- the earlier test would have
  passed on this bug, because the missing module was one hop deeper than it
  looked.
* The no-write property is asserted rather than assumed, on a tool whose default
  mode repairs.

### Negative

* Sixteen files are now committed into the mirrors that were not there before,
  and each is a byte-copy that must be regenerated when its source changes.
  Editing `scripts/adr_settings.py` now requires running the generator; the
  drift check is what catches a forgotten run.
* The identity marker is an absence, which is a subtler contract than a
  presence. Mirroring `clients/workflows.json` later would silently switch the
  doctor from degrading to hard-failing, so a test asserts it stays absent.
* One import is now lazy for a reason a casual reader will not guess. The
  exclusion is allowed only for lazy imports, and a test asserts that an eager
  import of an excluded module fails -- otherwise the exclusion would become a
  hole big enough to reproduce the v0.44.1 outage with a green suite.

## Pros and Cons of the Options

### First-class doctor context

* Good, because the user gets an answer about the client they installed.
* Good, because `unsupported` distinguishes "not applicable" from "broken".
* Bad, because it adds sixteen mirrored files and a maintenance edge.

### Degrade the whole doctor in a mirror

* Good, because it is a small change and cannot report anything wrong.
* Bad, because it reports almost nothing, which for a diagnostic is close to
  being absent.

### Leave the doctor unsupported in mirrors

* Good, because it costs nothing and mirrors stay minimal.
* Bad, because the doctor is how a user discovers a broken install, and a user
  who installed a client payload has no payload root to run it from.

## Open Questions

* None.

## Related Decisions

* ADR-010 names `bin/adr-doctor` as the measurement surface for the
  three-client outcome contract.
* ADR-029 retired the native hook binary, whose undeclared module produced the
  v0.44.1 instance of this same defect class.

## References

* `scripts/client_generation_model.py` -- `COPY_ROOTS` and
  `RUNTIME_SUPPORT_FILES`.
* `bin/adr_doctor_models.py` -- `generated_tree_owner` and `client_root`.
* `bin/adr-doctor:126` -- repair is the default mode.
* `tests/generated_tree_imports.py` -- the transitive import closure walk.

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
