---
id: TASK-40.12
title: Add and certify OMP and Pi package adapters
status: To Do
assignee: []
created_date: '2026-07-19 17:53'
updated_date: '2026-07-19 18:52'
labels:
  - omp
  - pi
  - typescript
  - packages
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.4
  - TASK-40.5
  - TASK-40.6
  - TASK-40.7
references:
  - 'https://pi.dev/'
  - 'https://github.com/can1357/oh-my-pi'
modified_files:
  - clients/omp/
  - clients/pi/
  - hooks/adapters/pi-family.ts
  - tests/fixtures/omp/
  - tests/fixtures/pi/
  - tests/test_pi_family_adapters.py
  - docs/clients/omp.md
  - docs/clients/pi.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build minimal reviewed TypeScript package bridges for OMP and Pi. Package canonical Agent Skills and prompt templates, register the local ADR Kit MCP/tool bridge, map supported session/turn/tool/compaction events to the normalized hook core, and integrate native package install/update/remove plus doctor. Pi's extension-owned MCP/subagent capabilities must be explicit and testable, not assumed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 OMP and Pi packages contain no ADR domain logic and delegate every ADR operation to the canonical Python engine.
- [ ] #2 Canonical skills and prompt templates are discoverable and user-invocable under stable documented names in both clients.
- [ ] #3 AGENTS.md project guidance points to `.adr-kit/ADR-guide.md` and works in primary and delegated execution modes.
- [ ] #4 Session/task/turn and pre/post edit events map to the normalized core; compaction and unused events are safe no-ops unless the registry assigns behavior.
- [ ] #5 Pi explicitly registers and validates its MCP/tool bridge and any subagent integration required for parity; missing extension-owned functionality is a failed certification, not a hidden degradation.
- [ ] #6 OMP uses its native plugin/package and compatibility providers without accidentally loading duplicate Claude/Codex/OpenCode copies.
- [ ] #7 Installer supports npm/git/local package sources as officially allowed, pins/verifies the ADR Kit version, handles update/remove, preserves unrelated config, and converges on rerun.
- [ ] #8 Doctor verifies package load, bridge-to-Python invocation, skill/prompt discovery, MCP/tool handshake, event registration, version/source, disabled state, and duplicate compatibility providers.
- [ ] #9 Windows path quoting, missing Node/Bun/package manager, reload semantics, concurrent package load, interrupted update, and rollback are covered by fixtures.
- [ ] #10 Latency and native smokes pass for start/task/edit behavior and prove no network/LLM call inside hooks.
- [ ] #11 Each client is promoted independently only after real install/list, command/skill, hook, MCP/tool, update/rollback, uninstall, and documentation evidence.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: planning review
created: 2026-07-19 18:52
---
Canceled by the approved 2026-07-19 maintainer scope decision. OMP and Pi native package adapters are outside the three-client first-class ceiling. Generic portability is the only current path unless a future task is explicitly approved.
---
<!-- COMMENTS:END -->
