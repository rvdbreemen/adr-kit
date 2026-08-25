---
id: TASK-187
title: >-
  ADR-029 is niet uitgevoerd: de native hook-binary shipt nog en de gate
  certificeert de verworpen optie
status: In Progress
assignee:
  - '@claude'
created_date: '2026-08-23 21:41'
updated_date: '2026-08-24 05:58'
labels:
  - adr
  - governance
  - hooks
  - adr-029
dependencies: []
references:
  - >-
    docs/adr/ADR-029-retire-the-native-hook-binary-rather-than-maintain-a-second-retrieval-engine.md
  - docs/adr/ADR-015-declare-a-latency-budget-per-hook-event.md
  - >-
    backlog/completed/task-127 -
    Flip-gate-and-binding-back-to-true-as-each-ADR-020..029-implementation-ships.md
  - tests/test_adr_hook_dispatch_matrix.py
modified_files:
  - hooks/bin/windows-x64/adr-hook.exe
  - codex/hooks/bin/windows-x64/adr-hook.exe
  - copilot/hooks/bin/windows-x64/adr-hook.exe
  - hooks/native/adr-hook.rs
  - hooks/native/windows-process-floor.rs
  - hooks/run-hook.cmd
  - hooks/hook_benchmark.py
  - tests/test_adr_hook_dispatch_matrix.py
  - >-
    docs/adr/ADR-029-retire-the-native-hook-binary-rather-than-maintain-a-second-retrieval-engine.md
priority: high
type: bug
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-029 "Retire the Native Hook Binary Rather Than Maintain a Second Retrieval Engine" is Accepted sinds 2026-08-04 en `binding: true`. De Must luidt: "Remove the native host, its committed artefact, and the dispatcher branch that prefers it." Niets daarvan is gebeurd, en het is niet zichtbaar in enige poort.

STAND OP v0.54.0, GEVERIFIEERD 2026-08-23:

* `hooks/bin/windows-x64/adr-hook.exe` is git-tracked in drie trees (`hooks/`, `codex/hooks/`, `copilot/hooks/`), samen 776 KB.
* De release-commit van v0.54.0 (`6f6656c`, 2026-08-20) heeft de binary **herbouwd**, niet verwijderd: 248320 → 258560 bytes.
* `hooks/native/adr-hook.rs` en `hooks/native/windows-process-floor.rs` bestaan nog.
* De dispatcher-branch staat er nog: `hooks/run-hook.cmd:16` (cmd) en `:52` (sh), plus `hooks/hook_benchmark.py:28-39`.
* Geen open backlog-taak dekt de verwijdering. Gezocht op "native hook", "ADR-029", "retire binary" en op modifiedFiles `hooks/bin` / `hooks/native`.

WAAROM DIT ERGER IS DAN EEN VERGETEN OPRUIMING: de gate is groen en certificeert de optie die de ADR expliciet verwierp. `tests/test_adr_hook_dispatch_matrix.py:25` zegt "Verified here: one retrieval engine: the native host runs only under ADR_KIT_NATIVE_HOOK=1". ADR-029 wijst die stand met zoveel woorden af onder "Why not decide later": "Opt-in is where v0.44.1 left it, and it is a stable resting place — nothing is broken. But an artefact that ships, cannot be trusted and is nobody's job decays into precisely the state this ADR is written about: last rebuilt two releases ago, diverging in ways only a comparison run reveals."

De frontmatter is wel eerlijk (`documents_shipped: false`, `verified_in: []`), maar `binding: true` plus een resolveerbare gate maakt `adr-lint` groen. Voor een tool die drift hoort te vangen is dat de duurste soort fout: de poort meldt naleving van een beslissing die niet genomen is uitgevoerd.

PREMISSE DIE NIET KLOPT: TASK-127 (Done) besluit met "The remaining seven had shipped implementations and were missing only the anchor string, so each anchor now lives in the test that actually verifies that decision." Voor ADR-029 is die premisse onjuist — er was geen geshipte implementatie, alleen een anchor. Corrigeer dat record als onderdeel van deze taak.

DE VORK DIE EEN UITVOERDER MOET KENNEN: er zijn twee legitieme uitkomsten en precies één illegitieme.

