---
id: TASK-80
title: 'Init: read the git history, and use the auto-accept path the spec grants'
status: Done
assignee: []
created_date: '2026-08-01 10:33'
updated_date: '2026-08-02 20:19'
labels:
  - spec-gap
  - R1
  - init
dependencies: []
modified_files:
  - bin/adr_history_scan.py
  - bin/adr-discover
  - bin/adr
  - skills/init/SKILL.md
  - tests/test_adr_init_history_and_autoaccept.py
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
- [x] #1 The bootstrap scanner reads git history (at minimum commit messages and file-level churn) and its findings feed the candidate set
- [x] #2 History-derived candidates are distinguishable from tree-derived ones, so a reviewer can see where a claim came from
- [x] #3 Init-generated ADRs end Accepted via a supported path, carrying evidence that they document already-shipped behaviour
- [x] #4 The auto-accept path is reachable from the shipped init flow, or is replaced by one that is
- [x] #5 Init cannot finish with a stale index: the index refresh is verified rather than assumed
- [x] #6 The 'never silently accept' instruction is reconciled with R1 in the skill text, so the two no longer contradict each other
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**AC#1/#2 — history is read, and stays distinguishable.** `bin/adr_history_scan.py` reads decision-shaped commit subjects, file-level churn above a floor, and the order in which tooling and dependencies first arrived. It is a separate module on purpose: its findings are weaker. A file that exists is a fact; a commit subject is a claim someone typed once, possibly about a decision reversed three commits later. Every candidate now carries `source: "tree" | "history"`, history candidates carry a `why_this_is_weak` note, and the payload reports `history.available` with a reason. Everything fails open — no git, no repository, no commits — because a bootstrap that refuses to run on a thin history is worse than one that scans what it can and says which half is missing. `--no-history` and `--max-commits` are available.

**Two real defects blocked AC#3/#4, both fixed.**
1. `bin/adr document` wrote `changed_by: ""`. It appends a status-history entry like every other lifecycle command and so must resolve a signer like every other one; it did not. The audit gate then rejected the entry, so an ADR correctly marked as documenting shipped behaviour could never be accepted — and the failure surfaced two commands later, blaming acceptance.
2. **`accept --auto` accepted an untouched scaffold.** Every gate it ran was structural, and a scaffold is structurally perfect: all sections present, valid frontmatter, quality 0.88 against a 0.70 threshold. It would have written "Chosen option: **Option A**, because state the decisive rationale" into the record as an Accepted decision. `_scaffold_residue` now refuses a record still carrying template instructions — their presence is not a heuristic about quality, it is proof a section was never written.

**AC#6 — "never silently accept" reconciled, not deleted.** What it forbids is the *silently*. Reconstructing a decision the code already implements is documentation, not authorisation. Init now asks once per batch, and every record still passes its own gates through `--auto`, which demands `documents_shipped: true`, a `verified_in` pointer, no unresolved Open Questions, and a quality score. A decision that is not already shipped is a new decision and goes through ordinary grilling.

**AC#5 — the index is verified, not assumed.** Init names `bin/adr new` explicitly instead of gesturing at "the lifecycle command", and a new step 3c runs `adr-index docs/adr --check` with an explicit rule that init does not finish while it is non-zero.

14 new tests in `tests/test_adr_init_history_and_autoaccept.py`; full suite green (1411 passed, 13 skipped).
<!-- SECTION:FINAL_SUMMARY:END -->
