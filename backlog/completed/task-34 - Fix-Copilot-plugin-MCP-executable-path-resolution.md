---
id: TASK-34
title: Fix Copilot plugin MCP executable path resolution
status: Done
assignee:
  - Codex
created_date: '2026-07-19 07:18'
updated_date: '2026-07-19 07:39'
labels:
  - bug
  - copilot
  - mcp
  - installer
dependencies: []
documentation:
  - README.md
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
modified_files:
  - copilot/.mcp.json
  - scripts/install-agent-envs.py
  - tests/test_agent_installer.py
  - README.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Correct the GitHub Copilot CLI plugin MCP manifest so the bundled adr-mcp executable resolves from the installed plugin root while the server continues serving the active workspace. Add a regression test that exercises the manifest-derived launch from an unrelated working directory, update user-facing Copilot installation troubleshooting, and repair the currently installed plugin through the supported update path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The Copilot plugin MCP manifest resolves adr-mcp through Copilot's injected plugin-root environment instead of the active workspace.
- [x] #2 The MCP process still uses the active project as its default root and ADR directory.
- [x] #3 A regression test derives the launch command from copilot/.mcp.json, launches from an unrelated workspace, and completes initialize plus tools/list.
- [x] #4 Installer/packaging validation covers the portable Copilot plugin-root path without weakening Codex behavior.
- [x] #5 README or relevant installation documentation explains the corrected Copilot configuration and update/reload path.
- [x] #6 Focused installer, MCP, packaging, and documentation tests pass; a live Copilot MCP inspection confirms the repaired installed configuration.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Change only the Copilot MCP executable argument to `${PLUGIN_ROOT}/bin/adr-mcp`, retaining `cwd: "."` so the active workspace remains the server root; leave the Codex manifest unchanged unless testing proves it shares the defect.
2. Extend installer/packaging tests to load `copilot/.mcp.json`, expand the injected plugin root, launch from an unrelated temporary project, and complete the real MCP initialize/tools-list handshake.
3. Update the agent-friendly Copilot install/troubleshooting documentation with the supported update and reload commands.
4. Run focused MCP, installer, packaging, synchronization, and documentation tests, then run the broader suite proportionate to the shared packaging surface.
5. Update the locally installed Copilot plugin through its native marketplace/update flow and verify `copilot mcp get adr-kit --json` plus a live MCP handshake from LLmWiki-KennisBank.
6. Record evidence, check every acceptance criterion, write the final summary, and mark TASK-34 Done.

Live installation adjustment: `copilot plugin marketplace update` succeeded, but `copilot plugin update adr-kit` returned Windows `Access is denied` because an active Copilot CLI session and old `adr-mcp` children hold the installed plugin cache. Do not terminate the user's session. Apply the same minimal `${PLUGIN_ROOT}/bin/adr-mcp` correction to the installed manifest, verify it with `copilot mcp get adr-kit --json` from LLmWiki-KennisBank, and document that the normal full plugin update should be rerun after the active session exits.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented `${PLUGIN_ROOT}/bin/adr-mcp` in the Copilot MCP manifest while retaining `cwd: "."`. Installer validation now loads each client manifest, expands Copilot's injected plugin root, launches from an unrelated project, checks the actual served root in stderr, and completes initialize plus tools/list without changing the Codex manifest contract. Verification: focused installer/MCP/documentation/packaging slice 57 passed, 1 skipped; full ADR Kit suite 641 passed, 4 skipped; plugin synchronization, Python compilation, and git diff checks passed. Live evidence from LLmWiki-KennisBank: marketplace refresh succeeded; the installed manifest was safely hotfixed because `copilot plugin update adr-kit` was blocked by a Windows file lock from the active Copilot session; `copilot mcp get adr-kit --json` now reports `${PLUGIN_ROOT}/bin/adr-mcp`; a real initialize/tools-list handshake exposed all four ADR tools and stderr confirmed the server root was LLmWiki-KennisBank. The installed cache still reports plugin version 0.33.0; rerun the documented normal plugin update after closing/restarting the active Copilot session to install the full newer package.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed GitHub Copilot's ADR Kit MCP launch path so the bundled server resolves from the installed plugin root while ADR operations remain rooted in the active workspace. Added manifest-derived cross-workspace handshake coverage and root verification, preserved Codex behavior, and documented agent-friendly update/reload recovery. All focused and full ADR Kit tests pass. The currently installed Copilot manifest is repaired and live-verified; a full package refresh remains a documented post-session step because Windows locked the active plugin cache.
<!-- SECTION:FINAL_SUMMARY:END -->
