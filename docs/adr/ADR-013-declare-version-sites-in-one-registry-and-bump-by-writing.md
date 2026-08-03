---
id: "ADR-013"
title: "Declare Version Sites in One Registry and Bump by Writing"
status: "Accepted"
date: "2026-07-22"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
topics:
  - "versioning"
  - "registry"
  - "release tooling"
aliases:
  - "version sites"
  - "bump writer"
  - "single source of version"
components:
  - "bump-version"
  - "packaging"
---

<!-- markdownlint-disable MD025 -->

# ADR-013 Declare Version Sites in One Registry and Bump by Writing

## Status

Accepted, 2026-07-22.

## Status History

```yaml
status_history:
  - date: 2026-07-22
    status: Proposed
    changed_by: Claude
    reason: Amends ADR-012 after the 0.38.0 release needed nine hand-edits across four discovery rounds
    changed_via: adr-kit
  - date: 2026-07-22
    status: Accepted
    changed_by: adr-kit
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-012 established the release flow and named the version-bearing files as a
fixed list enforced by `scripts/check-release-version.py`. Running that flow for
real on 0.38.0 exposed a weakness in the mechanism, not in the decision.

Cutting 0.38.0 required typing the version into nine files across four discovery
rounds, each round revealed only by re-running a different tool:

1. the CHANGELOG heading (the canonical read-source);
2. two Claude manifests, revealed by the generator aborting;
3. the Codex plugin, Copilot plugin and Copilot marketplace manifests, revealed by
   the generator aborting again;
4. three template version stamps, revealed only by a five-minute `pytest` run.

The README version pins (`adr-judge@vX`, `rev: vX`) were caught by nothing at all
and had silently pointed at v0.34.0 while 0.37.0 shipped.

Four properties caused this:

- **No writer.** `expected_version()` reads the CHANGELOG, but nothing writes the
  version anywhere; every other site is hand-maintained.
- **A duplicated site list.** The knowledge of where versions live was spread over
  `validate_manifests()`, `check-release-version.py`, and three separate pytest
  assertions, which can drift apart.
- **First-failure aborts.** The generator raised on the first stale manifest, so a
  bump became a fix-one-and-rerun loop.
- **An uneven feedback ladder.** Manifests failed fast, template stamps failed slow,
  README pins never failed. A bump could pass generation and lint and still be wrong.

A hand-edit also failed silently once: the pre-commit stamp is
`ADR_KIT_WRAPPER_VERSION="0.37.0"` and an unquoted regex replacement matched
nothing, which only surfaced on a later re-test.

## Decision Drivers

- One place to type a release version, and one place to declare where versions live.
- Adding a version-bearing file must not require teaching three separate tools.
- A bump must surface its complete work list in one pass.
- Everything that carries a version must be gated before a release ships.

## Considered Options

- One declarative registry consumed by a writer, the gate, the generator and the tests.
- Keep the fixed lists but extend each tool separately to cover stamps and README pins.
- Derive the version from a single manifest at build time and stop storing it elsewhere.

## Decision Outcome

Chosen: the declarative registry with a writer.

### The registry

`packaging/version-sites.json` declares the canonical source and every
version-bearing site with an explicit read/write strategy (`json` with an RFC 6901
pointer, or `regex`/`regex_all` with a prefix/version/suffix capture). It also
declares the negative invariant that the Codex local marketplace must *not* carry a
version because it inherits one, and records that README history markers such as
"introduced in v0.31.0" are deliberately not sites.

### One writer, four readers

`scripts/version_sites.py` is the shared implementation. `scripts/bump-version.py
X.Y.Z` writes the version to every declared site and ensures the CHANGELOG release
heading exists. `scripts/check-release-version.py`, the client-adapter generator and
`tests/test_version_sites.py` read the same registry. Declaring a new site is a
one-line change that every tool picks up at once, and a test asserts the registry
still covers the manifests the generator independently validates.

### Report everything, abort never

Both the registry checks and `validate_manifests()` now collect all stale sites and
report them together, with the exact command that fixes them.

### Scope of the gate

Template version stamps and README version pins are now declared sites, so
`release-publish.yml` and `/release-adr-kit` catch them at release time instead of a
slow test run or nothing at all.

### Confirmation

Against the 0.38.0 tree the registry reports eleven sites consistent; asked for
0.39.0 it lists all eleven mismatches in a single pass, where the previous flow
revealed them over four rounds.

## Consequences

### Positive

- A release version is typed once and written everywhere; the silent-regex and
  missed-file failure modes disappear.
- The complete work list appears in one pass instead of one error per tool run.
- Template stamps and README pins are gated for the first time.
- Adding a version-bearing file is a registry line, not three code edits.

### Negative

- One more indirection: contributors must learn that versions are declared, not edited.
- A malformed registry entry fails the release; the tests cover shape and coverage to
  keep that failure loud and early.

## Pros and Cons of the Options

### Registry plus writer

- Good: one source of truth, one writer, uniform coverage, cheap to extend.
- Bad: an extra file and module to understand.

### Extend each tool separately

- Good: no new concepts.
- Bad: keeps the duplicated list that caused the drift, and still has no writer.

### Derive the version at build time from one manifest

- Good: fewest stored copies.
- Bad: the published client manifests and templates must physically carry the version
  for the clients to read, so it cannot be fully derived.

## Related Decisions

- ADR-012 (Release to the Three Coding-Agent Marketplaces From the Public Repository):
  this ADR amends its version-consistency invariant, which is now sourced from the
  registry and enforced by a writer rather than a fixed list.

## References

- `packaging/version-sites.json`, `scripts/version_sites.py`, `scripts/bump-version.py`.
- `scripts/check-release-version.py`, `scripts/client_generation_artifacts.py`.
- `tests/test_version_sites.py`, `docs/RELEASING.md`.
- TASK-50. Evidence: the 0.38.0 release (TASK-47).

## Enforcement

```json
{
  "llm_judge": false,
  "llm_judge_reason": "no code surface: this decision governs process or documentation, so there is no diff for a model to judge it against"
}
```
