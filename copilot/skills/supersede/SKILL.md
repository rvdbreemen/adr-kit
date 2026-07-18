---
name: supersede
description: Replace an Accepted ADR with a Proposed successor while preserving history and reciprocal links.
license: MIT
---

# Supersede an ADR

This is a write workflow. First run `the ADR Kit related skill` for the target. Draft the
successor as Proposed and show it for approval. After approval, use:

```text
python <plugin-root>/bin/adr supersede <old-id> <new-id> --adr-dir docs/adr
```

Verify both reciprocal links, append-only status history, and the generated
index. Never rewrite the old Decision or overwrite an existing supersession
pointer.
