---
name: migrate
description: Migrate legacy, MADR, or Nygard decision records into ADR Kit's canonical format with preview and confirmation.
license: MIT
---

# Migrate ADRs

This is a write workflow. Resolve the plugin root from this skill's absolute
catalog path and run a preview first:

```text
python <plugin-root>/bin/adr-migrate <path>
```

Show the proposed structural changes. Apply only after explicit confirmation,
preserving prose that already exists and using TODO markers for genuinely
missing content. Run `the ADR Kit lint skill` after the approved migration.
