---
id: TASK-84
title: 'Add /adr-kit:audit — lint plus judge in one demandable command'
status: Done
assignee: []
created_date: '2026-08-01 10:34'
updated_date: '2026-08-02 19:32'
labels:
  - spec-gap
  - R15
  - audit
  - cli
dependencies: []
modified_files:
  - bin/adr-audit
  - bin/adr-discover
  - bin/adr_doctor_core.py
  - skills/audit/SKILL.md
  - skills/adr/SKILL.md
  - skills/init/SKILL.md
  - clients/workflows.json
  - scripts/client_generation_model.py
  - packaging/executables.json
  - .github/workflows/validate.yml
  - tests/test_adr_audit_command.py
  - tests/test_adr_discover.py
  - tests/test_template_profiles.py
  - tests/test_documentation_contracts.py
  - tests/test_native_client_packages.py
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
- [x] #1 /adr-kit:audit runs the ADR lint and the code judge in one invocation and reports both results
- [x] #2 Diff mode and whole-codebase mode are both supported, and whole-codebase mode really does apply forbid rules to files no recent diff touched
- [x] #3 Exit codes distinguish ADR-quality failure from code-violation failure from tooling error
- [x] #4 The naming collision with bin/adr-audit is resolved rather than documented around
- [x] #5 The command is usable from CI and from a hook without a second wrapper
- [x] #6 Whole-codebase mode passes the right diff budget instead of failing closed on size
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`bin/adr-audit` runs `adr-lint` and `adr-judge` in one invocation and reports both, so a caller does not have to know the two answers come from two binaries. `skills/audit/SKILL.md` plus a registered `audit` workflow gives it to all three clients.

**Whole-codebase mode really reaches untouched code.** It diffs against the empty tree (`4b825dc…`), so every line reads as added and `forbid_pattern` applies repository wide. The right-hand side is the working tree rather than HEAD, so a local run answers about the code in front of the person asking; in a CI checkout the two are the same bytes. A test proves a `print(` in a file committed before the rule existed is caught, while the diff of the most recent commit is clean — the only evidence that matters for this mode.

**Exit codes separate the owners:** 0 clean, 1 code violates an Accepted ADR, 3 the ADR set fails its own gates, 4 both, 2 the audit could not run. 3 and 4 sit above 1 so a caller checking `!= 0` still blocks while a caller who cares can tell the cases apart; exit 2 keeps its toolkit-wide meaning that could-not-answer is never answering no.

**Naming collision resolved, not documented around:** the init discovery scanner is now `bin/adr-discover` (with `tests/test_adr_discover.py`), and `bin/adr-audit` is the new command. Whole-codebase mode passes the CI-sized 33,554,432-byte budget from TASK-73 rather than failing closed on size; the repository's own diff is 9.85 MB.

Two contract tests counted skills with literals (16 per client, 48 total) and now read `WORKFLOW_IDS`. 12 new tests in `tests/test_adr_audit_command.py`; full suite green (1382 passed, 15 skipped).
<!-- SECTION:FINAL_SUMMARY:END -->
