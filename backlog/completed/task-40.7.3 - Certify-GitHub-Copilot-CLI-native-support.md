---
id: TASK-40.7.3
title: Certify GitHub Copilot CLI native support
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-19 18:52'
updated_date: '2026-07-19 22:49'
labels:
  - copilot
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
  - >-
    https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating
  - >-
    https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks
documentation:
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/research/cross-client-plugin-hooks-report.md
modified_files:
  - copilot/plugin.json
  - copilot/.mcp.json
  - copilot/hooks.json
  - copilot/hooks/
  - copilot/skills/
  - clients/capabilities.json
  - tests/fixtures/copilot/
  - tests/certification/copilot/
  - tests/test_native_client_packages.py
  - docs/clients/copilot.md
parent_task_id: TASK-40.7
priority: high
ordinal: 7300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Normalize and prove GitHub Copilot CLI independently against the ADR Kit first-class outcome and release contracts. Windows native evidence is required for every release; macOS/Linux are attempted best-effort and may be recorded as not run with a reason. This task owns Copilot plugin packaging, platform-specific hook commands, event/output limitations, fixtures, native smoke, and client documentation, but not shared ADR semantics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Copilot CLI installs, lists, enables, updates, rolls back, disables/removes, and reinstalls ADR Kit through the supported native plugin lifecycle without changing unrelated plugins or config.
- [x] #2 All documented ADR Kit skills, slash commands/prompts, Copilot instructions, and MCP tools are discoverable and invoke canonical workflows under stable names or approved aliases.
- [x] #3 Supported session/task/edit events provide bounded outcomes with separate Windows PowerShell and POSIX command forms where the native contract requires them.
- [x] #4 Copilot PreToolUse limitations are represented honestly: ADR Kit does not fake context injection or deny/retry edits; proactive session/task context, PostToolUse, and pre-commit provide the documented outcome.
- [x] #5 Every hook failure, malformed input, missing payload, timeout, and disabled state fails open while deterministic pre-commit remains available.
- [x] #6 Fast/deep doctor distinguishes missing, healthy, repaired, disabled, stale, broken platform command, broken hook, broken MCP, version skew, and rollback state.
- [x] #7 Verified stable update and failed-update rollback preserve previous healthy payload, instruction bytes outside markers, local guide, and unrelated Copilot configuration.
- [x] #8 Certification records official contract date/version, Copilot/ADR Kit versions and hashes, Windows environment, required outcomes, latency, fixture/native logs, and documented degradations.
- [x] #9 Windows native smoke passes on the release-supported Copilot CLI version; macOS/Linux best-effort results and limitations are recorded separately.
- [x] #10 Second install/update is a no-op; uninstall/reinstall leaves no orphaned ADR Kit-owned plugin, hook, command, MCP, or instruction state.
- [x] #11 Copilot documentation covers setup, platform commands, PreToolUse degradation, settings, doctor/repair, update/rollback, migration, and removal; support claims derive from evidence.
- [x] #12 The full ADR Kit regression and portable fixture suites pass with Copilot certification enabled.
- [x] #13 Copilot artifacts are natively optimized: root plugin.json declares skills, hooks.json, and .mcp.json; skill descriptions use Copilot discovery terms without Codex/Claude syntax; hook events use Copilot lower-camel casing with explicit bash and PowerShell commands; and unsupported prompt/command claims are omitted.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M/L. Prove native plugin and workflow/MCP discovery first, then Windows/POSIX hook command fixtures and the honest PreToolUse degradation, then doctor and lifecycle rollback/removal. Record reproducible Windows native evidence. Stop and return shared wrapper, installer, or doctor defects to their owning task; do not implement deny/retry context injection.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Official GitHub Copilot CLI docs rechecked 2026-07-19. Native plugin structure uses root plugin.json plus skills/, hooks.json, and .mcp.json. Manifest fields accept string or array paths. Hook event keys are lower camel case (sessionStart, sessionEnd, userPromptSubmitted, preToolUse, postToolUse, errorOccurred); cross-platform command hooks should provide both bash and powershell forms. Certification must verify /skills list discovery and avoid Codex $ syntax, Claude namespacing, or unsupported prompt claims.

Implemented the native Copilot package and ran isolated Windows lifecycle certification with GitHub Copilot CLI 1.0.71. The installed version documented enable/disable but did not expose those subcommands; settings opt-out plus uninstall/reinstall is retained as the explicit degradation. Native hooks use lower-camel events and separate bash/PowerShell commands.

Final verification: prepared payload SHA-256 70b3d62d88e0a8a61a070033bdab60e8381bbba61bcbca33c425a1dc1264eb2f; client-focused slice 103 passed; whole repository 740 passed, 6 skipped. macOS/Linux are explicitly not run because no runners were available.

Superseding artifact identity after final atomic-write hardening: prepared payload SHA-256 e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and independently certified the GitHub Copilot CLI package on Windows. The native package declares root skills, hooks.json, and MCP; skills use Copilot /skills discovery, while hooks use supported lower-camel events with explicit bash and PowerShell commands. Copilot's missing PreToolUse context injection is handled honestly through proactive task context, PostToolUse, and pre-commit rather than deny/retry. Isolated Copilot CLI 1.0.71 smoke covered marketplace add, install/list/update no-op, uninstall/reinstall, skill discovery, hook fail-open behavior, and MCP initialization. The unavailable enable/disable subcommands are documented with settings opt-out and uninstall/reinstall backstops. Evidence is payload-bound but not release-promoted until a clean candidate commit exists. Verification: 103 focused tests and 740 repository tests passed; 6 commit/platform-dependent tests skipped.

Final prepared-payload SHA-256 after atomic generator hardening: `e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51`.
<!-- SECTION:FINAL_SUMMARY:END -->
