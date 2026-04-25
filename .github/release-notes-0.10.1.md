# adr-kit v0.10.1

Patch release: aligns the lint skill's invocation discipline with the setup skill so the plugin offers a uniform `/adr-kit:<skill>` pattern.

## What changed

`skills/lint/SKILL.md` frontmatter gains `disable-model-invocation: true`. Before:

- `/lint` (root namespace, auto-invocable) AND `/adr-kit:lint` (prefix) both registered.

After:

- Only `/adr-kit:lint` registered, matching `/adr-kit:setup`.

## Why

Lint is a deliberate user action: a checking tool you reach for explicitly, not a background helper. The same reasoning that put `disable-model-invocation: true` on `setup` (a one-time write action) applies here: when the user means to check, they say so.

The setup and lint skills now follow the same invocation discipline. The main `adr` skill keeps auto-invocation enabled (it is a knowledge/guide skill that legitimately benefits from Claude triggering it when context calls for it).

## What did not change

- Lint logic. Severity model, gate evaluation, output format are identical to v0.10.0.
- `bin/adr-lint`. The deterministic CLI is independent of the skill's invocation discipline.
- Tests. The 15 pytest tests in `tests/test_adr_lint.py` exercise the CLI, not the skill's frontmatter, so they pass unchanged.

## Install / upgrade

Existing installations:

```
/plugin marketplace remove rvdbreemen-adr-kit
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
```

After reload, only `/adr-kit:lint` will appear in autocomplete; the root-namespace `/lint` form is gone.

## Refs

- Backlog task: TASK-423 (lint skill invocation discipline alignment with setup).
- Originating release: v0.10.0 (`bin/adr-lint` deterministic CLI).
