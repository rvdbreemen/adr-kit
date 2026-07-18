---
name: related
description: Show inbound and outbound references for one ADR and flag dangling links. Read-only.
license: MIT
---

# ADR relationships

Resolve the plugin root from this skill's absolute catalog path and run:

```text
python <plugin-root>/bin/adr-related <ADR-NNN> --adr-dir docs/adr --format json
```

Summarize outbound and inbound edges by relationship type. Flag dangling
references and ambiguous numbers. Do not edit any ADR.
