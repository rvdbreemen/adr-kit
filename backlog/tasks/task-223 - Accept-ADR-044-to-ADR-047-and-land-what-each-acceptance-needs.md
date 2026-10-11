---
id: TASK-223
title: Accept ADR-044 to ADR-047 and land what each acceptance needs
status: Done
assignee: []
created_date: '2026-10-11 15:17'
updated_date: '2026-10-11 15:40'
labels: []
dependencies:
  - TASK-222
references:
  - >-
    docs/adr/ADR-044-resolve-the-interpreter-and-the-engine-through-one-resolver-at-every-entry-point.md
  - >-
    docs/adr/ADR-045-let-the-judge-acquire-its-own-diff-and-give-every-diff-shape-an-explicit-verdict.md
  - >-
    docs/adr/ADR-046-match-every-path-glob-in-the-judge-s-dialect-wherever-it-is-read.md
  - >-
    docs/adr/ADR-047-cap-supporting-adrs-per-response-and-let-them-fill-only-the-slots-left-under-the-limit.md
  - templates/cc-settings/guardian-hook-entry.json
ordinal: 67000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On 2026-10-11 User: Robert van den Breemen explicitly confirmed, one record at a time, that ADR-044, ADR-045, ADR-046 and ADR-047 are to be accepted now, with ADR-044 accepted together with the skills part of its implementation. Acceptance turns ADR-044's Enforcement block on, and a dry run showed adr-audit --whole-codebase then fails with 32 violations: 16 resolver lines in 10 skills/*/SKILL.md use the Claude plugin-cache path with GNU sort -V (DEF-21). ADR-047 promises two tests and says ADR-014's status line will read 'Amended by ADR-047', which the tooling does not do; the precedent (ADR-007) records an amendment in the amended record's status history. Claude Code 2.1.296 substitutes ${CLAUDE_PLUGIN_ROOT} with the plugin root in a plugin skill's content (function lce, called with pluginPath), so the skills can resolve the root from the installed skill. install-hooks carries an inline copy of the guardian SessionStart entry that still uses sort -V and lacks the _wrapper_version stamp; templates/cc-settings/guardian-hook-entry.json is the portable, stamped original.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR-047 amends ADR-036, not the superseded ADR-014, and the two tests it promises exist and pass
- [x] #2 No skills/**/SKILL.md contains a client plugin-cache path or sort -V; each resolves the plugin root from the installed skill and, except the guardian's checkout fallback, stops with one line when the root stays empty; tests assert both
- [x] #3 install-hooks appends the shipped guardian entry template instead of an inline copy
- [x] #4 ADR-044, ADR-045, ADR-046 and ADR-047 are Accepted with bin/adr accept --confirm, signed by User: Robert van den Breemen
- [x] #5 The links the records declare are written with bin/adr relate on both sides, and no superseded record gains a history entry
- [x] #6 adr-audit --whole-codebase reports no violation, and the full suite passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, done on branch adr/accept-defect-sweep-records.
- Each record was put to User: Robert van den Breemen through an interactive question with a briefing, a dry run in a scratch clone, and the signer named. He chose: ADR-045, ADR-046 and ADR-047 now; ADR-044 now together with its skills part.
- While accepting, relate wrote status: Superseded into ADR-014's history. ADR-014 is Superseded (ADR-018 on 2026-08-01, then ADR-020, then ADR-036), so the cap had no Accepted record. The uncommitted lifecycle changes were discarded, and the maintainer chose that ADR-047 amends ADR-036 (its new Open Question 2, answered with bin/adr answer). ADR-046's three ADR-014 references were corrected, and it links to ADR-036. No other cited record is non-Accepted.
- Skills: 16 old resolver lines in 10 skills are replaced by the plugin root Claude Code substitutes for CLAUDE_PLUGIN_ROOT in skill content. This was observed in the 2.1.296 client (lce, called with pluginPath) and is documented in the plugin manifest reference. Every resolver except the guardian's is followed by an empty-root check that names Claude Code and the plugin. install-hooks installs templates/cc-settings/guardian-hook-entry.json instead of its drifted inline copy.
- Tests: two in tests/test_adr_query.py; tests/test_skill_resolver.py with a bash behaviour test of the real snippet. Each was mutation-checked against the defect it guards.
- Evidence: adr-audit --whole-codebase OK (32 violations on the dry run without the skills fix); judge on the staged diff 0 violations; lint and strict lint, index check, probes 3/3 and adapters changed=0 all pass; full serial suite green.
- Residual risk: a client that does not substitute the reference. The check turns that into a one-line stop.
<!-- SECTION:NOTES:END -->
