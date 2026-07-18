---
name: adr
description: Create or review Architecture Decision Records with ADR Kit's four verification gates and lifecycle rules.
license: MIT
---

# ADR authoring for Codex

Use this skill when a decision has long-term impact, crosses components, or
constrains later work. Do not create an ADR for a local bug fix or a refactor
that preserves the architecture.

Before writing:

1. Call `adr-kit.adr_context` with the task and absolute `project_root`.
2. Read the returned Accepted ADRs and report any conflict.
3. Run `python <plugin-root>/bin/adr profiles --format json`, then resolve the
   project body profile from `template.profile`. The default is `madr`. If the
   user chooses another format, accept only a returned id with
   `available: true` and use its returned template. The shipped alternatives
   are `nygard` and `canonical`; never invent a profile or replacement
   template.

Resolve the plugin root as the grandparent of this skill's `skills/` directory,
then run `python <plugin-root>/bin/adr new "Title" --adr-dir docs/adr`.
Use `--profile` only for a one-record override. Start new decisions as
Proposed. Require all four gates before
acceptance: Completeness, Evidence, Clarity, and Consistency. Include at least
two alternatives, positive and negative consequences, explicit risks and
mitigations, and verifiable references.

Use the bundled lifecycle CLI for state changes:

```text
python <plugin-root>/bin/adr propose ...
python <plugin-root>/bin/adr accept ...
```

Never rewrite an Accepted decision. Supersede it through `$adr-kit:supersede`.
