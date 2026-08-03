---
id: TASK-108
title: 'Make inject.enabled and watch.enabled true, or stop claiming them'
status: To Do
assignee: []
created_date: '2026-08-03 19:34'
labels:
  - settings
  - hooks
  - bug
dependencies:
  - TASK-103
priority: medium
ordinal: 3500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The settings surface makes a promise the code does not keep. `schemas/adr-kit-config.schema.json` describes `inject.enabled` as "When false, the PreToolUse injector never emits context and the hook is a no-op for this project", and `watch.enabled` similarly for PostToolUse. Both are inert.

`hooks/adr_hook_core.py` reads `.adr-kit.json` exactly once, at `_configured_limit`, and takes only `context.default_limit`. `inject.enabled` is read by `bin/adr-watch:223`, which no hook invokes on any of the three clients — `.claude-plugin/plugin.json` declares no hooks, and the codex and copilot plugin manifests point at their own `hooks.json`, neither of which mentions `adr-watch`. A user who sets `inject.enabled: false` is told the hook is now a no-op, and the injection keeps firing.

The pattern already exists and works: `guardian.enabled` is honoured at `bin/adr-guardian:735-736`, so one hook is switchable from the settings surface today.

Two honest routes, pick one and say why in the commit: have `adr_hook_core` read a per-event `hooks.*` block from `.adr-kit.json`, which keeps one file authoritative; or delete the two dead keys, correct the schema, and have `/adr-kit:settings` render install/uninstall rows by calling `install-hooks` in a status mode — which keeps consent where `skills/settings/SKILL.md:61-62` deliberately put it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Either the toggles work or they are gone; the schema description matches the behaviour either way
- [ ] #2 If they work: a test sets each toggle false and asserts the corresponding hook emits nothing
- [ ] #3 If they go: `/adr-kit:settings` still shows the user how to turn injection off, through the install-hooks path
- [ ] #4 The chosen route is stated in the commit message with the reason, since both are defensible
<!-- AC:END -->
