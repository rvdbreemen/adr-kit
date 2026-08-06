---
id: "ADR-025"
title: "Separate What Tracked Configuration May Select From What Only a Machine May Introduce"
status: "Accepted"
date: "2026-08-04"
binding: true
gate: "adr-config-trust-boundary-v1"
documents_shipped: true
verified_in:
  - "tests/test_adr_settings.py"
supersedes: []
superseded_by: null
related:
  - "ADR-017"
topics:
  - "configuration"
  - "security"
  - "llm routing"
aliases:
  - "trust boundary"
  - "select never introduce"
components:
  - "adr-settings"
  - "adr-judge"
symbols:
  - "SECRET_KEYS"
  - "apply_backend_setting"
context_scope: "global"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-025 Separate What Tracked Configuration May Select From What Only a Machine May Introduce

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: the rule is enforced in code and stated in the spec, and no decision carries it
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-025 constrains the backend selection ADR-017 introduced
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`docs/adr/.adr-kit.json` is committed. Anyone with commit access to a project
writes it, and every agent session in that project reads it. It selects which
backend judges a diff, and — since ADR-018 — which model embeds the ADRs.

The kit already enforces a boundary there. `judge.llm_cmd` accepts an
allowlisted bare binary name with a small set of safe flags, and refuses a path
component or an unrecognised flag. `bin/adr-settings` refuses to print a stored
credential, reporting `<set>` or `(not set)` plus a boolean about the
environment. The intent is written in the project guide and, since the gap
analysis, in `spec.md` R12.1 and R13.

No ADR carries any of it.

That inverts the model this kit sells. A deterministic gate is supposed to be
the mechanical expression of a recorded decision; here the gate exists and the
decision does not. Somebody widening the allowlist for a good local reason — a
self-hosted runtime whose binary is not on the list — has nothing to read that
explains why it is narrow. They will widen it, correctly by their lights, and
the boundary will be gone with no one having decided to remove it.

Of the records the gap analysis found missing, this is the one whose absence has
the largest consequence, because the thing it protects is arbitrary code
execution driven by a file a contributor can edit.

## Decision Drivers

* The tracked config file is writable by anyone with commit access; treat it as
  untrusted input to the machine that reads it.
* Which model judges a team's diffs is a team decision and belongs in the
  repository.
* Where a runtime lives, and what credential reaches it, are facts about one
  machine.
* A credential written into a committed file is a published credential.
* One registry. The judge backend and the embedding backend must not drift into
  two mechanisms with two boundaries.

## Considered Options

* **Tracked config selects from an enum; machine-local config introduces.**
* **Allow a command string in tracked config**, validated by an allowlist.
* **Move all backend configuration to machine-local**, so nothing about the
  model is shared.

## Decision Outcome

Chosen option: **repository-tracked configuration may select among backends an
operator has enabled, and may never introduce a command, an argument vector, an
endpoint or a credential**.

Concretely:

* **Backend choice is an enum**, resolving to a command table that lives in
  code. The committed file names a backend; it never supplies the thing that is
  executed. An enum a reviewer can read is a different security object from a
  string a reviewer has to reason about.
* **A credential in the tracked file is refused**, with the environment variable
  named in the error. Not ignored, not warned about — refused, because a key in
  a committed file has already been published and continuing quietly teaches the
  author that it worked.
* **An endpoint host is machine-local**, alongside the signer. Where a
  self-hosted runtime lives is a property of the machine, and putting it in a
  shared file both leaks internal topology and breaks every teammate whose
  machine differs.
* **The same rule binds the embedding backend**, because ADR-018 made it the same
  registry and the same setting. A boundary that holds for the judge and not for
  the embedder is not a boundary.

The split is not "public versus secret". It is **selection versus
introduction**: choosing among options an operator has already sanctioned, as
against creating a new option the operator never saw.

### Why not the alternatives

