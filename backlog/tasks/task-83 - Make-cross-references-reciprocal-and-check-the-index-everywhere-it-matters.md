---
id: TASK-83
title: 'Make cross-references reciprocal, and check the index everywhere it matters'
status: Done
assignee: []
created_date: '2026-08-01 10:34'
updated_date: '2026-08-02 18:30'
labels:
  - spec-gap
  - R7
  - index
  - lint
dependencies: []
modified_files:
  - bin/adr
  - bin/adr-lint
  - bin/adr-index
  - bin/adr_index_core.py
  - bin/adr_catalog.py
  - bin/adr_schema.py
  - bin/adr-guardian
  - schemas/adr-frontmatter.schema.json
  - templates/githooks/pre-commit
  - templates/github-workflows/adr-index-check.yml
  - .github/actions/adr-index-check/action.yml
  - skills/adr/SKILL.md
  - skills/guardian/SKILL.md
  - skills/install-hooks/SKILL.md
  - tests/test_adr_cross_references.py
  - tests/test_adr_index_freshness.py
  - tests/test_otgw_corpus.py
priority: medium
ordinal: 88500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R7. The index half is genuinely met and worth keeping: every `bin/adr` subcommand ends in `_commit_lifecycle_changes`, which snapshots the ADR files plus README.md/ADR-INDEX.md/ADR-INDEX.json, applies the writes and runs `run_index` inside the same rollback-able transaction. Two gaps around it.

**Supersession is the only reciprocal writer.** A new ADR that lists ADR-009 under Related Decisions updates nothing in ADR-009. `bin/adr-related` is read-only: it computes inbound, outbound and dangling links and prints them (`bin/adr-related:250-282`). `bin/adr-lint` has no reciprocity or dangling-related gate — only `detect_supersession_broken`. So the spec's "older ADRs updated too, precisely and reliably, not best-effort" holds for supersession and for nothing else.

R7 also says the LLM decides when a cross-reference is warranted. That is judgement and belongs in the authoring path; what must be mechanical is that a decided reference is *written on both sides* and that a dangling one is caught.

**Index freshness is not checked where it is most likely to rot.** `grep -l 'adr-index|--check'` over `bin/adr-guardian`, `bin/adr-lint`, `templates/githooks/pre-commit` and `skills/guardian/SKILL.md` returns nothing. The guarantee holds only for changes made through the lifecycle CLI; an ADR edited by hand, or written directly by a model with the Write tool, leaves the index stale until CI notices — and the CI check is on this repository, not in the templates a downstream project installs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 When an ADR gains a reference to another, the referenced ADR gains the reciprocal entry through a supported command
- [x] #2 adr-lint gains a gate for dangling and one-sided Related Decisions, at the appropriate severity
- [x] #3 The guardian sweep and the pre-commit hook check index freshness, not only the release path
- [x] #4 A downstream project installing adr-kit gets an index-freshness check in its own CI
- [x] #5 The authoring path asks the model to decide which cross-references are warranted, and the mechanism writes both sides once decided
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`bin/adr relate A --to B` writes a `related` frontmatter entry on **both** ADRs in one transaction, regenerating the indexes with it; `--remove` unwinds both the same way. Frontmatter rather than prose, because reference bookkeeping is a mutation the kit has always permitted on an Accepted record (`bin/adr supersede` writes `superseded_by` into one) while editing its body is not. A pair that already has a supersession relationship is refused rather than doubled.

`adr-lint` gates the declared links only: dangling → FAIL, one-sided → FAIL. Prose Related Decisions is deliberately **not** gated. It is free-form, names decisions from other repositories and ADRs not yet written, and adr-lint routinely runs on a fragment — `bin/adr accept` lints exactly one file, where every prose reference resolves to nothing. Gating that reports a fact about the invocation, not about the code, which ADR-009 forbids; an earlier draft did gate prose reciprocity and produced 57 advisories on this repository's own healthy 18-ADR set. `related` is machine-written, so a broken one can only come from a hand edit or a half-applied write.

Index freshness now has three checks at the strength each can honestly claim. The guardian nudges at SessionStart, in-process because `check` may never spawn, behind an mtime precondition that is a skip and not a proof (a hand-edited index is newer than every ADR and still wrong — pinned by a test). It stays silent for a project that has never generated an index at all. The commit hook warns rather than blocks, because it reads the worktree while the commit is the staged snapshot. CI blocks, and now ships downstream as `.github/actions/adr-index-check` plus a copyable `templates/github-workflows/adr-index-check.yml`.

Rendering moved from `bin/adr-index` into `bin/adr_index_core.py` (output unchanged) so the guardian can ask the generator its question without spawning it. The authoring skill now asks the model to decide which cross-references are warranted and to let `adr relate` write both sides.

24 new tests in `tests/test_adr_cross_references.py` and `tests/test_adr_index_freshness.py`; full suite green.
<!-- SECTION:FINAL_SUMMARY:END -->
