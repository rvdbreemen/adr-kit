---
id: TASK-198
title: >-
  Completeness accepts an empty required section, so a migration can make a
  hollow ADR pass the gate
status: Done
assignee:
  - '@claude'
created_date: '2026-09-06 08:17'
updated_date: '2026-09-06 13:49'
labels:
  - bug
  - lint
  - migrate
dependencies: []
priority: high
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
gate_completeness() in bin/adr-lint tests only whether a required heading matches somewhere in the text; it never looks at whether the section has a body. The /adr-kit:lint contract says a passing ADR has every load-bearing section 'with non-empty content', so implementation and specification disagree. This is not cosmetic: bin/adr accept runs the gate with --strict and refuses acceptance when it fails, so an empty heading is enough to walk an ADR into an immutable Accepted state with no verifiable reference.

Measured, not inferred. Two copies of the same ADR, differing only in the References section:
  section present but empty  -> completeness reports NO failure
  section absent             -> completeness FAIL: missing sections: ['References']

Second, related gap on the migrate side. adr-migrate --to-profile does NOT insert an empty section; _append_missing_role writes a visible placeholder, for example '- TODO: add verifiable references.'. That is honest at write time, but it counts as content, so the record passes completeness immediately and nothing stops adr accept from accepting an ADR whose References section still says TODO. The migrate output does not mention that placeholders were inserted either, so an operator running it has no signal that the record is unfinished.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 gate_completeness reports a required section that exists but has no body as missing, and the reason distinguishes absent from empty
- [x] #2 A subheading counts as content, so '## Consequences' followed by '### Positive' keeps passing
- [x] #3 adr-migrate does not silently create an empty required section; it either declines or marks the result as needing content, and the operator can tell from its output
- [x] #4 Regression test covers both an absent section and a present-but-empty one
- [x] #5 adr-migrate names the sections it filled with a placeholder, so the operator can see the record is unfinished
- [x] #6 A required section whose only content is an adr-kit TODO placeholder does NOT fail a blocking gate; adr-migrate reports it as needing content instead, so the operator is told without the import being refused
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Beide helften gefixt, met gemeten bewijs.

LINT (bin/adr-lint). gate_completeness kijkt nu naar de body tussen het kopje en de volgende H2, niet alleen naar het kopje. Leeg telt als ontbrekend, en een sectie waarvan elke regel een TODO-placeholder is ook. De melding onderscheidt de twee: References tegenover References (present but empty), zodat een auteur ziet of hij iets nooit schreef of de placeholder liet staan.

MIGRATE (bin/adr-migrate plus adr_format.unfilled_required_sections). Een conversie die een ontbrekend kopje toevoegt schrijft daar een TODO in. Dat werd stilzwijgend gedaan. adr-migrate meldt nu per bestand "needs content: ## <sectie>" en sluit af met de reden, en telt alleen wat DEZE run oningevuld liet, zodat een gat dat de auteur al had niet aan de migratie wordt toegeschreven.

CORRECTIE op de oorspronkelijke beschrijving. Ik meldde eerst dat adr-migrate een LEGE sectie invoegt. Dat klopte niet en het lag aan mijn eigen diff-filter: grep -v "^[+-][+-]" verwijdert naast bestandskoppen ook elke toegevoegde regel die met een streepje begint, dus elke markdown-bullet. De placeholder stond er wel degelijk. In een schone reproductie kwam er - TODO: add verifiable references. uit.

REGRESSIEMETING. Eerst leek de fix 110 ADRs om te gooien op de OTGW-corpus (177 ADRs). Dat was een vergelijking tussen de geinstalleerde 0.56.0 en dev HEAD, niet mijn wijziging. Met dezelfde binary ervoor en erna: 31 PASS / 114 ADVISORY / 32 FAIL, identiek. Nul regressie. Op de eigen corpus van adr-kit: 42 PASS, 0 FAIL, ook identiek.

TESTS. Twee fixtures (empty-section, placeholder-section) plus drie tests in test_adr_lint.py en twee in test_selectable_formats.py, waaronder een die controleert dat een volledig ingevuld record geen vals alarm geeft. Gericht: 23 en 29 passed. Volledige suite draait.

End-to-end op de oorspronkelijke casus (OTGW ADR-170, References ontbrak): migratie meldt needs content, lint faalt daarna met References (present but empty). Voorheen: migratie zweeg en lint gaf PASS strictly.

DERDE VINDPLAATS gevonden en gefixt: adr_quality_core.gate_completeness. Dezelfde sectie-lus met alleen pattern.search(). Het veelzeggende detail is dat diezelfde functie drie regels lager wel op leegte controleert, voor Decision, Alternatives en Consequences. References en Related Decisions vielen door dat gat, en adr accept --quality-threshold rekent met die score. Gemeten op de empty-section fixture: completeness 0.90 naar 0.76 met "Required section missing: References". De Evidence-gate van hetzelfde gereedschap meldde al "References section is empty", dus twee helften van een tool spraken elkaar tegen over hetzelfde record.

