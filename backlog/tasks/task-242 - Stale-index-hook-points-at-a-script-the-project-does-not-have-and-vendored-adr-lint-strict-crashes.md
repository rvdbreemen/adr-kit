---
id: TASK-242
title: >-
  Stale-index hook points at a script the project does not have, and vendored
  adr-lint --strict crashes
status: To Do
assignee: []
created_date: '2026-10-24T17:06:00Z'
labels: []
dependencies: []
priority: medium
ordinal: 84000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found in OTGW-firmware 2026-10-24 (TASK-1355), adr-kit plugin 0.59.1.
1. hooks/adr_hook_core.py:494 tells the agent 'Run `bin/adr-index docs/adr` to regenerate it' when ADR-INDEX.json is stale. OTGW-firmware's bin/ has no adr-index (only adr-audit, adr-context, adr-generate-scripts, adr-judge, adr-lint, adr-quality, adr-retire, adr-status); it exists only in the plugin (bin/adr-index). The hook repeats on every tool call while the index is stale, and the advice cannot be followed as written. Fix idea: resolve the command the same way the plugin runs it (plugin path or 'adr index'), or have bin/adr-generate-scripts install adr-index into projects, and name what actually exists.
2. OTGW-firmware's vendored bin/adr-lint --strict docs/adr crashes: 'File bin/adr-lint, line 191, in severity_of: AttributeError: NoneType object has no attribute group' (a regex match that returned None). The plugin's own bin/adr-lint 0.59.1 --strict runs without the crash on the same ADR set, so the vendored copy is stale. Fix ideas: severity_of must not assume the match succeeds; and projects need a visible way to see that vendored scripts lag the plugin (version stamp + a warning, or adr-generate-scripts --check).
Repro: OTGW-firmware dev @057535397, 199 ADRs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The stale-index message names a command that exists in a project set up by adr-kit (test with a project without bin/adr-index)
- [ ] #2 severity_of handles a missing match without crashing (unit test with the failing input)
- [ ] #3 A vendored script older than the plugin is reported (version stamp or --check)
<!-- AC:END -->
