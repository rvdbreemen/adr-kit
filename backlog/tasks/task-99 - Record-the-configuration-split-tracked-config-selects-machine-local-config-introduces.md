---
id: TASK-99
title: >-
  Record the configuration split: tracked config selects, machine-local config
  introduces
status: To Do
assignee: []
created_date: '2026-08-03 19:32'
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
- [ ] #1 An ADR states the select-never-introduce rule and names the threat: the tracked file is writable by anyone with commit access
- [ ] #2 It states that backend choice is an enum resolving to a command table in code, not a command string in config
- [ ] #3 It states that a credential in the tracked file is refused with the environment variable named, and why refusing beats silently using it
- [ ] #4 It states that the same rule binds the embedding backend, one registry and one setting
- [ ] #5 It names what belongs machine-local instead: endpoint host, credentials, signer
- [ ] #6 An Enforcement block guards the settings surface, or the ADR explains why the rule cannot be expressed mechanically
<!-- AC:END -->