CHANGELOG-regel toegevoegd onder Unreleased, Fixed, voor beide helften.

Client-adapters geregenereerd (changed=2) en geverifieerd met --check (changed=0). codex/ en copilot/ nooit met de hand aangeraakt.

Tests: 95 passed over test_adr_quality, test_adr_lint, test_selectable_formats, test_adr_migrate en test_release_allowlist.

NIET gedaan: de volledige suite. Twee pogingen zijn door het besturingssysteem afgebroken wegens geheugen (commit charge 88 van 93 GB), dus er is geen uitslag in plaats van een groene. CI is de gate.

PR: https://github.com/rvdbreemen/adr-kit/pull/146 naar dev.

- CI on PR #146 rejected the placeholder half of the fix. Two tests already encoded the opposite policy: test_adr_policy.py::test_neither_migration_placeholder_spelling_counts_as_an_option and test_migration_discovery.py both assert that an imported record must NOT fail a blocking gate on arrival, "which is how a migrating team learns to disable the gate".
- AC #5 as originally written was therefore a policy change, not a bug fix. Rewrote it to state the decision; the emptiness half of the fix stands unchanged.
- c476525 narrows _is_unfilled to emptiness only in bin/adr-lint and bin/adr_quality_core.py and drops _PLACEHOLDER_LINE_RE from both. adr_format.unfilled_required_sections keeps placeholder awareness: that surface reports, it does not gate.
- Commit needed ADR_KIT_NO_LLM=1: two attempts were killed by the OS for memory (commit charge 70.6 of 78.4 GB). Declarative adr-judge pass ran, 20 ADRs, 0 violations.
- PR #146 all 12 checks green and MERGEABLE. Merge to dev is the maintainer action (enforce_admins: true).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A heading on its own is not a section. Three tools shared that hole and the migrator could open it in one command.

Changes:
- `bin/adr-lint` reads the body between a required heading and the next H2. A section with nothing under it is reported as missing, and the finding separates the two cases (`References` vs `References (present but empty)`).
- `bin/adr_quality_core.py` carried the same loop. It already measured emptiness for Decision, Alternatives and Consequences three lines below, so References and Related Decisions fell through a gap in the same function. `adr accept --quality-threshold` reads that score; on the empty-section fixture it moves 0.90 -> 0.76.
- `bin/adr-migrate` names the sections it filled with a placeholder as `needs content: ## <heading>`, counting only what that run left unfilled so a pre-existing hole is not blamed on the migration. The shared rule lives once, in `adr_format.unfilled_required_sections`, whose only caller is `bin/adr-migrate`: it reports, it never gates.

Correction, and the reason the placeholder criterion was rewritten (it is AC #6, not #5; removing the old #5 shifted the list): the first version also treated a `- TODO:` placeholder as a hole. CI rejected it and CI was right. `test_adr_policy.py` and `test_migration_discovery.py` already decided that an imported record must not fail a blocking gate on arrival, "which is how a migrating team learns to disable the gate". That made the placeholder rule a policy change wearing a bugfix's clothes. `c476525` narrows `_is_unfilled` to emptiness only in both blocking gates and drops `_PLACEHOLDER_LINE_RE` from them. The two placeholder tests now assert that policy, so a future tightening trips over the decision instead of silently reversing it.

What this closes, measured on `docs/adr/ADR-042` copied into a scratch directory with the whole ADR set as context:
- `## References` emptied: the acceptance gate set (`--strict`, all seven gates, the exact set `bin/adr accept` runs) now blocks with `missing sections: ['References (present but empty)']`. Before this branch it passed.
- `## References` holding only `- TODO: add verifiable references.`: still passes, and `adr-quality` scores it 0.87 grade A with completeness 1.0. That path is deliberately left open at arrival, and it is filed as TASK-199, which proposes reporting it at readiness/grill rather than in completeness.

Regression: none. Downstream corpus of 177 ADRs (OTGW-firmware) 31 PASS / 114 ADVISORY / 32 FAIL, identical before and after; this repository's own `docs/adr` 42 PASS / 0 FAIL, identical. An earlier reading of mine claiming 110 ADRs would flip compared installed 0.56.0 against `dev` and was wrong.

Tests: two fixtures (`empty-section`, `placeholder-section`) plus cases in `test_adr_lint.py`, `test_adr_quality.py` and `test_selectable_formats.py`. Locally 232 passed across thirteen files; the full suite has no local verdict because two attempts were killed by the OS for memory. CI is the gate and PR #146 was green on all twelve checks, six platform/version combinations included.

Note on the commits: `c476525` needed `ADR_KIT_NO_LLM=1` after two attempts were killed for memory (commit charge 70.6 of 78.4 GB). The declarative adr-judge pass did run: 20 ADRs with Enforcement blocks, 0 violations, 0 advisory. No `--no-verify`.

Not landed: PR #146 is MERGEABLE but unmerged. `dev` has `enforce_admins: true`, so merging is the maintainer's action, not mine.
<!-- SECTION:FINAL_SUMMARY:END -->
