---
name: install-hooks
description: Install or remove ADR Kit's deterministic pre-commit gate without changing agent client configuration.
license: MIT
---

# Install ADR enforcement hooks

Resolve the plugin root from this skill's absolute catalog path. Before writing,
inspect `core.hooksPath` and any existing hook.

For install, copy `<plugin-root>/templates/githooks/pre-commit` to
`.githooks/pre-commit`, preserving an unrelated existing hook by chaining it,
then set:

```text
git config core.hooksPath .githooks
```

For uninstall, remove only the ADR Kit wrapper and restore the prior chained
hook when present. Do not edit Claude settings, Copilot settings, or Copilot config.
The multi-client installer owns those installation surfaces.
