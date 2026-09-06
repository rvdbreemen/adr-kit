---
id: TASK-198
title: >-
  Completeness accepts an empty required section, so a migration can make a
  hollow ADR pass the gate
status: In Progress
assignee:
  - '@claude'
created_date: '2026-09-06 08:17'
updated_date: '2026-09-06 13:12'
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
- [x] #5 A required section whose only content is an adr-kit TODO placeholder is reported as incomplete, so migrate output cannot be accepted unfilled
- [x] #6 adr-migrate names the sections it filled with a placeholder, so the operator can see the record is unfinished
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
<!-- SECTION:NOTES:END -->
