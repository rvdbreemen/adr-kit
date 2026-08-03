---
id: TASK-110
title: Make an unattended acceptance refuse rather than sign
status: To Do
assignee: []
created_date: '2026-08-03 19:35'
labels:
  - lifecycle
  - correctness
dependencies: []
priority: high
ordinal: 3700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr accept ADR-NNN` succeeds unattended. With `lifecycle.signer` configured — which is now the common case, since v0.44.1's derivation makes it the common case — it writes the user's name, a plausible reason and today's date into an immutable history entry the user never saw.

False attribution is worse than a missing one. That is R8's own argument, turned against the command that implements it.

The consent step is prose on all three clients (`skills/adr/SKILL.md:31-34`, and `clients/workflows.json`'s `adr` workflow step 6), and no hook intercepts it: `adr_hook_core:543` returns noop for any tool outside `WRITE_TOOLS`, so a Bash call to `adr accept` is injected nothing and blocked never. R14's own reading says a guarantee needs something that fires without the model choosing to.

No ADR needed: ADR-011 records the human-gated principle. What is missing is enforcement at the boundary.

**This changes the exit behaviour of a shipped command.** It needs a CHANGELOG entry that names the break, and `--auto --auto-mode auto` stays as it is, because R1 grants the init flow that exception explicitly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An unattended `bin/adr accept` refuses instead of signing, using the `--confirm` shape auto-accept's assist mode already uses at `bin/adr:686`
- [ ] #2 `--auto --auto-mode auto` keeps working, because R1 grants init that exception
- [ ] #3 A test asserts that accept with closed stdin and no confirmation writes nothing and exits non-zero
- [ ] #4 `bin/adr signer --audit` runs somewhere real — the guardian sweep or CI — rather than existing and never being called
- [ ] #5 The CHANGELOG names the behaviour change explicitly, since scripts may depend on the old exit
<!-- AC:END -->
