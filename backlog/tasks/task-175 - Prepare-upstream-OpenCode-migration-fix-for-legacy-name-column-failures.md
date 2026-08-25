---
id: TASK-175
title: Prepare upstream OpenCode migration fix for legacy name-column failures
status: Done
assignee: []
created_date: '2026-08-16 20:33'
updated_date: '2026-08-25 23:25'
labels:
  - opencode
  - upstream
  - sqlite
  - migration
dependencies: []
references:
  - 'https://github.com/anomalyco/opencode/issues/40470'
  - 'https://github.com/anomalyco/opencode/issues/32430'
  - 'https://github.com/anomalyco/opencode/pull/37707'
  - 'https://github.com/anomalyco/opencode/pull/41610'
priority: high
type: bug
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate and, if necessary, improve the upstream OpenCode fixes for startup failures reporting no such column: name. Cover both legacy __drizzle_migrations journals and legacy workspace tables, avoid duplicating an existing upstream fix, and offer a tested contribution upstream.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The legacy Drizzle journal path no longer queries a missing name column and maps known created_at entries safely.
- [ ] #2 The workspace-name migration preserves existing names and defaults missing legacy names without querying a missing column.
- [ ] #3 Focused migration tests and relevant Windows checks pass.
- [x] #4 The upstream contribution clearly references existing PRs #37707 and #41610 and does not duplicate accepted work.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: OpenCode
created: 2026-08-16 20:35
---
Decision 2026-08-16: do not create a duplicate PR. Existing PR #37707 covers legacy Drizzle journals without a name column, and PR #41610 covers the legacy workspace-name migration. Their focused migration tests are reported passing; the overall Windows check on #41610 failed in an unrelated app UI test. Local Windows reproduction evidence was posted to both PRs. Task remains In Progress pending upstream maintainer action.
---

author: Claude
created: 2026-08-25 23:01
---
VERIFICATIE 2026-08-26 — NIET AFSLUITBAAR OP HET 'CODE IN MAIN'-CRITERIUM, en de upstream-stand is veranderd sinds het besluit van 2026-08-16.

Deze taak wijzigt per ontwerp niets in adr-kit: de beslissing van 2026-08-16 was 'geen duplicaat-PR maken, bewijs op de bestaande PR's posten'. Er is dus geen commit die in `main` kan landen. `main` als criterium is hier niet van toepassing.

UPSTREAM-STAND, opgehaald 2026-08-26 (repo `sst/opencode`; `anomalyco/opencode` redirect daarheen):

| Ref | Titel | Stand |
|---|---|---|
| PR #37707 | fix(core): import legacy drizzle migration journals without a name column | **CLOSED**, `mergedAt: null` — gesloten zonder merge |
| PR #41610 | fix(core): tolerate missing workspace names | **OPEN** |
| Issue #40470 | [BUG]: Blank TUI hides legacy migration error on 1.18.11 | CLOSED 2026-08-04 |
| Issue #32430 | Desktop upgrade can fail on workspace migration | CLOSED 2026-08-14 |

WAT DIT BETEKENT VOOR DE ACs:
- AC#1 (legacy Drizzle-journal-pad) hing op PR #37707. Die is **gesloten zonder merge**. Het record zei 'pending upstream maintainer action'; die actie is inmiddels genomen en luidt: niet gemerged. Of het onderliggende probleem langs een andere weg is opgelost — issue #40470 is wel gesloten — is niet nagegaan.
- AC#2 (workspace-name-migratie) hangt op PR #41610, nog steeds OPEN. Onveranderd wachtend.
- AC#3 en AC#4 zijn upstream-eigenschappen van diezelfde PR's.

AANBEVELING AAN DE MAINTAINER, niet zelf uitgevoerd: dit is geen adr-kit-werk meer en de enige resterende afhankelijkheid is één open PR in een vreemde repo. Twee redelijke uitkomsten: (a) sluiten als 'bijgedragen, upstream beslist', met de tabel hierboven als eindstand, of (b) open houden puur als wachtpost op #41610. De keuze is aan jou.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GESLOTEN op 2026-08-26 als "bijgedragen, upstream beslist", op beslissing van de maintainer.

WAT DEZE TAAK WEL HEEFT OPGELEVERD — AC#4, geverifieerd, niet aangenomen. Op beide upstream-PR's staat een comment van `rvdbreemen` d.d. 2026-08-16 met Windows-reproductiebewijs ("Additional Windows reproduction evidence: OpenCode Desktop 1.18.18 logged a fatal renderer error, no such column: name, immediately after its sidecar exited..."). Opgehaald met `gh pr view <n> --repo sst/opencode --json comments`. De bijdrage refereert dus aantoonbaar aan de bestaande PR's en dupliceert geen aanvaard werk — precies wat AC#4 eist. Afgevinkt.

De beslissing van 2026-08-16 was bewust: geen duplicaat-PR aanmaken, wel bewijs leveren waar het werk al liep. Achteraf de juiste keuze — een vierde PR had het beeld alleen vertroebeld.

WAT DEZE TAAK NIET HEEFT OPGELEVERD — AC#1, #2 en #3 blijven ongevinkt. Dat zijn eigenschappen van code in een vreemde repository; adr-kit heeft ze nooit in de hand gehad.

UPSTREAM-EINDSTAND, opgehaald 2026-08-26 (`sst/opencode`; `anomalyco/opencode` redirect daarheen):

| Ref | Titel | Stand |
|---|---|---|
| PR #37707 | fix(core): import legacy drizzle migration journals without a name column | CLOSED, `mergedAt: null` — gesloten zonder merge |
| PR #41610 | fix(core): tolerate missing workspace names | OPEN |
| Issue #40470 | [BUG]: Blank TUI hides legacy migration error on 1.18.11 | CLOSED 2026-08-04 |
| Issue #32430 | Desktop upgrade can fail on workspace migration | CLOSED 2026-08-14 |

Het record zei "pending upstream maintainer action". Die actie is inmiddels genomen op #37707 en luidt: niet gemerged. Of het onderliggende journal-probleem langs een andere weg is opgelost — issue #40470 is wel gesloten — is niet nagegaan; dat viel buiten deze verificatie.

WAAROM SLUITEN JUIST IS. Er is geen commit die ooit in adr-kit's `main` kan landen; deze taak wijzigt per ontwerp niets in deze repo. De enige resterende afhankelijkheid is één open PR van iemand anders in een vreemde repo. Een backlog-taak openhouden als wachtpost op andermans review geeft geen signaal dat iemand hier kan lezen of beïnvloeden.

ALS HET PROBLEEM TERUGKEERT: het is een OpenCode-startfout ("no such column: name") bij een legacy SQLite-migratie, niet een ADR Kit-fout. Comment #1 op dit record beschrijft de diagnose, en de lokale `opencode.db` liet zich herbouwen (2026-08-13T21:57:43Z). Nieuwe aanleiding = nieuwe taak, met #41610 als startpunt.
<!-- SECTION:FINAL_SUMMARY:END -->
