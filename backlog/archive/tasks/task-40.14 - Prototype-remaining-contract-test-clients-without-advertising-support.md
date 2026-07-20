---
id: TASK-40.14
title: Prototype remaining contract-test clients without advertising support
status: To Do
assignee: []
created_date: '2026-07-19 17:53'
updated_date: '2026-07-19 18:52'
labels:
  - prototypes
  - contract-tests
  - research
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.5
  - TASK-40.6
references:
  - 'https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins'
  - 'https://ampcode.com/manual'
  - 'https://kiro.dev/docs/cli/hooks/'
  - 'https://antigravity.google/docs/plugins'
  - 'https://docs.openhands.dev/sdk/guides/plugins'
  - 'https://github.com/XiaomiMiMo/MiMo-Code'
  - 'https://github.com/letta-ai/letta-code'
  - 'https://github.com/HKUDS/OpenHarness'
  - 'https://zcode.z.ai/en/docs/plugin'
modified_files:
  - docs/research/client-contract-tests/
  - tests/experimental/
  - clients/capabilities.json
parent_task_id: TASK-40
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run bounded disposable prototypes for Hermes, Amp, Kiro, Antigravity, OpenHands, MiMo Code, Letta Code, OpenHarness, and Z Code. The purpose is to turn unknowns into evidence, not to ship a broad set of partial adapters. Each client gets an independent go/no-go record against ADR Kit's actual start/task/edit/MCP/install/update/doctor requirements and adoption policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each prototype has a dated official-source contract snapshot, client/version, star/impact and recent-maintenance result, OS/surface scope, and unresolved assumptions.
- [ ] #2 A disposable adapter installs without modifying client source code or requiring an application author to wire an SDK manually.
- [ ] #3 Canonical skill/workflow and persistent project guidance are discoverable in the normal end-user client.
- [ ] #4 Session or invocation context reaches the model, task-tier ADR context can be supplied, and pre/post edit events expose target file arguments or an honest equivalent.
- [ ] #5 The local ADR Kit MCP/tool bridge initializes, lists tools, and completes one read-only call.
- [ ] #6 Installer can inspect installed version/source, update or replace it idempotently, disable/remove it, and preserve unrelated configuration.
- [ ] #7 Doctor distinguishes installed/active, disabled, stale, broken, unsupported-version, and not-installed states with evidence.
- [ ] #8 Hook failure/timeout behavior is proven fail-open and meets the applicable ADR Kit latency budgets.
- [ ] #9 For proprietary clients, material ecosystem impact and official versioned contract are documented; for open-source clients, >=2,000 stars and recent maintenance are verified.
- [ ] #10 Every prototype ends with one explicit outcome: promote into its own implementation task, remain contract-test with named blockers, compatibility-only, inherited/no separate adapter, or exclude.
- [ ] #11 No prototype changes the public supported-client list, default installer selection, or release claims before the certification gate in TASK-40.13 passes.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: planning review
created: 2026-07-19 18:52
---
Canceled by the approved 2026-07-19 maintainer scope decision. The open-ended prototype wave created an unbounded maintenance and research sink. TASK-38 remains the durable watchlist; any future prototype needs one nominated client, a bounded question, and explicit approval.
---
<!-- COMMENTS:END -->
