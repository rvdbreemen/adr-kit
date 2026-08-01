---
id: TASK-77
title: Configure the signer; refuse to sign an acceptance on the user's behalf
status: To Do
assignee: []
created_date: '2026-08-01 10:32'
labels:
  - spec-gap
  - R8
  - lifecycle
  - audit-trail
dependencies: []
priority: high
ordinal: 82500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R8 and R8.1. Nothing today establishes that a human was present, and nothing authenticates who.

`bin/adr:772` reads exactly `parser.add_argument("--changed-by", default="adr-kit", help="status history actor")`. Omit the flag and the durable record says the tool accepted its own ADR. Supply it and it is unvalidated free text: an agent types `--changed-by "User: Robert van den Breemen"` and the file carries a human signature no mechanism ever checked. `--date` is equally arbitrary.

**What to build.**

The recorded actor becomes `User: <user>` where `<user>` is configured, not passed ad hoc:
- asked during installation, and on upgrade when unset;
- changeable through the settings surface (TASK-79);
- the installer *proposes* `git config user.name` for confirmation, never adopts it silently.

Storage matters: the signer belongs in the gitignored machine-local config next to `judge.host_client`, not in the tracked `.adr-kit.json`. A committed signer puts one person's name on every teammate's acceptance, which is a false attribution rather than a missing one.

And the default must go. With no configured signer and no explicit flag, a lifecycle command that writes a Status History entry **refuses**. An unsigned acceptance is a bug; a self-signed one is a lie in the audit trail.

Out of scope, worth stating: this does not make the signature cryptographically trustworthy. It makes it *attributable and deliberate*. Real non-repudiation would need signed commits, and that is a separate decision.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The signer is read from machine-local config; `git config user.name` is offered as a proposed default during install and upgrade
- [ ] #2 /adr-kit:settings can show and change the signer
- [ ] #3 A lifecycle command that would write a Status History entry with no configured signer and no explicit --changed-by exits non-zero with an actionable message instead of writing 'adr-kit'
- [ ] #4 No shipped path can produce a Status History entry whose actor is the tool itself
- [ ] #5 Existing ADRs carrying 'adr-kit' as actor are reported by a check so they can be corrected deliberately
- [ ] #6 The docs state plainly what the signature does and does not prove
<!-- AC:END -->
