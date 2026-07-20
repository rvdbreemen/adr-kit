---
id: TASK-40.11
title: Add and certify Qwen Code and Gemini CLI extension adapters
status: To Do
assignee: []
created_date: '2026-07-19 17:52'
updated_date: '2026-07-19 18:52'
labels:
  - qwen
  - gemini
  - extensions
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.4
  - TASK-40.5
  - TASK-40.6
  - TASK-40.7
references:
  - 'https://qwenlm.github.io/qwen-code-docs/en/users/extension/introduction/'
  - 'https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/'
  - 'https://geminicli.com/docs/extensions/reference/'
modified_files:
  - clients/qwen/
  - clients/gemini/
  - tests/fixtures/qwen/
  - tests/fixtures/gemini/
  - tests/test_gemini_family_adapters.py
  - docs/clients/qwen.md
  - docs/clients/gemini.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate Qwen Code and Gemini CLI extensions from a shared Gemini-family source. Package canonical skills, commands, subagent/context files, hooks, and MCP while retaining separate native manifests, event outputs, updater behavior, doctor probes, and migration notes. Treat Gemini as a transition adapter where official migration guidance applies; Qwen remains an independent target.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both extensions install/list/update/remove through their documented native mechanisms and report canonical ADR Kit version/source.
- [ ] #2 Canonical skills and commands are discoverable and invoke the same workflows and arguments as existing clients.
- [ ] #3 QWEN.md/GEMINI.md or extension context points to `.adr-kit/ADR-guide.md` only where native plugin context and AGENTS.md are insufficient; user files remain marker-owned and non-clobbered.
- [ ] #4 SessionStart, UserPromptSubmit, Pre/PostToolUse, and SubagentStart map to normalized ADR Kit behavior with bounded model-visible output.
- [ ] #5 PreCompact, Stop, SessionEnd, failure, permission, notification, HTTP/background, and unused events are declared only when supported and otherwise safely no-op.
- [ ] #6 Qwen import/compatibility with Gemini/Claude ecosystems does not create duplicate ADR Kit payloads or cause the wrong adapter to win.
- [ ] #7 Gemini auto-update is exposed as an explicit installer policy; transition/migration state is visible in doctor and documentation.
- [ ] #8 MCP handshake resolves the current prepared Python payload on Windows, macOS, and Linux without source mutation.
- [ ] #9 Doctor detects disabled extension, duplicate imported plugin, missing command/skill, hook mismatch, update-source failure, unsupported version, stale cache, and healthy state independently for Qwen and Gemini.
- [ ] #10 Native smokes cover install/list, skill/command, session/task/edit hooks, MCP, update/rollback, uninstall, and a second-run no-op.
- [ ] #11 Capability status is promoted independently; a Gemini product transition cannot silently remove Qwen support or shared canonical artifacts.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: planning review
created: 2026-07-19 18:52
---
Canceled by the approved 2026-07-19 maintainer scope decision. Qwen Code and Gemini CLI native adapters are deferred; compatibility may use the generic bundle without a custom adapter. Research remains in TASK-38.
---
<!-- COMMENTS:END -->
