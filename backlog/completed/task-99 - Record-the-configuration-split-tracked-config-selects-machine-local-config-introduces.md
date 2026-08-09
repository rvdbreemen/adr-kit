---
id: TASK-99
title: >-
  Record the configuration split: tracked config selects, machine-local config
  introduces
status: Done
assignee: []
created_date: '2026-08-03 19:32'
updated_date: '2026-08-03 20:53'
labels:
  - adr
  - security
  - retrospective
dependencies: []
priority: high
ordinal: 2100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The rule is enforced in code — `judge.llm_cmd` is restricted to an allowlisted bare binary name with a small safe-flag set, an API key in the committed file is refused with the environment variable named instead — and it is written in the guide and now in the spec (R12.1, R13), but no ADR carries it.

That inverts the kit's own model: the deterministic gate is derived from a decision, and here the decision exists only as behaviour. Someone relaxing the allowlist for a good local reason has nothing to read that says why it is narrow.

Of the five retrospective records this is the one with the largest security consequence. `docs/adr/.adr-kit.json` is committed, so anyone with commit access writes it; it may select among backends an operator enabled and may never introduce a command, an argument vector, an endpoint or a credential. Where a self-hosted runtime lives is a fact about the machine and belongs in the gitignored local file, alongside the signer.

Record it, including the part that is easy to lose: the same rule governs the embedding backend, because it is the same registry and the same setting.

Spec: R12.1, R13, R8.1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR states the select-never-introduce rule and names the threat: the tracked file is writable by anyone with commit access
- [x] #2 It states that backend choice is an enum resolving to a command table in code, not a command string in config
- [x] #3 It states that a credential in the tracked file is refused with the environment variable named, and why refusing beats silently using it
- [x] #4 It states that the same rule binds the embedding backend, one registry and one setting
- [x] #5 It names what belongs machine-local instead: endpoint host, credentials, signer
- [x] #6 An Enforcement block guards the settings surface, or the ADR explains why the rule cannot be expressed mechanically
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ADR-025 written and Proposed, passing all gates.

It records the rule as **selection versus introduction** rather than as "public versus secret", which is the framing that makes it decidable: choosing among options an operator already sanctioned, against creating an option the operator never saw.

Two things the ADR settles beyond the task's ACs:

**The existing `judge.llm_cmd` allowlist is named as the weaker half, not as the pattern.** An allowlist is a denylist wearing better clothes — every new backend widens it, and the widening is where the mistake lands. It is retained for backward compatibility and **frozen**: no new entries, no new flags. New backends go in the enum. Without that sentence the ADR would have blessed the mechanism it exists to contain.

**AC#6 is answered as "explain why not".** The rule cannot be expressed as a `forbid_pattern`: it is about where a value lives and what shape it has, not about a string appearing in a diff. The Decision Contract carries the named gate `adr-config-trust-boundary-v1` and `verified_in: tests/test_adr_settings.py` instead, which is the ADR-004 route for a decision whose surface a regex cannot reach.

Acceptance is the maintainer's action.
<!-- SECTION:FINAL_SUMMARY:END -->
