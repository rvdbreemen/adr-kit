---
name: supersede
description: Replace an Accepted ADR with a Proposed successor while preserving history and reciprocal links.
license: MIT
---

# Supersede an ADR

This is a write workflow. First run `$adr-kit:related` for the target. Draft the
successor as Proposed and show it for approval. After approval, use:

```text
python <plugin-root>/bin/adr supersede <old-id> --by <new-id> --adr-dir docs/adr
```

The CLI rejects illegal transitions, existing or competing successor pointers,
and incoherent reciprocal state before mutation. It updates both ADRs and all
generated index views in one rollback-safe transaction. Verify the reciprocal
links and append-only status history afterward. Never rewrite the old Decision
or reproduce the lifecycle edits manually.
