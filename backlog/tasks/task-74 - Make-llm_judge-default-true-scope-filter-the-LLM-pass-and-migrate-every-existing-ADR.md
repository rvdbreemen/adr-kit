---
id: TASK-74
title: >-
  Make llm_judge default true, scope-filter the LLM pass, and migrate every
  existing ADR
status: Done
assignee: []
created_date: '2026-08-01 09:16'
updated_date: '2026-08-01 10:05'
labels:
  - judge
  - llm
  - adr-017
  - cost
dependencies: []
modified_files:
  - bin/adr-judge
  - bin/adr-lint
  - bin/adr-migrate
  - bin/adr_llm_judge_migration.py
  - codex/bin/
  - copilot/bin/
  - schemas/adr-enforcement.schema.json
  - skills/adr/SKILL.md
  - skills/upgrade/SKILL.md
  - agents/adr-generator.md
  - templates/adr-template.md
  - templates/adr-template.madr.md
  - templates/adr-template.canonical.md
  - templates/adr-template.nygard.md
  - templates/adr-kit-guide.md
  - tests/test_adr_judge_llm.py
  - tests/test_adr_llm_judge_migration.py
  - tests/test_documentation_contracts.py
  - README.md
  - CHANGELOG.md
  - docs/adr/*.md
priority: high
ordinal: 79500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today every Accepted ADR in this repo carries `"llm_judge": false`, so the LLM pass that ADR-017 turned on by default has an empty population and never runs. Six ADRs (002, 004, 006, 012, 013, 014) go further: their Enforcement block contains zero forbid rules, zero require rules and `llm_judge: false`, so the block enforces literally nothing while looking like a guard.

Maintainer decision (2026-08-01): the default must be `llm_judge: true`, and an update must walk every existing ADR and set it to true.

**Why this cannot ship alone.** `collect_llm_targets` (bin/adr-judge:1119-1170) filters on `llm_judge`, Enforcement validity, Accepted status, retirement and a non-empty Decision. It never consults `path_glob` and never asks whether the staged diff touches the ADR's scope. Flipping 15 ADRs to true therefore means 15 isolated model calls on every commit, including a commit that only touches a README.

ADR-017 states the intended behaviour explicitly: "enabling `llm_judge` on an ADR costs one model call per commit **that touches its scope**, every time." The schema repeats it at schemas/adr-kit-config.schema.json:144. The code does not implement it. The scope filter is therefore part of this change, not a follow-up.

**Scope of work:**
- Default `llm_judge` to true where the key is absent, and change the schema default.
- Add scope filtering to `collect_llm_targets`: an ADR is only a target when the diff touches a file matching its Enforcement `path_glob` set. Decide and document what happens for an ADR whose Enforcement block has no glob at all (today a rule with no glob applies to every file).
- Migration that walks `docs/adr/` and sets `llm_judge: true` on every Accepted ADR, with a dry-run and a report of what it changed.
- Update the authoring path (skills/adr, agents/adr-generator, templates) so new ADRs are born with true.
- Regenerate the codex/ and copilot/ mirrors.
- Docs: CHANGELOG, README, RELEASING if relevant, and the config schema description.

**Open question for the maintainer, flagged not decided:** the six rule-less Enforcement blocks. Setting `llm_judge: true` on them turns six blocks that enforce nothing into six model calls per in-scope commit, judging decisions that may have no code surface at all (ADR-012 is a release runbook, ADR-013 a version registry). Those may deserve an explicit "no code surface" note instead.</description>
<parameter name="acceptanceCriteria">["An Enforcement block that omits `llm_judge` is treated as true by bin/adr-judge, and the schema default agrees", "The LLM pass only targets an ADR when the staged diff touches a file matching that ADR's Enforcement path_glob set; a commit outside every scope makes zero model calls", "The no-glob case is decided deliberately and documented: an ADR whose Enforcement block declares no path_glob does not silently become a call on every commit", "A migration command walks docs/adr/ and sets llm_judge:true on every Accepted ADR, supports a dry run, and reports each file it changed", "New ADRs from the authoring path (skills/adr, agents/adr-generator, template) are born with llm_judge:true", "codex/ and copilot/ mirrors regenerated and the adapter drift check is clean", "Cost is stated honestly where a maintainer will read it: with N opted-in ADRs, a commit touching M distinct scopes makes M calls, not N"]
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An Enforcement block that omits `llm_judge` is treated as true by bin/adr-judge, and the schema default agrees
- [x] #2 The LLM pass only targets an ADR when the staged diff touches a file matching that ADR's Enforcement path_glob set; a commit outside every scope makes zero model calls
- [x] #3 The no-glob case is decided deliberately and documented: an ADR whose Enforcement block declares no path_glob does not silently become a call on every commit
- [x] #4 The upgrade enables llm_judge on every Accepted ADR by default; the user is shown what will change and given the chance to opt out, per ADR and for the whole set at once
- [x] #5 Opting out is remembered: an ADR the user explicitly declined keeps llm_judge:false and is not re-proposed on the next upgrade
- [x] #6 The per-ADR prompt shows that ADR's Decision and its current Enforcement block, so the opt-out decision is made with the text in front of the user
- [x] #7 A non-interactive run (CI, no TTY) applies the opt-out default, meaning it enables, and prints exactly which ADRs it enabled so the change is auditable after the fact
- [x] #8 The upgrade is idempotent: re-running it changes nothing and says so
- [x] #9 New ADRs from the authoring path (skills/adr, agents/adr-generator, template) are born with llm_judge:true
- [x] #10 codex/ and copilot/ mirrors regenerated and the adapter drift check is clean
- [x] #11 Cost is stated honestly where a maintainer will read it: with N opted-in ADRs, a commit touching M distinct scopes makes M calls, not N
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Maintainer refinement (2026-08-01): the migration must ASK interactively per ADR rather than flipping the whole set. Walk every ADR, show its Decision and current Enforcement block, and let the user choose. A blind mass-flip would turn six rule-less blocks into six recurring model calls over decisions that may have no code surface at all, which is exactly the judgement a human should make once, per ADR, with the text in front of them.

Maintainer refinement 2 (2026-08-01): the upgrade is OPT-OUT, not opt-in. Enable llm_judge on everything by default and give the user the chance to switch it off, per ADR and for the whole set. This supersedes the earlier note's framing of an ask-per-ADR gate: the question is still asked and the text is still shown, but the default answer is yes and silence means enabled.

Consequence to keep visible: with opt-out defaults, the scope filter stops being an optimisation and becomes load-bearing. Without it, a repo that upgrades gets one model call per Accepted ADR on every single commit.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Flipped the llm_judge default to true, made scope the thing that bounds cost, and migrated this repository's own ADRs opt-out style.

**Root cause of the empty population.** The MADR scaffold at templates/adr-template.md shipped a rule-less Enforcement block ending in `"llm_judge": false`, and `bin/adr new` copies the template verbatim. ADR-006 and ADR-014 still carry that block byte-identically. The one instruction anywhere that could set it true (agents/adr-generator.md:163) frames it as a "downgrade" from declarative rules, and it sits on a path the guided authoring contract does not traverse: /adr-kit:adr routes propose -> grill -> accept, and skills/grill never mentions Enforcement at all. Nothing downstream corrects it either -- adr-quality never reads the block, adr-lint's policy gate only iterates rules that already exist and is not in the default gate set, and the schema has no top-level required or minProperties. So a default-on LLM pass shipped over a population that the scaffold guaranteed would be empty.

**Engine.** `llm_judge` now defaults to true where the key is absent; only an explicit false opts out. `collect_llm_targets` takes the diff's post-image paths and drops any ADR the diff does not touch, recording it in the --json attestation as "diff does not touch this ADR's scope" rather than silently. An Enforcement block with no rules, or a rule without a path_glob, has no boundary and is judged everywhere -- the same semantics `path_matches` already gives a rule with no glob, chosen deliberately by the maintainer.

**Memory for opt-outs.** New optional key `llm_judge_reason`. A bare false is a leftover from the old default and gets re-proposed; a reasoned false is a decision and is left alone forever. Both validators and the schema accept it, and a reason without an explicit false is flagged as meaningless.

**Migration.** `bin/adr-migrate --enable-llm-judge` with --dry-run, --except/--reason, --force-enable and --format json. A rule-less block is proposed as no-code-surface instead of becoming a call on every commit. /adr-kit:upgrade step 4b runs the scan, shows each Decision with its rule count and whether it has a scope, and asks before applying.

**Applied to this repo, with the maintainer choosing accept-as-proposed:** 9 ADRs enabled (005, 007, 008, 009, 010, 011, 015, 016, 017), each with a real path_glob; 6 rule-less ones (002, 004, 006, 012, 013, 014) marked no-code-surface with a reason; 001 and 003 untouched as Superseded. Re-running reports "Nothing to change".

**Verified on real diffs.** A diff touching only bin/adr-judge targets exactly ADR-017 and skips 8 as out of scope. A diff touching only README.md targets nothing and makes no call at all. Enforcement coverage is now 60% with 15 of 15 blocks valid.

Gates: 1247 passed / 11 skipped, adapter drift clean, adr-lint --strict clean, adr-index --check clean, retrieval probes 2/2 pass after regenerating the graph the migration made stale.

Two contract tests encoded the old expectations and were updated rather than worked around: the canonical template must now NOT ship llm_judge, and the "no targets" test now uses an explicit false plus a reason, since omitting the key no longer means opted out.</finalSummary>
<notesAppend">["Not done, flagged for the maintainer: this change alters the cost model ADR-017 argued for. ADR-017's Consequences lean on llm_judge being per-ADR and defaulting to FALSE, so that a default-on pass over an empty population costs nothing. That bound is now the scope filter instead of the flag. A successor ADR (or an amendment) should record the new reasoning, otherwise ADR-017 documents a safety property the code no longer has."]</notesAppend>
<!-- SECTION:FINAL_SUMMARY:END -->
