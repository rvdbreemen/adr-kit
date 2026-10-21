---
id: TASK-239
title: Add native OMP (oh-my-pi) client support
status: Done
assignee: []
created_date: '2026-10-21T18:48:00Z'
updated_date: '2026-10-21T20:05:00Z'
labels:
  - omp
  - client
  - typescript
  - hooks
dependencies: []
references:
  - docs/clients/omp.md
  - https://github.com/can1357/oh-my-pi
modified_files:
  - omp/extension.ts
  - package.json
  - bin/adr_llm.py
  - bin/adr-settings
  - tests/test_omp_extension.py
  - docs/clients/omp.md
  - >-
    docs/adr/ADR-050-certify-omp-as-a-fourth-native-client-through-a-thin-extension.md
  - README.md
priority: high
ordinal: 81000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
OMP installs the Claude Code plugin through its Claude-compatible marketplace (docs/clients/omp.md), but only MCP, skills and the adr-generator agent work there. OMP runs only TypeScript/JavaScript hook factories, so hooks/hooks.json never fires: no session/prompt/edit/compaction context, no pull-request guard, no judge host recorded. OMP also neither substitutes ${CLAUDE_PLUGIN_ROOT} in skill bodies nor exports it, so ten skills stop with 'plugin root not found' unless ADR_KIT_ROOT is set by hand. Add a thin OMP extension, declared through package.json omp.extensions so a marketplace install loads it, that exports ADR_KIT_ROOT to the shell and maps OMP lifecycle events onto the shared Python hook core, plus omp-cli as an LLM host. Supersedes the canceled TASK-40.12 scope decision for OMP only, recorded in an ADR, following the ADR-039 OpenCode precedent.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records adding a native OMP extension without expanding the certified three-client gate
- [x] #2 A marketplace install of adr-kit in OMP loads the extension with no manual configuration
- [x] #3 Skills resolve the ADR Kit root under OMP without ADR_KIT_ROOT being set by the user
- [x] #4 OMP session, prompt, pre/post edit, shell PR moment, subagent and compaction events reach hooks/adr-hook.py and their context reaches the model; the hooks fail open
- [x] #5 omp-cli is a judge host client and the first OMP session records it when none is recorded
- [x] #6 The extension contains no ADR domain logic; every ADR operation delegates to the Python engines
- [x] #7 Tests cover the event mapping and host registration; a real omp session smoke proves context injection
- [x] #8 docs/clients/omp.md, INSTALL.md, INSTALL-AGENT.md, README and CHANGELOG describe native OMP support and its boundary
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced both gaps on OMP 18.12.5 before the change: an OMP session in a docs/adr project never wrote .adr-kit.local.json (SessionStart did not fire; running the hook by hand did), and ${CLAUDE_PLUGIN_ROOT} and ADR_KIT_ROOT were both empty in OMP's shell. OMP loads package.json omp.extensions for marketplace installs (pi-coding-agent plugins/installer.ts: manifest = pkg.omp). omp -p reads the prompt on stdin with clean stdout; --no-extensions verifiably keeps the extension out of a judging call (without it the call wrote .adr-kit.local.json). OMP delivers tool_call additionalContext after the tool batch, so pre-edit context arrives after the edit (recorded in ADR-050). The hook drops input over 64 KiB, so the extension forwards only edit paths, never file content.

2026-10-21: ADR-050 grilled with the maintainer and Accepted as full certification (amends ADR-010's client list); certification work split into TASK-240 for v0.62.0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added omp/extension.ts (declared in package.json omp.extensions): exports ADR_KIT_ROOT, maps session_start/before_agent_start/tool_call/tool_result/session.compacting onto hooks/adr-hook.py (session, prompt, edit, post-edit, PR guard, subagent, compaction), fail-open except the guard's explicit deny, ADR_KIT_HOST_CLIENT=omp-cli. Added omp-cli host (omp -p --no-extensions --no-session --no-tools) to HOST_COMMANDS and the adr-settings enum; regenerated codex/copilot. ADR-050 (Proposed, awaiting human acceptance) records the decision, related to ADR-039 and ADR-049. Docs: README Supported clients table (certified / native not certified / portable), docs/clients/omp.md, INSTALL.md, INSTALL-AGENT.md, docs/README.md, C4 context/container, CHANGELOG. Verification: tests/test_omp_extension.py (9 Bun-harness tests); real OMP marketplace install from the checkout showed prompt and edit context reaching the model, ADR_KIT_ROOT set in the shell, and omp-cli recorded; omp-cli host answered through SubprocessBackend; adr-lint --strict, adr-index --check, build-client-adapters --check (changed=0) and adr-judge clean; full suite 2131 passed, 1 environment-dependent failure in tests/test_pre_commit_portability.py (bash probe; passes/skips when run alone, template untouched).
<!-- SECTION:FINAL_SUMMARY:END -->
