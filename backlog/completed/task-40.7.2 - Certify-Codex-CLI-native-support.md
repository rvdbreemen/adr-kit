---
id: TASK-40.7.2
title: Certify Codex CLI native support
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-19 18:51'
updated_date: '2026-07-19 22:49'
labels:
  - codex
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
  - 'https://learn.chatgpt.com/docs/hooks'
  - 'https://developers.openai.com/learn/developers-codex-plugin'
documentation:
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/research/cross-client-plugin-hooks-report.md
  - >-
    docs/adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md
modified_files:
  - codex/.codex-plugin/plugin.json
  - codex/.mcp.json
  - codex/hooks/
  - codex/skills/
  - clients/capabilities.json
  - tests/fixtures/codex/
  - tests/certification/codex/
  - tests/test_native_client_packages.py
  - docs/clients/codex.md
parent_task_id: TASK-40.7
priority: high
ordinal: 7200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Normalize and prove Codex CLI independently against the ADR Kit first-class outcome and release contracts. Windows native evidence is required for every release; macOS/Linux are attempted best-effort and may be recorded as not run with a reason. This task owns Codex plugin packaging, hook review/trust behavior, native event mappings, stale version-ranked cache and launcher cases, fixtures, smoke evidence, and client documentation, but not shared ADR semantics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Codex CLI installs, lists, enables, updates, rolls back, disables/removes, and reinstalls ADR Kit through the supported native lifecycle without changing unrelated plugins or config.
- [x] #2 All documented ADR Kit skills, prompts/commands, managed AGENTS.md guidance, and MCP tools are discoverable and invoke canonical workflows under stable names or approved aliases.
- [x] #3 Supported SessionStart, UserPromptSubmit, SubagentStart, PreToolUse, PostToolUse, and useful compact behavior produce bounded outcomes; unsupported lifecycle events are successful no-ops.
- [x] #4 Changed hook definitions and plugin state expose review/trust requirements accurately; ADR Kit never bypasses Codex approval boundaries.
- [x] #5 Every hook failure, malformed input, missing payload, timeout, and disabled state fails open while deterministic pre-commit remains available.
- [x] #6 Fast/deep doctor resolves actual launcher/interpreter targets and distinguishes current healthy state from a current manifest pointing at a removed older cache.
- [x] #7 The real 0.35.0-to-removed-0.34.0 stale launcher class is a deterministic regression fixture with exact repair and rollback evidence.
- [x] #8 Verified stable update and failed-update rollback preserve previous healthy payload, user AGENTS.md bytes outside markers, local guide, and unrelated Codex config.
- [x] #9 Certification records official contract date/version, Codex/ADR Kit versions and hashes, Windows environment, required outcomes, latency, fixture/native logs, trust state, and degradations.
- [x] #10 Windows native smoke passes on the release-supported Codex version; macOS/Linux best-effort results and limitations are recorded separately.
- [x] #11 Second install/update is a no-op; uninstall/reinstall leaves no orphaned ADR Kit-owned cache, launcher, hook, MCP, or plugin registration.
- [x] #12 Codex documentation covers setup, trust/review, hooks, settings, doctor/repair, update/rollback, migration, stale cache recovery, and removal; support claims derive from evidence.
- [x] #13 The full ADR Kit regression and portable fixture suites pass with Codex certification enabled.
- [x] #14 Codex artifacts are natively optimized: root skills/ and hooks/hooks.json are referenced by the Codex manifest, descriptions front-load natural trigger terms within the progressive-disclosure budget, explicit invocation uses the Codex $skill surface, AGENTS.md remains concise, and deprecated local custom prompts are not advertised as plugin-distributed commands.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M/L. Begin with the real stale launcher/cache regression on Windows and prove that install and doctor resolve the same active target. Then certify workflow/MCP discovery, hook review/trust and event outcomes, update/rollback, and removal. Record reproducible evidence under the early schema. Stop and return common root-selection or installer defects to their owning shared task instead of patching around them in Codex-only code.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Current Codex manual fetched 2026-07-19. Native requirements: only plugin.json under .codex-plugin/; skills/, hooks/, .mcp.json at plugin root; manifest should reference ./skills/, ./hooks/hooks.json, and ./.mcp.json; skill descriptions front-load triggers because Codex initially loads only name/description/path under a bounded catalog; explicit invocation is via $ skill mention; custom prompts are deprecated and local-only, so generated prompt prose may support testing/installer compatibility but must not be claimed as a distributable native plugin surface. Codex hook trust/review must remain visible.

Implemented the native Codex package and ran isolated Windows lifecycle certification with Codex CLI 0.144.6. The current CLI exposes add/list/remove rather than dedicated update/disable commands, so verified remove/add plus ADR Kit settings opt-out is recorded as the honest supported lifecycle; hook review/trust is never bypassed.

Final verification: prepared payload SHA-256 70b3d62d88e0a8a61a070033bdab60e8381bbba61bcbca33c425a1dc1264eb2f; client-focused slice 103 passed; whole repository 740 passed, 6 skipped. macOS/Linux are explicitly not run because no runners were available.

Superseding artifact identity after final atomic-write hardening: prepared payload SHA-256 e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and independently certified the Codex CLI package on Windows. The manifest references native root skills, hooks/hooks.json, and MCP; generated skills use the Codex $skill surface without cross-client or deprecated prompt claims. Isolated Codex 0.144.6 smoke covered marketplace/plugin add, list, remove/re-add, hook fail-open behavior, MCP discovery, and visible trust boundaries. Because this CLI version exposes add/list/remove rather than dedicated update/disable commands, verified remove/add and settings opt-out are documented as the supported lifecycle degradation. Stale removed-cache behavior remains a deterministic doctor/repair fixture. Evidence is payload-bound but not release-promoted until a clean candidate commit exists. Verification: 103 focused tests and 740 repository tests passed; 6 commit/platform-dependent tests skipped.

Final prepared-payload SHA-256 after atomic generator hardening: `e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51`.
<!-- SECTION:FINAL_SUMMARY:END -->
