---
name: retire
description: Rank Accepted ADRs for retirement using deterministic age, technology, supersession, and policy signals. Read-only.
license: MIT
---

# ADR retirement audit

Resolve the plugin root from this skill's absolute catalog path and run:

```text
python <plugin-root>/bin/adr-retire docs/adr/ --format json
```

For each candidate show the signal and draft a possible status transition.
Never apply it automatically. A human must choose Deprecated, Superseded, or
keep.
