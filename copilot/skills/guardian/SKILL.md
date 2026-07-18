---
name: guardian
description: Run ADR Kit health, drift, stale-decision, and optional semantic sweeps for the active project.
license: MIT
---

# ADR guardian for GitHub Copilot CLI

Resolve the plugin root from this skill's absolute catalog path, then run the
bundled tools against the active workspace:

```text
python <plugin-root>/bin/adr-doctor docs/adr/
python <plugin-root>/bin/adr-retire docs/adr/ --format json
python <plugin-root>/bin/adr-status --adr-dir docs/adr/ --format json
```

Report drift first, then retirement candidates, then health. Never apply ADR
edits automatically.

Only run the LLM tier after explicit cost confirmation. In Copilot CLI, perform the
semantic review in the active model session. Do not shell out to Claude unless
the user explicitly selected that configured provider.
