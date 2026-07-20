---
id: TASK-40.9
title: Validate generic support in OpenCode and document Kilo/Kimi compatibility
status: To Do
assignee: []
created_date: '2026-07-19 17:52'
updated_date: '2026-07-19 19:03'
labels:
  - opencode
  - generic
  - compatibility
  - discovery
dependencies:
  - TASK-40.7.1
  - TASK-40.7.2
  - TASK-40.7.3
references:
  - 'https://opencode.ai/docs/plugins/'
  - 'https://kilo.ai/docs/automate/extending/plugins'
  - 'https://www.kimi.com/code/docs/en/'
modified_files:
  - tests/fixtures/opencode/
  - tests/test_opencode_generic_discovery.py
  - docs/clients/opencode.md
  - docs/client-support.md
parent_task_id: TASK-40
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use OpenCode as the lightweight periodically tested reference for the generic portability architecture after the three native clients are normalized. Verify discovery of the generic bundle without an OpenCode adapter. Document Kilo Code CLI and Kimi Code as untested best-effort generic compatibility. Do not implement a TypeScript bridge, native hooks, native installer mutations, Kilo VS Code support, or native certification.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A lightweight OpenCode smoke discovers the portable skill, AGENTS.md guidance, prompt/workflow artifact where supported, and local MCP configuration through documented generic paths.
- [ ] #2 The smoke uses no custom OpenCode plugin or TypeScript runtime bridge and records any generic feature that OpenCode cannot discover.
- [ ] #3 OpenCode generic discovery runs at least quarterly and whenever generic discovery paths or packaging change; it does not block an ordinary release unless it exposes a portable-bundle defect.
- [ ] #4 Doctor and support documentation classify OpenCode as tested generic support with the evidence date, never first-class native support.
- [ ] #5 Kilo Code CLI and Kimi Code are listed as untested best-effort generic compatibility with no implied smoke, native lifecycle, hook, or support commitment.
- [ ] #6 Kilo VS Code is explicitly deferred and inherits no Kilo CLI compatibility claim.
- [ ] #7 No product-specific installer config mutation is added for OpenCode, Kilo, or Kimi beyond neutral generic paths explicitly selected by the user.
- [ ] #8 A generic client contract change produces an actionable compatibility report rather than silently adding adapter scope.
- [ ] #9 Documentation explains how users can opt out, manually register MCP when neutral automatic registration is unavailable, and report compatibility evidence.
- [ ] #10 The task stops at generic validation; any proposed native adapter requires a new user-approved task and maintenance-budget decision.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size S/M. After TASK-40.8 and native normalization, run one bounded OpenCode discovery smoke against the installed generic bundle and capture supported/missing surfaces. Add support-matrix wording for OpenCode, Kilo CLI, Kimi, and deferred Kilo VS Code. Do not write client adapters. Stop once generic discovery and honest documentation are proven.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: scope correction
created: 2026-07-19 19:03
---
Transferred out of the current implementation scope by the maintainer on 2026-07-19. OpenCode, Kilo, and Kimi work is preserved in future TASK-43 and requires fresh contract and priority review on activation. It is not part of TASK-40.
---
<!-- COMMENTS:END -->
