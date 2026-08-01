---
id: TASK-80
title: 'Init: read the git history, and use the auto-accept path the spec grants'
status: To Do
assignee: []
created_date: '2026-08-01 10:33'
labels:
  - spec-gap
  - R1
  - init
dependencies: []
priority: high
ordinal: 85500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R1. Two of its four clauses fail today.

**Git history is never read.** `.git/**` is in `DEFAULT_SKIP_GLOBS` (`bin/adr-audit:137`) and the four scanners (`scan_tooling`, `scan_dependencies`, `scan_doc_decisions`, `scan_template_profiles`) all walk the working tree only. The single `git log` in `bin/` is adr-judge's override-trailer reconciliation, which is enforcement, not bootstrap. Commit messages, merges, the order in which subsystems appeared and the churn that marks a contested area contribute nothing to the candidate set — even though that is where the *why* of an existing codebase actually lives.

**ADRs are not auto-accepted.** `skills/init/SKILL.md:227` writes `Status: Proposed` with the instruction "Never silently accept reconstructed history", and :406-408 requires individual grilling and acceptance. The machinery for R1's exception exists — `bin/adr accept --auto` → `command_auto_accept` (bin/adr:631) — but no shipped path reaches it, and it would refuse anyway: `_assert_auto_accept_eligible` demands `documents_shipped: true` plus `verified_in`, which init-generated ADRs do not carry, and it defaults to assist mode with no mutation without `--confirm`.

The spec grants this exception deliberately: the code already exists and the user is explicitly asking for the record. Reconstructing a decision that is already shipped is documentation, not authorisation.

**Also.** Init tells the model to "use the lifecycle command" but never names `bin/adr new`, while `allowed-tools` includes `Write` — a model that writes the file directly produces no index refresh, and no step verifies one happened. Make the index guarantee structural, not hoped-for.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The bootstrap scanner reads git history (at minimum commit messages and file-level churn) and its findings feed the candidate set
- [ ] #2 History-derived candidates are distinguishable from tree-derived ones, so a reviewer can see where a claim came from
- [ ] #3 Init-generated ADRs end Accepted via a supported path, carrying evidence that they document already-shipped behaviour
- [ ] #4 The auto-accept path is reachable from the shipped init flow, or is replaced by one that is
- [ ] #5 Init cannot finish with a stale index: the index refresh is verified rather than assumed
- [ ] #6 The 'never silently accept' instruction is reconciled with R1 in the skill text, so the two no longer contradict each other
<!-- AC:END -->
