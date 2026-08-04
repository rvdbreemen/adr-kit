---
id: TASK-108
title: 'Make inject.enabled and watch.enabled true, or stop claiming them'
status: Done
assignee: []
created_date: '2026-08-03 19:34'
updated_date: '2026-08-03 22:21'
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
- [x] #1 Either the toggles work or they are gone; the schema description matches the behaviour either way
- [x] #2 If they work: a test sets each toggle false and asserts the corresponding hook emits nothing
- [ ] #3 If they go: `/adr-kit:settings` still shows the user how to turn injection off, through the install-hooks path
- [x] #4 The chosen route is stated in the commit message with the reason, since both are defensible
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Made them work rather than deleting them, and the reason is in the commit as AC#4 asks.

Of the two routes, this one matches what the kit already does: `guardian.enabled` has been honoured since v0.18, so the pattern is the project's own rather than a new invention, and the settings surface stays one file instead of half a file plus an install command.

**The switches are independent.** `inject` is PreToolUse, `watch` is PostToolUse. A team may reasonably want the pre-edit constraint without the post-edit backstop, or the reverse; one key silencing both would be a different feature from the one the schema documents. Two tests assert the crossed pairs still inject.

**Only an explicit `false` switches a tier off.** A missing key, a missing file, a wrong type, the string `"false"` and an unparseable document all keep injecting — five parametrised cases. The reasoning is worth keeping: a settings surface must not be able to silence governance by being broken, and the failure mode of guessing the other way is silent loss of a constraint the user believes is in force.

Refactored `_configured_limit` onto a shared `_project_config` reader so the config file is parsed the same way for all three keys, instead of one function owning both the read and its own error handling.

AC#3 does not apply: the toggles were kept, so `/adr-kit:settings` needs no install/uninstall rows.

148 hook, watch and settings tests pass; all three client trees regenerated.
<!-- SECTION:FINAL_SUMMARY:END -->