**An allowlisted command string** is what `judge.llm_cmd` does today, and it is
the weaker half of the current implementation rather than a model to extend. An
allowlist is a denylist wearing better clothes: every new backend widens it, and
the widening is where the mistake will be. It is retained only for backward
compatibility and is not the pattern new settings follow.

**Moving everything machine-local** would make the boundary trivially safe and
would also mean a team cannot agree on which model judges their code. That is a
real coordination loss, and the thing being coordinated — a model name — carries
no execution authority once the command table lives in code.

### Confirmation

Writing a credential into the tracked file produces a refusal naming the
environment variable. Writing a `judge.llm_cmd` with a path component or an
unlisted flag is refused. `bin/adr-settings` never prints a stored credential.
Setting an endpoint host in the tracked file is refused and directed to the
machine-local file.

## Decision Contract

### Must

* Resolve backend choice from an enum to a command table defined in code.
* Refuse a credential found in repository-tracked configuration, naming the
  environment variable to use instead.
* Keep endpoint hosts, credentials and the lifecycle signer machine-local.
* Apply the same rule to the embedding backend as to the judge backend.
* Report credential presence as a boolean about the environment, never as a
  value.
* Refuse an incomplete backend selection rather than writing a configuration the
  judge will silently degrade on.

### Must Not

* Execute a command, an argument vector or an endpoint that originates in a
  tracked file.
* Select a backend by probing which binaries happen to exist on the machine.
* Print, log or echo a stored credential.
* Widen the legacy `judge.llm_cmd` allowlist to accommodate a new backend;
  add the backend to the enum instead.

### Exceptions

* The legacy `judge.llm_cmd` allowlist is retained for existing projects. It is
  frozen: no new entries, no new flags.

### Verification

* `adr-config-trust-boundary-v1`: the gate that anchors this decision. It ships
  in `tests/test_adr_settings.py`, so `gate` carries the name and `binding` is
  true. It covers the credential refusal, the command-string refusal, and the
  redacted settings output.

## Consequences

### Positive

* The narrowness of the boundary now has a reason attached to it, which is what
  stops it being widened by someone acting in good faith.
* One rule covers 2 backends, so the embedding path cannot become a second,
  looser door.
* A misconfigured project fails loudly at the moment of writing rather than
  silently at the moment of judging.

### Negative

* Adding a backend now requires a code change rather than a config change. That
  is the point, and it is a real friction for someone running an unusual runtime.
  The machine-local file remains available to them.
* A team using the legacy `judge.llm_cmd` keeps a weaker path until they move to
  the enum. Freezing it bounds the exposure without breaking them.
* 2 configuration files instead of 1 is more to explain. `/adr-kit:settings`
  reports which file a value came from for exactly this reason.

## Pros and Cons of the Options

### Select from an enum; introduce only machine-locally

* Good, because a reviewer reads a name rather than reasoning about a string.
* Good, because the shared decision and the machine fact live where each belongs.
* Bad, because an unusual runtime needs a code change or a local override.

### Allowlisted command string in tracked config

* Good, because a new backend needs no release.
* Bad, because every widening is an opportunity to widen it wrongly, and the
  file is writable by anyone with commit access.

### Everything machine-local

* Good, because the tracked file carries no execution-adjacent value at all.
* Bad, because a team can no longer agree on which model judges their code.

## Open Questions

* None.

## Related Decisions

* Constrains ADR-017, which turned the LLM judge on by default and introduced
  backend selection.
* Binds ADR-018 and its successor ADR-020, which reuse the same registry for the
  embedding backend.
* Complements the machine-local signer rule of spec R8.1, which is the same
  principle applied to identity rather than to execution.

## References

* `bin/adr-settings` `SECRET_KEYS` — the redaction that keeps a stored
  credential out of the settings output.
* `bin/adr-settings` `apply_backend_setting` — the completeness refusals for
  host, openrouter and ollama.
* `docs/adr/.adr-kit.json` versus `docs/adr/.adr-kit.local.json` — the tracked
  and machine-local files this decision separates.
* `spec.md` R12, R12.1, R13, R8.1.
