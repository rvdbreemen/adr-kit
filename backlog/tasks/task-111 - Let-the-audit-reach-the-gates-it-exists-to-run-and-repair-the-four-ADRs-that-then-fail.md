---
id: TASK-111
title: >-
  Let the audit reach the gates it exists to run, and repair the four ADRs that
  then fail
status: To Do
assignee: []
created_date: '2026-08-03 19:35'
labels:
  - lint
  - audit
  - adr
dependencies: []
priority: medium
ordinal: 3800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The audit cannot answer the question its own rationale poses: "A clean judge over a set of vague ADRs proves nothing, because vague rules cannot be violated." Vagueness is what the evidence and clarity gates measure, and neither is reachable from `bin/adr-audit`. `run_lint()` builds a fixed argv and never passes `--gates`; `--help` has no gate selector; `parse_gates()` has exactly one call site, the CLI.

Correcting an earlier reading: `--strict` does **not** reach them; it adds `schema` only. Measured on this repository:

- `adr-lint --format json docs/adr` → `gates_enabled: [audit, completeness, consistency]`, 0 fails
- `--strict` → adds `schema`, still 0 fails
- `--gates all` → **pass 10, advisory 5, fail 4**

The audit calls a set with four quality failures clean.

**Be honest about the size before starting.** Turning the gates on turns this repository's own ADR set red on day one — first failure `ADR-001 clarity FAIL: 4 acronym(s) without inline expansion`, with ADR-002, ADR-003 and ADR-004 behind it. Either repair those first, or ship the gate advisory with a named deadline. Skipping that step is how this task stalls.

Also: `grep -rn adr-audit .github/ templates/` returns nothing. The whole-codebase mode — the one that asks "does the code as it stands obey the decisions as they stand" — never runs unless someone types it.

No ADR needed: ADR-009 already settles which gates are merge-time and which are authoring-time.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `bin/adr-audit` gains a gate selector, or a config key does — today `.adr-kit.json` can only skip gates, never add one
- [ ] #2 The four clarity failures are repaired and the five advisories triaged, before any gate is promoted to blocking
- [ ] #3 `skills/audit/SKILL.md` states which gates a green audit does and does not cover, so it is not read as a release gate
- [ ] #4 `templates/github-workflows/adr-audit.yml` ships, and this repository runs whole-codebase mode weekly or at release
- [ ] #5 A test asserts the audit runs the gate set it claims to run
<!-- AC:END -->
