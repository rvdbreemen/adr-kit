---
id: TASK-31
title: Validate ADR Kit against the OTGW-firmware ADR corpus
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:25'
updated_date: '2026-07-18 19:40'
labels:
  - testing
  - migration
  - real-world-corpus
  - otgw-firmware
dependencies: []
references:
  - 'https://github.com/rvdbreemen/OTGW-firmware'
  - ../OTGW-firmware/docs/adr
documentation:
  - tests/testsets/otgw-firmware/README.md
  - docs/format-migration.md
  - CONTRIBUTING.md
modified_files:
  - .gitattributes
  - CONTRIBUTING.md
  - docs/format-migration.md
  - scripts/refresh-otgw-corpus.py
  - tests/test_otgw_corpus.py
  - tests/testsets/otgw-firmware/README.md
  - tests/testsets/otgw-firmware/manifest.json
  - tests/testsets/otgw-firmware/LICENSE
  - tests/testsets/otgw-firmware/adrs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Freeze the adjacent OTGW-firmware repository's large real-world ADR collection as a provenance-tracked local test corpus and use it to validate format detection, graph/index/context readers, lint tolerance, migration planning, dry-run safety, and deterministic migration idempotence without depending on the adjacent checkout during CI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Exactly the 169 numbered OTGW-firmware ADR Markdown files are copied into a repository-local test-set directory without generated indexes, state files, or unrelated repository content.
- [x] #2 The corpus includes machine-readable provenance with source repository URL, source revision, ADR tree revision, source path, capture date, file count, per-file SHA-256 hashes, and preserved GPLv3 licensing information.
- [x] #3 Tests verify every corpus file against the manifest and fail on missing, unexpected, or modified fixtures.
- [x] #4 Migration planning runs read-only across the entire corpus and reports a deterministic format/action summary without crashing.
- [x] #5 Migration dry-run validation proves the frozen corpus is byte-for-byte unchanged and failures include actionable metadata or guided-migration reasons.
- [x] #6 The deterministic subset can be migrated in a temporary directory and reaches an idempotent check-clean state without mutating the frozen corpus.
- [x] #7 Index, JSON graph, context, relationship, and tolerant lint readers process the corpus without treating generated artifacts as ADRs or depending on the adjacent OTGW checkout.
- [x] #8 Contributor documentation explains corpus origin, licensing, refresh procedure, expected baseline, and how to intentionally update snapshot expectations.
- [x] #9 Focused corpus/migration tests and the complete repository test suite pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory only numbered `ADR-NNN-*.md` files from `../OTGW-firmware/docs/adr`, confirm none are locally modified, and capture origin URL, working revision, last ADR-tree commit, GPLv3 license, counts, sizes, and current migration-plan distribution.
2. Create `tests/testsets/otgw-firmware/` with `adrs/`, a copied source `LICENSE`, a human README, and a deterministic JSON manifest containing provenance, baseline planner counts, and sorted per-file SHA-256 hashes. Exclude generated indexes, README/state/lock files, and all non-ADR content.
3. Add one corpus test module that validates manifest integrity, runs planner and dry-run paths read-only, checks actionable failures, exercises shared catalog/index/context/related/lint readers, and migrates only planner-approved deterministic files inside pytest temporary directories before checking idempotence.
4. Keep tests independent of `../OTGW-firmware`; the adjacent checkout is used only by the explicit refresh procedure. Avoid asserting details that prevent legitimate parser improvements, while snapshotting format/action totals so behavior changes require an intentional baseline review.
5. Document source ownership/licensing, refresh commands, expected baseline, and how to review changed classifications/hashes in the corpus README and migration guide.
6. Run the new corpus suite, existing migration/index/context/profile suites, strict ADR/index/payload checks, and the complete pytest suite. Record evidence and finalize TASK-31.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User explicitly owns OTGW-firmware and requested copying its ADR set into adr-kit's local test set. Source working tree is dirty, but `git status` shows no numbered ADR Markdown modifications; corpus hashes and both repository/ADR-tree revisions will preserve provenance.

Initial source inventory: 169 numbered ADRs, 1,946,079 bytes. Current planner baseline: canonical=85, nygard=11, unknown=73; deterministic-preview=81, guided-migration=88. Whole-corpus metadata dry-run is read-only and currently reports 154 changed candidates and 15 actionable failures.

Completed the frozen real-world corpus at source revision `9eaf9618bd7931ac30270b393e8d12b923458e4b` and ADR-tree revision `b7b7ad71b69b85e4b0c6080148627293dd51695c`: exactly 169 numbered ADRs, 1,946,079 bytes, copied license, sorted SHA-256 manifest, and no generated/state/unrelated files. The source checkout's numbered ADR set remained clean; pre-existing `.adr-kit-state.json` and lock status were not copied or modified.

Validation evidence: `python -m pytest tests/test_otgw_corpus.py -q` -> 5 passed; related migration/index/context/relationship/profile/documentation slice -> 113 passed; `python -m pytest -q` -> 596 passed, 3 skipped; `python scripts/sync-agent-plugins.py --check`, strict self-lint, self-index check, `git diff --check`, and Python compilation all passed. Refresh reproducibility produced the identical manifest SHA-256 `5A2D8DC8447581C79F3F7944311D4FBE1DA34BE7FE19902AA42E7ED55FA745E9`.

Reviewed corpus behavior is pinned intentionally: canonical=85, nygard=11, unknown=73; deterministic-preview=81, guided-migration=88; metadata dry-run changed=154 and failed=15 with actionable reasons. Deterministic files migrate to MADR only in pytest temporary copies and pass a second idempotence check with zero changes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a provenance- and license-tracked OTGW-firmware ADR test corpus plus a deterministic refresh utility. New integration coverage validates exact fixture hashes, read-only planning and dry-run behavior, MADR migration idempotence on temporary copies, legacy JSON indexing, JSON graph generation, context retrieval, relationships, and tolerant lint across all 169 ADRs. Contributor and migration documentation explains corpus isolation, expected baselines, licensing, and the reviewed refresh workflow. All focused and full repository verification passes.
<!-- SECTION:FINAL_SUMMARY:END -->
