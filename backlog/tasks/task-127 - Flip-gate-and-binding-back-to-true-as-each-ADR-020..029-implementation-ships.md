---
id: TASK-127
title: Flip gate and binding back to true as each ADR-020..029 implementation ships
status: To Do
assignee: []
created_date: '2026-08-04 17:29'
updated_date: '2026-08-04 23:02'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
INVESTIGATION 2026-08-05 — none of the ten gates exist yet, so only AC#2 is implementable.

VERIFIED: the repo's own resolver, `_resolve_gates_locally(<the ten names>, repo_root)` from bin/adr-lint:1010, returns the empty set for all ten. The reason is structural, not accidental: TEXT_SCAN_SKIP_DIRS (bin/adr-lint:249-258) contains both `docs` and `backlog`, so an ADR's own Verification bullet and this task's table cannot make a gate 'exist'. A raw grep confirms every occurrence of all ten names lives under docs/adr/ or backlog/tasks/ — zero in bin/, tests/, scripts/, .github/.

Consequence: AC#1 and AC#3 are vacuous today (nothing to flip). AC#2 — the check that fails when a gate name appears in the tree while the ADR naming it still carries gate:null — is the durable half and can be built now. Its value is prospective: landing it means the anchors arrive already covered.

CORRECTION TO A SIBLING RECORD: backlog task-100 line 67 claims 'the gate anchor adr-audit-exit-contract-v1 has real coverage in source'. That conflates behaviour with the anchor. tests/test_adr_audit_command.py does test the five exit codes, but the literal string `adr-audit-exit-contract-v1` appears nowhere in tests/. Under the rule at bin/adr-lint:1138 the anchor is a literal-string requirement, so ADR-026's gate is still absent.

MEASURED COST: the declared-gate probe adds roughly +220 ms to adr-lint, which makes the corpus row for adr-lint (p50_ms 1200) false on landing — post-change p50 lands near 1340 ms. Two mitigations were measured and both rejected on evidence. Coordinate with TASK-126, which owns the corpus.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-04 18:09
---
Injection-independence is now confirmed live, not only by grep. After the flip to `binding: false`, this session's `UserPromptSubmit` hook context listed "Governing Accepted ADRs relevant to this prompt: ADR-020, ADR-026, ADR-027" — three records that all carry `binding: false`. The injection path answered with them, so the arrangement rests on an observed property rather than on the absence of a reader in `hooks/`.

That matters because injection is the thing the flip must not cost. What it does cost stays as written: `adr_retrieval_health` skips these records' Decision Contract check while they are non-binding.
---
<!-- COMMENTS:END -->
