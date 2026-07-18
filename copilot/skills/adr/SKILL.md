---
name: adr
description: Create or review Architecture Decision Records with ADR Kit's four verification gates and lifecycle rules.
license: MIT
---

# ADR authoring for GitHub Copilot CLI

Use this skill when a decision has long-term impact, crosses components, or
constrains later work. Do not create an ADR for a local bug fix or a refactor
that preserves the architecture.

Before writing:

1. Call `adr-kit.adr_context` with the task and absolute `project_root`.
2. Read the returned Accepted ADRs and report any conflict.
3. Find the next unused `ADR-NNN` under `docs/adr/`.

Draft from the bundled `templates/adr-template.md`. The plugin root is the
grandparent of this skill's `skills/` directory, as shown in Codex's skill
catalog. Start new decisions as Proposed. Require all four gates before
acceptance: Completeness, Evidence, Clarity, and Consistency. Include at least
two alternatives, positive and negative consequences, explicit risks and
mitigations, and verifiable references.

Use the bundled lifecycle CLI for state changes:

```text
python <plugin-root>/bin/adr propose ...
python <plugin-root>/bin/adr accept ...
```

Never rewrite an Accepted decision. Supersede it through `the ADR Kit supersede skill`.
