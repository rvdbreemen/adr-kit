---
id: TASK-144
title: Remove the embedding/vector subsystem
status: To Do
assignee: []
created_date: '2026-08-09 10:34'
labels: []
dependencies:
  - TASK-143
references:
  - docs/plans/kiss-simplification-plan.md
priority: high
ordinal: 115500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 3 of docs/plans/kiss-simplification-plan.md. Requires the records from TASK-143 to exist first (R10: no removal before supersession). Delete bin/adr-embed, bin/adr_vector_store.py, bin/adr_embedding_runtime.py, hooks/adr_embed_query.py, the vector route in bin/adr_query.py (_apply_semantic_order collapses to the lexical path), the embedding doctor probes in bin/adr_doctor_probes.py, and EMBEDDING_EVENTS in hooks/adr-hook.py. Revert user-prompt-submit in hooks/manifest.json to network_allowed: false and drop its network_reason. Remove the R16 setup dialogue from the setup/init skills. Remove dedicated tests (test_adr_embedding_runtime.py, test_adr_vector_store_contract.py) and embedding assertions elsewhere. Mind ADR-010 line limits and tests/test_release_allowlist.py when files disappear from the allowlist.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 No file under bin/ or hooks/ imports or spawns an embedding backend; grep for embed over bin/ hooks/ returns only historical ADR text
- [ ] #2 hooks/manifest.json declares network_allowed: false for user-prompt-submit
- [ ] #3 python -m pytest -q passes; build-client-adapters.py --check reports changed=0
<!-- AC:END -->