1. ADR-029 uitvoeren zoals aanvaard: binary, Rust-bron, dispatcher-branch en benchmark-tak weg, Python is het enige pad. Kosten zijn in de ADR gemeten: SessionStart gaat van 21 ms naar 235 ms mediaan, binnen het 500 ms-budget van dat event; de edit-tier op 100 ms is de krappe.
2. De beslissing terugdraaien. Dat mag, maar alleen door supersessie met een nieuwe ADR, niet door stil niet-uitvoeren. ADR-029 beschrijft de weg terug zelf onder "If the latency proves unacceptable": een native pad herstellen betekent `bin/adr_query.py` porten, niet `adr-hook.rs` patchen, en het vraagt een pariteitstest op artefactniveau die de binary draait in plaats van de bron leest.
3. Niet legitiem: de huidige toestand laten staan met een groene gate.

De keuze tussen 1 en 2 is aan de maintainer. Voer 1 uit tenzij hij anders beslist.

CONTEXT DIE ANDERS VERLOREN GAAT: de binary was aantoonbaar onjuist, niet alleen ongetest. Gemeten tegen de Python-oracle gaf hij 1 van 4 governing ADR's terug op een edit-event en 0 van 1 op `ExitPlanMode`. De pariteitstest die dat had moeten vangen, `tests/test_adr_hook_result_limit.py`, las een constante uit `adr-hook.rs` in plaats van de binary te draaien, en slaagde dus over een twee releases oude build.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 hooks/bin/windows-x64/ is verwijderd uit alle drie de trees (hooks/, codex/hooks/, copilot/hooks/) en geen adr-hook.exe is nog git-tracked
- [ ] #2 hooks/native/ is verwijderd, inclusief adr-hook.rs en windows-process-floor.rs
- [ ] #3 De native dispatcher-branch is weg uit hooks/run-hook.cmd (zowel de cmd- als de sh-helft) en uit hooks/hook_benchmark.py; ADR_KIT_NATIVE_HOOK komt nergens meer voor
- [ ] #4 Elk manifest-event levert op elke client dezelfde records als vandaag via het Python-pad, op Windows zowel als POSIX
- [ ] #5 De edit-tier events zijn gemeten tegen hun 100 ms-budget via het fixture-contract van ADR-015 en de meting is meegecommit
- [ ] #6 De gate-anchor in tests/test_adr_hook_dispatch_matrix.py beweert wat ADR-029 werkelijk besliste, niet dat de native host onder een env-vlag draait; de gate faalt als een tweede retrieval-implementatie terugkeert
- [ ] #7 ADR-029 frontmatter documents_shipped en verified_in weerspiegelen de werkelijke stand na afloop
- [ ] #8 TASK-127 is gecorrigeerd op het punt dat ADR-029 een geshipte implementatie zou hebben gehad
- [ ] #9 Als de maintainer kiest voor terugdraaien in plaats van uitvoeren, gebeurt dat via een superseding ADR en niet door deze taak te sluiten met de binary intact
- [ ] #10 python -m pytest -q slaagt volledig
- [ ] #11 python scripts/build-client-adapters.py --check meldt changed=0
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Branch `fix/retire-native-hook-and-jsonrpc-hygiene`, afgetakt van `release/v0.54.0` (de enige tip die alle release-commits bevat; `origin/dev` mist v0.52.1..v0.54.0). Elke regelverwijzing in dit record is tegen die tree geverifieerd.

## Onderzoek: de sweep is breder dan het record beschreef

Een uitputtende grep op `ADR_KIT_NATIVE_HOOK`, `adr-hook.exe`, `hooks/bin/` en `hooks/native` leverde vier vindplaatsen op die bij het aanmaken niet in beeld waren:

1. `copilot/hooks.json` roept de exe aan in drie PowerShell-handlers. Dat is een **gegenereerd** artefact; de bron is `scripts/client_generation_artifacts.py:207-212`.
2. `bin/adr_doctor_checks.py:191-216` heeft een doctor-check die de exe als *required file* eist.
3. `tests/test_adr_hook_result_limit.py` leest `hooks/native/adr-hook.rs` op drie plaatsen (regels 44, 150, 183). Dit is precies de pariteit-uit-broncode die ADR-029 onder Must Not verbiedt.
4. `.npmignore:17-19` sluit `hooks/bin/` en `hooks/native/` uit van het npm-pakket.

