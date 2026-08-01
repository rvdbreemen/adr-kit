---
id: TASK-84
title: 'Add /adr-kit:audit — lint plus judge in one demandable command'
status: To Do
assignee: []
created_date: '2026-08-01 10:34'
labels:
  - spec-gap
  - R15
  - audit
  - cli
dependencies: []
priority: medium
ordinal: 89500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R15. The combination already exists inside the guardian cheap tier (adr-lint + adr-judge + adr-retire + adr-status), but not as a command a person, hook or CI job can demand, and its judge looks at `HEAD~5..HEAD` rather than a chosen diff or the whole codebase.

**Why the two halves belong together.** A clean judge over vague ADRs proves nothing, because vague rules cannot be violated. A sharp ADR set nobody checks the code against is documentation, not governance. "Are we still on course?" needs both answers, and the caller should not have to know they come from two binaries.

**Two modes.** Diff mode is the default in a hook or PR context. Whole-codebase mode answers the question no per-diff gate can: does the code as it stands obey the decisions as they stand? A rule added after a file was written has never been applied to that file. Mechanically that is a diff against the empty tree, so every line reads as added and `forbid_pattern` applies repo-wide; `require_pattern` already reads a snapshot and needs no change. Such a diff is large — which is what the separate CI diff budget from TASK-73 exists for.

**Exit codes must separate the two failures.** "Your ADRs are not good enough" and "your code violates an ADR" have different owners; one conflated non-zero exit tells the caller nothing about what to fix.

**Naming.** `bin/adr-audit` already exists and is the init discovery scanner. Either rename it to what it does (`adr-discover`) or do not reuse the word. Two things called audit that audit different things is exactly the ambiguity ADRs are meant to prevent.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 /adr-kit:audit runs the ADR lint and the code judge in one invocation and reports both results
- [ ] #2 Diff mode and whole-codebase mode are both supported, and whole-codebase mode really does apply forbid rules to files no recent diff touched
- [ ] #3 Exit codes distinguish ADR-quality failure from code-violation failure from tooling error
- [ ] #4 The naming collision with bin/adr-audit is resolved rather than documented around
- [ ] #5 The command is usable from CI and from a hook without a second wrapper
- [ ] #6 Whole-codebase mode passes the right diff budget instead of failing closed on size
<!-- AC:END -->
