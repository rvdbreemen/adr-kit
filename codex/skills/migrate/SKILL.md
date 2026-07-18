---
name: migrate
description: Preview metadata migration or convert ADRs between MADR, Nygard, and legacy canonical profiles.
license: MIT
---

# Migrate ADRs

This is a write workflow. Resolve the plugin root from this skill's absolute
catalog path and run read-only discovery first:

```text
python <plugin-root>/bin/adr-migrate --plan <path>
```

The plan detects supported profiles and conservative Y-Statement,
Tyree/Akerman, and arc42 markers. It gives a deterministic preview command
when safe and routes ambiguous mappings back to guided review. It never writes.
For a supported source, run the reported preview:

```text
python <plugin-root>/bin/adr-migrate --dry-run --to-profile madr <path>
```

Show the proposed structural changes. Apply only after explicit confirmation,
by rerunning without `--dry-run`. Use `--from-profile` only after reading an
unknown/hybrid record. Preserve frontmatter, history, relationships,
references, prose, and Enforcement. Verify idempotency with
`--check --to-profile ...`, then run `$adr-kit:lint`.
