---
id: TASK-174
title: Add generic OpenCode support through portable ADR Kit surfaces
status: In Progress
assignee: []
created_date: '2026-08-13 22:14'
updated_date: '2026-08-16 21:31'
labels:
  - opencode
  - generic
  - compatibility
  - discovery
dependencies: []
references:
  - 'https://opencode.ai/docs/skills/'
  - 'https://opencode.ai/docs/rules/'
  - 'https://opencode.ai/docs/mcp-servers/'
  - 'https://opencode.ai/docs/plugins/'
  - >-
    backlog/archive/tasks/task-40.9 -
    Build-and-certify-the-shared-Kilo-Code-and-OpenCode-adapter-family.md
documentation:
  - docs/clients/opencode.md
modified_files:
  - clients/generic/
  - tests/fixtures/opencode/
  - tests/test_opencode_generic_discovery.py
  - docs/clients/opencode.md
  - docs/client-support.md
  - README.md
  - INSTALL.md
  - AGENTS.md
priority: medium
type: enhancement
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide tested generic compatibility for OpenCode without adding a native TypeScript plugin, installer mutation, or native hook adapter. Reuse ADR Kit's existing portable skills, project AGENTS.md guidance, and stdio MCP server through OpenCode's documented discovery paths. Document unsupported native lifecycle, doctor, update, and certification claims honestly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 OpenCode can discover ADR Kit workflows from a documented generic skill path with valid OpenCode frontmatter.
- [ ] #2 OpenCode receives ADR Kit project guidance through AGENTS.md without replacing user-owned content.
- [ ] #3 OpenCode can use the local adr-kit MCP server through documented opencode.json configuration without a product-specific runtime bridge.
- [ ] #4 Focused discovery tests validate supported and unsupported surfaces and do not add OpenCode to the three-client native registry or release gate.
- [ ] #5 Documentation explains setup, opt-out/manual MCP registration, evidence scope, and the boundary between generic compatibility and native support.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: OpenCode
created: 2026-08-16 20:07
---
Investigation 2026-08-16: the reported OpenCode desktop error
o such column: name is an upstream OpenCode 1.18.18 SQLite migration failure, not an ADR Kit plugin failure. Desktop logs show it before the native plugin development session; upstream issue #40470 and PR #37707 document the same legacy migration-journal bug. The local opencode.db was rebuilt successfully at 2026-08-13T21:57:43Z. ADR Kit's plugin loads via opencode debug config, and the focused package/plugin suite passes 10 tests. No repository code was changed during this investigation; TASK-174 remains In Progress because its generic-support acceptance criteria are separate from ADR-039's native-plugin work.
---

author: OpenCode
created: 2026-08-16 20:07
---
Correction: the exact logged error is Error: no such column: name. The previous comment lost Markdown backticks because PowerShell uses them as escapes; the intended command name is opencode debug config.
---

author: OpenCode
created: 2026-08-16 21:31
---
ADR-039 was explicitly accepted on 2026-08-16. Native OpenCode support is now the approved architectural direction while the certified three-client gate remains unchanged. TASK-174's original generic-only description is now a separate compatibility track and should not be treated as the native-plugin decision.
---
<!-- COMMENTS:END -->
