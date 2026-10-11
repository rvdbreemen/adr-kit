---
id: TASK-226
title: The commit floor finds the engine wherever a client installed it
status: Done
assignee: []
created_date: '2026-10-11 16:27'
updated_date: '2026-10-11 16:29'
labels: []
dependencies: []
references:
  - templates/githooks/pre-commit
ordinal: 70000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
templates/githooks/pre-commit:96-163 looks for the engine in the Claude and Codex plugin caches, Copilot's installed-plugins and an ADR Kit checkout. Two installs fall outside it, and the hook then exits 0, so a violating commit lands. Copilot CLI 1.0.81 and later loads a directory marketplace live from the installer's payload (${XDG_DATA_HOME:-~/.local/share}/adr-kit/marketplaces/<version>/copilot) and no longer copies it to installed-plugins (DEF-29, observed with 1.0.95). OpenCode installs the kit as the @rvdbreemen/adr-kit-opencode npm package (DEF-30, observed with 1.19.0). ADR-044's candidate set also starts with ADR_KIT_ROOT. The setup-recorded root and the refusal when nothing resolves remain WP-6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR_KIT_ROOT, the installer payloads (including the Copilot live directory, honouring XDG_DATA_HOME), the project's node_modules package and OpenCode's cache package are candidates
- [x] #2 Every candidate still competes on manifest version
- [x] #3 The not-found message names ADR_KIT_ROOT and the clients it looked for
- [x] #4 Tests run the real hook against each location and refuse a violating commit
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first: with the old hook, 6 of the tests in tests/test_pre_commit_engine_roots.py failed, because the violating commit landed or the message did not name ADR_KIT_ROOT.

The OpenCode cache layout was observed with OpenCode 1.19.0: $XDG_CACHE_HOME/opencode/packages/@rvdbreemen/adr-kit-opencode@<spec>/node_modules/@rvdbreemen/adr-kit-opencode, one directory per spec. A project-local npm install lands in <project>/node_modules/@rvdbreemen/adr-kit-opencode. The Copilot live directory comes from the agent run with Copilot 1.0.95 (PLUGIN_ROOT=.../marketplaces/0.59.1/copilot).

The hook now adds ADR_KIT_ROOT, the installer payloads (marketplaces/*/copilot, */codex and the payload root, honouring XDG_DATA_HOME) and both OpenCode locations. The version ranking is unchanged. All 8 tests pass, and the shared helper is tests/_precommit_project.py. Still WP-6: the setup-recorded root (it needs a machine-only config key and an ignore guard), and refusing when nothing resolves (ADR-044 Open Question 1).
<!-- SECTION:NOTES:END -->