**Pivotale vondst:** `scripts/client_generation.py:268` laat de orphan-sweep `/hooks/bin/` expliciet overslaan:
`if "/hooks/bin/" in f"/{relative}" or relative in expected_set: continue`
Alleen de entry uit `client_generation_model.py:50` halen ruimt de kopieen dus **niet** op. Die uitzondering moet mee weg, anders houdt de driftcontrole een permanente blinde vlek op precies het pad dat we opheffen.

## Scope-lijn

IN: alles wat code, config, tests of de verzonden payload is, plus levende gebruikersdocumentatie die de gebruiker een env-vlag aanraadt die niet meer bestaat.

UIT, en waarom: `CHANGELOG.md` en de Context-secties van ADR-029/ADR-030 zijn historische vastlegging en worden niet herschreven. `C4-Documentation/*` zijn gedateerde architectuurrapporten uit een skill-run; die volgen bij hun eigen regeneratie. Dit is een routinematige afbakening binnen AC#3 ("komt nergens meer voor" slaat op de werkende boom), geen scopewijziging.

## Stappen

1. `git rm -r` op `hooks/bin/windows-x64/`, `codex/hooks/bin/`, `copilot/hooks/bin/` en `hooks/native/`.
2. Canoniek bewerken: `hooks/run-hook.cmd` (cmd-tak regels 6+12-19, sh-tak regels 38-55 inclusief de nu doelloze ARCH/OS-detectie), `hooks/hook_benchmark.py` (`host_command` houdt alleen het Python-pad; de tweede tupelwaarde blijft bestaan voor de bestaande callers), `scripts/client_generation_artifacts.py` (PowerShell-tak weg), `scripts/client_generation_model.py:50` (entry weg), `scripts/client_generation.py:268` (uitzondering weg), `bin/adr_doctor_checks.py` (native-check weg), `.npmignore`, `docs/hook-performance.md:52`.
3. Tests: de drie Rust-pariteitstests uit `tests/test_adr_hook_result_limit.py`; de anchor-comment en assertions in `tests/test_adr_hook_dispatch_matrix.py:25,282-284`; `tests/test_client_adapter_generation.py:369-387`; `tests/test_hook_performance.py:65-96`. De gate-anchor gaat beweren wat ADR-029 werkelijk besliste: er is geen tweede retrieval-implementatie, en de dispatcher kent geen native tak.
4. Eenmalig `python scripts/build-client-adapters.py`, daarna `--check` (verwacht `changed=0`).
5. Edit-tier meten tegen het 100 ms-budget via het fixture-contract van ADR-015 en de meting meecommitten.
6. ADR-029 frontmatter bijwerken; TASK-127 corrigeren.
7. `python -m pytest -q` volledig, daarna `/adr-kit:judge`.

## Risico

