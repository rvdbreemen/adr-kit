---
id: TASK-127
title: Flip gate and binding back to true as each ADR-020..029 implementation ships
status: To Do
assignee: []
created_date: '2026-08-04 17:29'
updated_date: '2026-08-04 18:09'
labels:
  - adr
  - follow-up
  - consistency
dependencies: []
priority: medium
ordinal: 97500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-020 through ADR-029 were accepted on 2026-08-04 with `gate: null` and `binding: false`, because every one of them declared a named gate that does not exist yet. `adr-lint` refuses an Accepted binding ADR whose gate cannot be resolved in the tree, and refuses a binding one that names no gate at all, so the fields had to say what was true rather than what was intended.

The intended gate name is recorded in each ADR's Verification section. Both fields flip back **together**, per record, when its gate actually exists:

| ADR | intended gate |
| --- | --- |
| ADR-020 | `adr-query-embedding-v1` |
| ADR-021 | `adr-hook-index-refresh-v1` |
| ADR-022 | `adr-open-questions-append-only-v1` |
| ADR-023 | `adr-pr-guard-tier-v1` |
| ADR-024 | `adr-pr-suggest-v1` |
| ADR-025 | `adr-config-trust-boundary-v1` |
| ADR-026 | `adr-audit-exit-contract-v1` |
| ADR-027 | `adr-signer-derivation-v1` |
| ADR-028 | `adr-reference-gate-scope-v1` |
| ADR-029 | `adr-single-retrieval-engine-v1` |

This is the part of the arrangement that decays silently. `binding: false` costs two things while it lasts: `adr_retrieval_health` skips the record's Decision Contract check (it only inspects Accepted **binding** records), and the frontmatter understates a decision that is in fact meant to constrain implementation. Edit-time injection is unaffected — `hooks/` does not read `binding` at all, only `status`.

Consider making the flip mechanical rather than remembered: a check that fails when a gate name appears in the tree while the ADR that names it in its Verification section still carries `gate: null`. That turns "someone must remember" into "the gate tells you".

Evidence: `bin/adr-lint:1053` and `:1104` (the two rules); `bin/adr_retrieval_health.py:137`; commit accepting ADR-020..029.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each of ADR-020..029 carries gate plus binding:true once its gate exists in the tree
- [ ] #2 A check fails when a named gate exists while the ADR expecting it still has gate:null, so the flip is not left to memory
- [ ] #3 No record sits at binding:false with a shipped implementation
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-04 18:09
---
Injection-independence is now confirmed live, not only by grep. After the flip to `binding: false`, this session's `UserPromptSubmit` hook context listed "Governing Accepted ADRs relevant to this prompt: ADR-020, ADR-026, ADR-027" — three records that all carry `binding: false`. The injection path answered with them, so the arrangement rests on an observed property rather than on the absence of a reader in `hooks/`.

That matters because injection is the thing the flip must not cost. What it does cost stays as written: `adr_retrieval_health` skips these records' Decision Contract check while they are non-binding.
---
<!-- COMMENTS:END -->
