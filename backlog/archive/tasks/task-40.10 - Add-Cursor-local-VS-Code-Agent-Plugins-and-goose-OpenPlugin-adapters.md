---
id: TASK-40.10
title: 'Add Cursor local, VS Code Agent Plugins, and goose OpenPlugin adapters'
status: To Do
assignee: []
created_date: '2026-07-19 17:52'
updated_date: '2026-07-19 18:52'
labels:
  - cursor
  - vscode
  - goose
  - openplugin
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.4
  - TASK-40.5
  - TASK-40.6
  - TASK-40.7
references:
  - 'https://cursor.com/docs/reference/plugins'
  - 'https://cursor.com/docs/hooks'
  - 'https://code.visualstudio.com/docs/agent-customization/agent-plugins'
  - 'https://code.visualstudio.com/docs/agent-customization/hooks'
  - 'https://goose-docs.ai/docs/guides/context-engineering/hooks/'
modified_files:
  - clients/cursor/
  - clients/vscode/
  - clients/goose/
  - tests/fixtures/cursor/
  - tests/fixtures/vscode/
  - tests/fixtures/goose/
  - tests/test_openplugin_adapters.py
  - docs/clients/
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate the Cursor IDE/local and VS Code Agent Plugin payloads from a shared OpenPlugin/Claude-compatible source while retaining native manifests, event filtering, surface detection, update probes, and doctor fixtures. Prototype goose from the same canonical inputs, but keep it contract-test until its independent native lifecycle passes. Cursor CLI and cloud remain separate degraded surfaces.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Cursor IDE/local plugin bundles canonical skills, commands, rules/instructions, MCP, and hooks through its documented plugin format.
- [ ] #2 Cursor sessionStart, beforeSubmitPrompt, pre/post edit tool events, and SubagentStart map correctly; unsupported cloud events are omitted and cloud is never reported as local support.
- [ ] #3 Cursor CLI is detected separately and reported compatibility-only unless its own official hook/plugin contract has passed certification.
- [ ] #4 VS Code Agent Plugin bundles canonical slash commands, Agent Skills, agents/rules, hooks, and MCP using the current preview format and reports preview status visibly.
- [ ] #5 VS Code adapter filters matcher semantics inside the wrapper where the host ignores Claude matcher values, preventing non-edit tools from triggering edit-tier logic.
- [ ] #6 goose payload uses its native Open Plugins layout and available SessionStart/UserPrompt/Pre/PostTool/Stop events, but is not promoted until install/update/doctor and all ADR Kit-required execution modes pass.
- [ ] #7 The shared generator proves common semantic content while each client retains native event/output fixtures and no unsupported/dead hook declarations.
- [ ] #8 Installer uses native install/update/remove paths where available, preserves unrelated config, handles global/project precedence, and rolls back failed activation.
- [ ] #9 Doctor distinguishes Cursor local/cloud/CLI, VS Code preview/version incompatibility, goose partial/experimental state, disabled plugins, missing hooks, MCP failure, stale payload, and healthy state.
- [ ] #10 Native edit smoke proves governing ADR context before a local write and PostToolUse confirmation afterward without duplicate context.
- [ ] #11 Windows/macOS/Linux tests and user documentation cover install, update, reload/restart needs, rollback, uninstall, cloud limitations, and preview status.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: planning review
created: 2026-07-19 18:52
---
Canceled by the approved 2026-07-19 maintainer scope decision. Cursor, VS Code, and goose native adapters are deferred; the three-client first-class maintenance ceiling is Claude, Codex, and Copilot. Research remains in TASK-38 and may inform a future separately approved task.
---
<!-- COMMENTS:END -->
