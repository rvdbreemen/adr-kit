---
id: TASK-40.8
title: Ship the Level-4 generic ADR Kit portability bundle
status: To Do
assignee: []
created_date: '2026-07-19 17:52'
updated_date: '2026-07-19 19:03'
labels:
  - generic
  - portability
  - skills
  - agents-md
  - mcp
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.4
  - TASK-40.5
  - TASK-40.6
references:
  - 'https://agents.md/'
  - 'https://github.com/agentsmd/agents.md'
  - 'https://skills.md/docs'
modified_files:
  - skills/
  - prompts/
  - instructions/ADR-guide.md
  - clients/generic/
  - tests/fixtures/generic/
  - tests/test_generic_bundle.py
  - docs/clients/generic.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Package generic ADR Kit support without a custom client runtime adapter. The bundle includes portable Agent Skills, `AGENTS.md` guidance, generated `.adr-kit/ADR-guide.md` plus optional local guide, local MCP configuration intent, portable slash prompts/workflows, and only native hook configurations whose Claude/Codex/Copilot format works unchanged. Install it by default with opt-out and label it separately from first-class support.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The generic payload contains standard Agent Skills, portable prompt/workflow Markdown, AGENTS.md integration, generated/local guide behavior, and documented local MCP registration intent.
- [ ] #2 The generic payload contains no client-specific runtime adapter or duplicated ADR engine logic.
- [ ] #3 A hook is included only when one existing first-class native format, invocation, exit contract, and paths work unchanged; otherwise generic support explicitly omits hooks.
- [ ] #4 Setup detects generic eligibility, shows the planned artifacts, selects generic support by default, and offers global and per-project opt-out.
- [ ] #5 Install, upgrade, disable, and uninstall are idempotent and remove only ADR Kit-owned artifacts and markers.
- [ ] #6 Generic doctor reports artifact discovery and MCP/instruction readiness without calling the client first-class or natively certified.
- [ ] #7 Portable fixtures run on every release across Windows and best-effort macOS/Linux path, newline, permission, and executable-mode cases.
- [ ] #8 The bundle remains usable when no Claude, Codex, or Copilot executable is installed.
- [ ] #9 Documentation distinguishes portable guarantees, client-dependent discovery, unchanged-hook reuse, unsupported native lifecycle behavior, and troubleshooting.
- [ ] #10 No Kilo, Kimi, OpenCode, or other product-specific code is required to produce or install the bundle.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M. Assemble the bundle only from outputs of the canonical generator, settings/guide, installer, doctor, and reusable hook work. Prove standalone installation without a native first-class client. Treat discovery as evidence about portability, never as native support. Stop rather than add a client-specific bridge.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: scope correction
created: 2026-07-19 19:03
---
Transferred out of the current implementation scope by the maintainer on 2026-07-19. Generic portability is preserved in future TASK-43 and must be re-scoped when that epic is explicitly activated. TASK-40 now contains Claude, Codex, and Copilot only.
---
<!-- COMMENTS:END -->
