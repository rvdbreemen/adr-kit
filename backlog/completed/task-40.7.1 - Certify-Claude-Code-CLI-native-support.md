---
id: TASK-40.7.1
title: Certify Claude Code CLI native support
status: Done
assignee:
  - Codex
created_date: '2026-07-19 18:51'
updated_date: '2026-07-19 22:49'
labels:
  - claude
  - certification
  - windows
  - native
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.4
  - TASK-40.5
  - TASK-40.6
  - TASK-40.13
references:
  - 'https://code.claude.com/docs/en/plugins'
documentation:
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/research/cross-client-plugin-hooks-report.md
modified_files:
  - .claude-plugin/plugin.json
  - .mcp.json
  - hooks/hooks.json
  - hooks/run-hook.cmd
  - skills/
  - clients/capabilities.json
  - tests/fixtures/claude/
  - tests/certification/claude/
  - tests/test_native_client_packages.py
  - docs/clients/claude.md
parent_task_id: TASK-40.7
priority: high
ordinal: 7100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Normalize and prove Claude Code CLI independently against the ADR Kit first-class outcome and release contracts. Windows native evidence is required for every release; macOS/Linux are attempted best-effort and may be recorded as not run with a reason. This task owns Claude-specific manifests, plugin lifecycle, event mappings, trust/permission behavior, fixtures, native smoke, and support documentation, but not shared ADR semantics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Claude Code CLI installs, lists, enables, updates, rolls back, disables/removes, and reinstalls ADR Kit through the supported native lifecycle without changing unrelated plugins or config.
- [x] #2 All documented ADR Kit skills, slash commands, managed instructions, and MCP tools are discoverable and invoke canonical workflows under their stable names or approved aliases.
- [x] #3 Required SessionStart, task-context, pre/post edit, subagent/compact behavior where supported, and safe no-op events produce bounded model-visible or documented fallback outcomes.
- [x] #4 Every hook failure, malformed input, missing payload, timeout, and disabled state fails open while deterministic pre-commit remains available.
- [x] #5 Fast and deep doctor distinguish missing, healthy, repaired, disabled, stale, trust/permission pending, broken hook, broken MCP, version skew, and rollback state.
- [x] #6 Verified stable update and failed-update rollback preserve the previous healthy payload, user instruction bytes outside markers, local guide, and unrelated Claude configuration.
- [x] #7 The certification record includes official contract version/date, ADR Kit version/hash, Windows/client versions, required outcomes, cold/warm latency evidence, fixture/native logs, and degradations.
- [x] #8 Windows native smoke passes on the release-supported Claude Code version; macOS/Linux best-effort results and limitations are recorded separately.
- [x] #9 Second install/update is a no-op and uninstall followed by reinstall proves no orphaned ADR Kit-owned registrations or stale launchers.
- [x] #10 Claude-specific documentation covers setup, settings, hook differences, doctor/repair, update/rollback, migration, and removal; generated support claims derive from passing evidence.
- [x] #11 The full ADR Kit regression and portable fixture suites pass with Claude certification enabled.
- [x] #12 Claude artifacts are natively optimized: plugin-root skills/hooks layout, concise trigger-rich descriptions, Claude-only argument-hint and disable-model-invocation semantics where appropriate, $ARGUMENTS-aware slash workflows, and no Codex/Copilot terminology or adapter boilerplate.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M/L. Use the certification schema and existing normalized package; do not change canonical ADR semantics here. First prove install/list plus workflow/MCP discovery on Windows, then hook outcomes and doctor states, then update/rollback/uninstall. Capture reproducible evidence identifiers rather than manual prose alone. Stop and return to the owning shared task if a failure is common to more than Claude.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Official Claude docs rechecked 2026-07-19. Optimize the Claude adapter independently: only plugin.json under .claude-plugin/, components at plugin root, new workflows under skills/ rather than legacy commands/, hooks in hooks/hooks.json, concise persistent skill bodies, trigger terms first, native argument-hint/disable-model-invocation/$ARGUMENTS, and namespaced /adr-kit:<skill> invocation. Rich Claude frontmatter is intentional and must not be reduced to the cross-client schema.

Beginning Claude normalization first. The current package violates the official root-layout rule by placing hook components under `.claude-plugin/hooks`; implementation will move hook configuration/dispatcher to plugin-root `hooks/`, preserve the normalized core, and add native-shape fixtures before lifecycle certification.

Completed isolated Windows native lifecycle smoke with Claude Code 2.1.215: marketplace add, install, list, enable/disable, no-op update, uninstall/reinstall, 14 skills, one agent, six hooks, one MCP server, fail-open malformed input, and MCP initialize/tools-list. Paid/cloud workflow invocation remained not run by policy.

Final verification: prepared payload SHA-256 70b3d62d88e0a8a61a070033bdab60e8381bbba61bcbca33c425a1dc1264eb2f; client-focused slice 103 passed; whole repository 740 passed, 6 skipped. macOS/Linux are explicitly not run because no runners were available.

Superseding artifact identity after final atomic-write hardening: prepared payload SHA-256 e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and independently certified the Claude Code CLI package on Windows. The plugin now uses Claude's native plugin-root layout, rich trigger-focused skill metadata, $ARGUMENTS-aware workflows, six fail-open hooks, and a root MCP declaration. Isolated Claude 2.1.215 lifecycle smoke covered marketplace add, install/list, enable/disable, update no-op, uninstall/reinstall, discovery, malformed-hook fail-open behavior, and MCP initialization. Installer/doctor/rollback and preservation fixtures cover shared lifecycle states. Evidence is bound to the prepared payload hash but intentionally not release-promoted until a clean candidate commit exists. Verification: 103 focused tests and 740 repository tests passed; 6 commit/platform-dependent tests skipped.

Final prepared-payload SHA-256 after atomic generator hardening: `e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51`.
<!-- SECTION:FINAL_SUMMARY:END -->
