---
name: judge
description: Check the staged diff against Accepted ADR enforcement rules, then review semantic rules in the active Codex session.
license: MIT
---

# Judge a staged diff

Read `git diff --cached --unified=3`. If empty, stop and say that nothing is
staged. Call `adr-kit.adr_judge` with the diff and absolute `project_root`.

For each violation offer exactly three paths:

1. The decision changed: draft a superseding ADR.
2. The ADR does not cover this case: propose a narrowly scoped amendment.
3. The ADR stands: propose the smallest compliant code change.

For ADRs marked `llm_judge: true`, assess the diff in the active Codex session
after the deterministic result. Never send code to another model or provider
without explicit user approval.
