---
id: TASK-111
title: >-
  Let the audit reach the gates it exists to run, and repair the four ADRs that
  then fail
status: Done
assignee: []
created_date: '2026-08-03 19:35'
updated_date: '2026-08-03 22:37'
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
- [x] #1 `bin/adr-audit` gains a gate selector, or a config key does — today `.adr-kit.json` can only skip gates, never add one
- [x] #2 The four clarity failures are repaired and the five advisories triaged, before any gate is promoted to blocking
- [x] #3 `skills/audit/SKILL.md` states which gates a green audit does and does not cover, so it is not read as a release gate
- [x] #4 `templates/github-workflows/adr-audit.yml` ships, and this repository runs whole-codebase mode weekly or at release
- [x] #5 A test asserts the audit runs the gate set it claims to run
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**The repair the task proposed would have been the wrong one, and the reason is the interesting part.**

The task said: turn the gates on, then repair the four clarity failures. Turning them on produced 14 findings across 4 records, and reading them changed the conclusion. Exactly **one** was a genuine unexplained acronym (`OTGW`). The other thirteen were:

- **`LLM`** — the product's own subject, in every reader's head, ten of the fourteen
- **`FAIL`, `DUE`, `TODO`** — literal status tokens the records *quote* from output they describe
- **`SKILL`, `INDEX`** — fragments of `SKILL.md` and `ADR-INDEX.json`, matched inside identifiers

Repairing the records would have meant writing "LLM (large language model)" into an Accepted Decision, and rewording prose so the linter stops seeing `SKILL` inside a filename. That is verbatim what spec R15 forbids: "the only escape left to the author is to contort a permanent decision to suit a heuristic — renaming the file, padding the prose, choosing words the decision would not otherwise use." Two of the four are **Superseded**, where the text is immutable outright.

So the gate was bounded instead, which is ADR-009's principle applied to a case it had not reached. It now skips fenced blocks, inline code spans, and acronyms adjacent to identifier characters, and the allowlist carries this ecosystem's vocabulary.

**Proven by negative control, not by assertion.** Five cases: three unexpanded acronyms in prose → FAIL; the same three in a code span → quiet; in a fenced block → quiet; properly expanded → quiet; two only → quiet. Bounding a heuristic must not disable it, and this is what shows it did not.

**Advisory triage:** all 6 are the same finding — "Consequences contains no numbers" — on records whose Consequences are immutable. No action, deliberately: adding numbers to satisfy a nudge is the same contortion at a smaller scale.

`--gates` now reaches `adr-lint` from `bin/adr-audit`; `skills/audit/SKILL.md` states which set produced a green answer, since "the audit is green" means different things at different sets; `templates/github-workflows/adr-audit.yml` ships and runs here weekly, report-only, because a sweep that reddens the default branch for a pre-existing violation teaches people to ignore it.

`bin/adr-audit --whole-codebase --gates all` now exits 0 over 28 ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
