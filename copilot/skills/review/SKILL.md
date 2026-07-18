---
name: review
description: Audit a branch or pull request against ADRs and identify architectural decisions that are not documented yet.
license: MIT
---

# ADR branch review

Determine the merge base with the requested base ref, defaulting to
`origin/main`. Read the committed range diff and commit intent.

1. Call `adr-kit.adr_judge` with the range diff and absolute `project_root`.
2. Run `python <plugin-root>/bin/adr-audit --root <workspace>` for local
   decision-shaped evidence.
3. Inspect the diff and intent for new long-lived contracts not represented by
   an ADR.

Report enforcement and discovery separately. Draft Proposed ADRs only for
candidates the user selects. Do not mutate Accepted ADRs.
