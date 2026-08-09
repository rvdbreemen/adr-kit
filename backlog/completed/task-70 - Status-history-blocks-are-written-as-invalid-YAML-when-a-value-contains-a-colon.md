---
id: TASK-70
title: >-
  Status history blocks are written as invalid YAML when a value contains a
  colon
status: Done
assignee: []
created_date: '2026-07-30 23:01'
updated_date: '2026-07-30 23:06'
labels:
  - adr
  - lifecycle
  - data-integrity
dependencies: []
references:
  - 'bin/adr:194'
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
  - >-
    docs/adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md
  - docs/adr/ADR-009-bound-heuristic-gates-to-findings-an-author-can-act-on.md
modified_files:
  - bin/adr
  - tests/test_adr_lifecycle.py
priority: high
ordinal: 75500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`history_entry()` (`bin/adr:194`) emits every field as a bare YAML plain scalar. A value containing `": "` therefore terminates the scalar and reads as a nested mapping, which makes the **entire** `status_history` block unparseable — not just the offending line.

**Already affecting three ADRs in this repository**, found by parsing every fenced `yaml` block in `docs/adr/` with PyYAML:

```
ADR-007 -> reason: Amended by ADR-014: advance the generated graph enforcement gate ...
ADR-008 -> reason: Human approval: records the v0.34.0 engine-resolution decision ...
ADR-009 -> reason: Human approval: records the v0.34.0 heuristic-gate scope decision ...
```

All three fail with `ScannerError: mapping values are not allowed here`.

**The recommended workflow produces it.** `.claude/adr-kit-guide.md` tells authors to pass `--changed-by "User: <name>"`, which writes `changed_by: User: Robert van den Breemen` — invalid. Reproduced on a scratch set:

```
changed_by: User: Test
                ^ ScannerError: mapping values are not allowed here
```

I hit this twice by hand while accepting ADR-016 and ADR-017 and quoted the values manually, without recognising it as a tooling defect rather than a formatting preference.

**Why it went unnoticed.** adr-kit reads these blocks with its own stdlib mini-parser, which is line-oriented and takes everything after the first colon as the value. So `bin/adr-lint --strict docs/adr` reports 17/17 PASS with three unparseable blocks on disk. The project's own tools are the only consumers that tolerate it; any external consumer using a real YAML parser sees a corrupt block.

`reason` is the field most likely to contain a colon, because it holds free text, but `changed_by` and `changed_via` have the same exposure. Other YAML-hostile shapes (a leading `- `, `#`, `*`, `&`, a trailing colon) are the same class of defect.

**Repair note.** Fixing the three existing files means editing Accepted ADRs, which the project treats as immutable. This is a syntactic repair that makes existing bytes parseable and changes no meaning — no date, status, actor or wording is altered. That distinction should be stated in the commit rather than assumed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `history_entry()` emits values that round-trip through a real YAML parser regardless of content, including colons, leading indicators and trailing colons
- [x] #2 The three existing damaged ADRs (007, 008, 009) parse cleanly, with no change to any date, status, actor or reason wording
- [x] #3 A regression test asserts that a status history written with a colon-bearing reason and a colon-bearing changed_by parses with a real YAML parser, not only with the project's own mini-parser
- [x] #4 A test guards the whole ADR directory: every fenced yaml block in docs/adr/ parses, so a future regression is caught in CI rather than by an external consumer
- [x] #5 If PyYAML is unavailable in the test environment the guard skips explicitly rather than passing silently, since a silent pass is what let this survive
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed at the writer and repaired the three damaged files.

**Writer.** `bin/adr` gains `_yaml_scalar()`, used by `history_entry()` for all five fields. It quotes only when a plain scalar would not survive: empty string, leading or trailing whitespace, `": "`, a trailing `:`, `" #"`, or a leading YAML indicator character. Quoting is double-quoted style with backslash and quote escaping, the one style that can represent every scalar. Values that are already safe stay unquoted, so existing output style is preserved and the diff stays small.

Verified by round-tripping five hostile shapes through PyYAML and comparing each parsed value to the original: a colon-bearing `changed_by`, a colon-bearing `reason`, a leading `- `, a trailing `:`, a `#`, an `*` anchor, an `@`, embedded quotes, a backslash, a padded string and an empty string. All match exactly.

**Repair.** ADR-007, ADR-008 and ADR-009 each had exactly one offending line — in every case a `reason` containing `": "`. Repaired by re-rendering the block through the same `_yaml_scalar`, with an assertion that every parsed value equals the original raw text before the file is written. One line changed per file; no date, status, actor or wording altered. This does edit Accepted ADRs, which the project treats as immutable — the justification is that it is a syntactic repair making existing bytes parseable, not a change of meaning, and it is stated rather than assumed.

**Tests** in `tests/test_adr_lifecycle.py`:

- `test_history_entry_round_trips_through_a_real_yaml_parser` — the five hostile shapes. Teeth verified: with the quoting neutralised it fails with `ScannerError`.
- `test_every_status_history_block_in_the_repo_parses` — directory-wide guard over `docs/adr/`. This one does not fail against the unfixed writer, and that is correct: it guards the *data*, and the data is already repaired. Its job is to catch the next regression in CI rather than downstream.

Both use `pytest.importorskip("yaml")` with an explicit reason. A silent pass is precisely what let this survive, so the skip is loud.

**Why it hid for so long.** adr-kit reads these blocks with its own line-oriented mini-parser that takes everything after the first colon as the value. `bin/adr-lint --strict docs/adr` reported 17/17 PASS with three unparseable blocks on disk. Asserting with the project's own parser would have reproduced exactly the blind spot, which is why both tests reach for PyYAML.

Worth recording: I hit this twice by hand, quoting `changed_by` manually while accepting ADR-016 and ADR-017, and read it as a formatting preference rather than a tooling defect. It only surfaced as a real bug when I parsed the generated output with something other than adr-kit itself.

Verification: `tests/test_adr_lifecycle.py` 21 passed; lifecycle + lint + mcp 102 passed; `bin/adr-lint --strict docs/adr` 17/17 PASS, 0 FAIL; indexes regenerated with no change.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
