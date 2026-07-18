---
name: lint
description: Validate ADRs against schema, completeness, evidence, clarity, and consistency gates. Read-only.
license: MIT
---

# Lint ADRs

Resolve the plugin root from this skill's absolute catalog path. Run:

```text
python <plugin-root>/bin/adr-lint --strict <path-or-docs/adr>
```

Report PASS, ADVISORY, and FAIL separately with file and line citations.
Evaluate Evidence and Clarity in-session where deterministic checks cannot.
End with one recommended action against the most important FAIL. Do not edit
ADRs.
