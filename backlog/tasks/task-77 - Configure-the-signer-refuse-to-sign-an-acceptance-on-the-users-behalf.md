---
id: TASK-77
title: Configure the signer; refuse to sign an acceptance on the user's behalf
status: Done
assignee: []
created_date: '2026-08-01 10:32'
updated_date: '2026-08-02 00:36'
labels:
  - spec-gap
  - R8
  - lifecycle
  - audit-trail
dependencies: []
modified_files:
  - bin/adr
  - codex/bin/adr
  - copilot/bin/adr
  - tests/test_adr_lifecycle.py
  - tests/test_adr_open_questions.py
  - tests/test_selectable_formats.py
  - CHANGELOG.md
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
- [x] #1 The signer is read from machine-local config; `git config user.name` is offered as a proposed default during install and upgrade
- [ ] #2 /adr-kit:settings can show and change the signer
- [x] #3 A lifecycle command that would write a Status History entry with no configured signer and no explicit --changed-by exits non-zero with an actionable message instead of writing 'adr-kit'
- [x] #4 No shipped path can produce a Status History entry whose actor is the tool itself
- [x] #5 Existing ADRs carrying 'adr-kit' as actor are reported by a check so they can be corrected deliberately
- [x] #6 The docs state plainly what the signature does and does not prove
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The status-history actor is now configured rather than defaulted, and an unsigned transition is refused instead of signed by the tool.

`--changed-by` no longer defaults to `adr-kit`. Resolution is: explicit flag, then `lifecycle.signer` from the gitignored machine-local config, then refuse with a message that names the fix and offers `git config user.name` as a proposal. Nothing is written on refusal.

`bin/adr signer` ships with three modes: show (with the git proposal when unset), `--set` (writes the machine-local config atomically), and `--audit`, which lists history entries with no human actor. That audit immediately found six in this repository: ADR-012, 013, 015, 016 and 017 record `adr-kit` as the accepting actor, and ADR-001 records the recovered `unknown`. Correcting them means editing history, so the command reports rather than rewrites.

One design correction during implementation. The first version resolved the signer at the command call site, which put the check ahead of `assert_legal_transition` - so an illegal transition reported "no signer configured" instead of naming the illegality. Resolution moved inside `mutate_status`, after legality. Validate the act before the actor; otherwise the error sends the user to fix the wrong thing. A regression test pins that ordering.

Test fallout was fifteen lifecycle invocations across three files that relied on the old default. They now pass an explicit signer, which is what a test of lifecycle behaviour should do anyway. Seven of those edits were wrong on the first pass - the patcher injected the flag into `adr-related` and `adr-doctor` calls that do not accept it - and were reverted before landing.

Gates: 1255 passed / 11 skipped, adapter drift clean.

AC #2 is not met and is deliberately left to TASK-78: there is no `/adr-kit:settings` command yet, so `bin/adr signer` is the interim surface. When the settings command lands it should delegate here rather than write the file itself.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