De grootste is een half uitgevoerde sweep: een record dat gecorrigeerd en verouderd tegelijk is, is moeilijker te herkennen dan een volledig verouderd record. Sluitstuk daarom een grep op `ADR_KIT_NATIVE_HOOK` en `hooks/native` over de werkende boom, met alleen de bewust-historische treffers over.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
CORRECTIE OP TASK-127 (AC#8). Het afgeronde record is niet bewerkbaar: zowel `task_edit` als `backlog task edit 127` antwoordt "Task not found", terwijl `backlog task 127 --plain` het wel leest. De repo kent hier een eigen precedent - TASK-127 corrigeerde zelf backlog task-100 door de correctie in het corrigerende record te schrijven, niet in het foute. Diezelfde vorm hier.

WAT ER NIET KLOPT. TASK-127's Final Summary zegt: "The remaining seven had shipped implementations and were missing only the anchor string, so each anchor now lives in the test that actually verifies that decision." Voor ADR-029 was er geen geshipte implementatie. Op 2026-08-05, toen `gate` en `binding` werden omgezet, stond `hooks/bin/windows-x64/adr-hook.exe` nog in alle drie de trees, bestond `hooks/native/adr-hook.rs`, en droeg `hooks/run-hook.cmd` de native dispatcher-tak. De release-commit van v0.54.0 (6f6656c, 2026-08-20) herbouwde de binary daarna nog: 248320 -> 258560 bytes.

WAAROM NIEMAND HET ZAG. De anchor die TASK-127 schreef beweerde de verworpen optie: `tests/test_adr_hook_dispatch_matrix.py:25` las "Verified here: one retrieval engine: the native host runs only under ADR_KIT_NATIVE_HOOK=1". Dat is precies de opt-in-stand die ADR-029 onder "Why not decide later" afwijst. De gate resolveerde, `binding: true` hield stand, `adr-lint` bleef groen, en een aanvaarde bindende beslissing bleef 20 dagen onuitgevoerd terwijl de tooling naleving meldde.

WAT DIT SCHERPT IN PLAATS VAN TEGENSPREEKT. TASK-127's AC#2-check toetst of een gate-naam RESOLVEERT, nooit of de anchor beweert wat de ADR besliste. Dat zijn verschillende eigenschappen en alleen de eerste is mechaniseerbaar. `documents_shipped: false` en `verified_in: []` waren de hele tijd eerlijk; dat was het beschikbare signaal en niets las het.

NIET GECONTROLEERD: de andere zes records uit de ADR-020..029-sweep die volgens dezelfde zin "shipped implementations" hadden. Dezelfde kloof kan daar bestaan.

AFWIJKINGEN BUITEN DE AC, met reden. Vastgelegd voor de commit, zodat een reviewer ze als keuze ziet en niet als ruis.

NOODZAKELIJK (zonder deze breekt de build of liegt een poort):
1. `bin/adr_doctor_checks.py` - de doctor eiste `adr-hook.exe` als *required file*. Na verwijdering zou elke gezonde installatie 'failed' melden.
2. `scripts/client_generation_model.py` + `scripts/client_generation.py` - de exe stond in de kopieerlijst, en de orphan-sweep sloeg `/hooks/bin/` expliciet over. Alleen het eerste weghalen laat de kopieen staan; alleen het tweede laten staan houdt een permanente blinde vlek op het pad dat we opheffen.
3. `scripts/client_generation_artifacts.py` -> `copilot/hooks.json` - de gegenereerde PowerShell-handlers riepen de exe aan.
4. Vier testbestanden die de exe of `adr-hook.rs` lazen: `test_adr_hook_result_limit.py` (drie pariteit-uit-broncode-tests, precies wat ADR-029's Must Not verbiedt), `test_adr_auto_grill.py`, `test_adr_guardian_queue.py`, `test_hook_protocol.py`. Alle vier zouden crashen of permanent skippen.
5. `.npmignore` - excludes voor mappen die niet meer bestaan.
6. `docs/hook-performance.md` - noemde de native host het gecertificeerde Windows-pad en citeerde het 25/50/100 ms edit-budget dat ADR-030 al had vervangen.

EIGEN TOEVOEGING, niet door een AC gevraagd (drie stuks):
7. `test_client_adapter_generation.py`: de hash-gelijkheidsassertie op de drie exe-kopieen is vervangen door een rglob die `.exe/.dll/.so/.dylib/.pdb/.rs` in elke hooks-tree verbiedt. De `.rs` in die lijst is de toevoeging: zonder hem zou de Rust-bron kunnen terugkeren zonder gecompileerd artefact, en dat is nog steeds een tweede engine.
8. Dezelfde test: `len(handlers) == len(doc["hooks"])` in plaats van alleen `handlers` niet-leeg. Gevonden omdat mijn eerste versie faalde - de voorganger liep over `doc.values()` in plaats van `doc["hooks"]`, waardoor zijn per-handler-lus nooit iets vond. Alleen zijn blob-check deed werk. De telling maakt die stilte onmogelijk.
9. `test_release_allowlist.py`: het verboden-pad-voorbeeld `hooks/bin/windows-x64/adr-hook.pdb` is `bin/adr-hook.pdb` geworden. Dezelfde regel wordt getoetst, zonder een pad te noemen dat niet meer bestaat.

BEWUST NIET GEDAAN: `CHANGELOG.md`, de Context-secties van ADR-029/ADR-030 en `C4-Documentation/*` blijven ongemoeid. Historie en gedateerde rapporten worden niet herschreven.

AC#5 KAN NIET WORDEN AFGEVINKT ZOALS GESCHREVEN - premisse achterhaald. Blijft daarom open; ik wijzig de AC-tekst niet, want dat is een beslissing van de maintainer.

AC#5 luidt: "De edit-tier events zijn gemeten tegen hun 100 ms-budget via het fixture-contract van ADR-015 en de meting is meegecommit." Dat 100 ms-budget bestaat niet meer. Het komt uit ADR-029's tekst van 2026-08-04; ADR-030 "Recalibrate the Hook Latency Budgets to the Python Host That Actually Ships" (Accepted 2026-08-05, een dag later) heeft precies die budgetten vervangen, met als argument dat de interpreter-vloer van 182,6 ms alleen al boven 100 ms ligt en geen enkele optimalisatie binnen de hook ze ooit had kunnen halen. `hooks/manifest.json` geeft `pre-tool-use` nu 450 p50 / 550 p95 / 1100 hard.

WAT IK IN PLAATS DAARVAN HEB GEDAAN: gemeten tegen de budgetten die er wel zijn, 30 samples per event, method_id `adr-kit-hook-latency-v1`, procesopstart meegerekend. Vastgelegd in `docs/hook-performance.md` onder "Python-only measurement, 2026-08-24".

UITKOMST, eerlijk: elk event rapporteert host `python` - er is geen andere host meer om te rapporteren, en dat is de eigenschap die ADR-029 werkelijk eist. De edit-tier (`pre-tool-use` 303,4 p50 / 362,6 p95, `post-tool-use` 261,6 / 301,6, `plan-exit` 263,8 / 303,7) haalt elk doel met marge. Drie events missen op deze machine: `user-prompt-submit` (p95 627,7 tegen 450), `pre-compact` (p95 2117 tegen 1000) en `pr-create` (p50 4719 tegen 1500, 13 van 30 timeouts).

DIE DRIE MISSERS KOMEN NIET VAN DIT WERK, en dat is een codefeit, geen gevolgtrekking: `hooks/adr-hook.py`, `hooks/adr_hook_core.py` en `hooks/adapters/` zijn byte-ongewijzigd, en `host_command` gaf ditzelfde Python-commando al terug zodra `ADR_KIT_NATIVE_HOOK` niet gezet was - wat de default was. Het gemeten pad is het pad dat al shipte. Dit is bovendien een ontwikkelmachine die tegen de adr-kit-repo zelf meet (41 ADR's, grote werkboom), niet de verklaarde certificatierunner tegen het fixture-corpus. Certificering houdt het release-blokkerende oordeel; deze getallen zijn vastgelegd in plaats van weggepoetst.

AAN DE MAINTAINER: ofwel AC#5 herformuleren naar de ADR-030-budgetten en dan afvinken, ofwel een aparte taak voor een certificatierun op de verklaarde runner. Ik heb geen van beide zelf gedaan.

TESTRUN-HYGIENE. Een eerste volledige pytest-run (achtergrondtaak b29emgkf3) kreeg status 'killed' en het log toonde daarna 98 failures over volledig ongerelateerde modules (test_setup_project_command, test_managed_instructions, test_selectable_formats, test_template_profiles, test_otgw_corpus) - geen daarvan raakt bestanden die deze taak wijzigt. Dat patroon plus de 'killed'-status matcht het project-precedent 'Afgebroken testrun geeft valse failures' (CLAUDE.md, KennisBank-geheugen): een gekilde of gelijktijdige run produceert F-lawines die artefact zijn van de checkout, niet van de code. Dat log is verworpen zonder één van de 98 te 'fixen'. Herdraaid in isolatie (bg1mmm82g), zonder enig ander commando gelijktijdig tegen de repo, met eigen --basetemp en log-naar-bestand. Resultaat volgt in deze taak.
<!-- SECTION:NOTES:END -->
