---
id: TASK-188
title: Release adr-kit v0.55.1
status: Done
assignee: []
created_date: '2026-08-26 04:35'
updated_date: '2026-08-26 18:03'
labels: []
dependencies:
  - TASK-186
  - TASK-187
references:
  - docs/RELEASING.md
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
priority: high
type: chore
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release adr-kit v0.55.1 to the three certified coding-agent marketplaces (Claude Code, Codex, GitHub Copilot) and stage the OpenCode npm package, following docs/RELEASING.md and ADR-012.

The version number skips 0.55.0 deliberately. The tag v0.55.0 was pushed at the dev tip (77278c1) before the version bump was committed, so every version site at that commit still read 0.54.0 and the release-publish gate refused to publish it (run 32908217579, failed after 8s). No GitHub Release for v0.55.0 exists and nothing was ever published under that number. The tag is left in place rather than moved, because a pushed tag is a public ref that consumers may register a marketplace from.

Release content: ADR-029 carried out (native hook binary retired, Python is the only hook host) and adr-mcp JSON-RPC conformance tightened. Closes the work tracked in TASK-186 and TASK-187.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every publish surface reports 0.55.1 via scripts/check-release-version.py --expect v0.55.1
- [x] #2 Generated client adapters show changed=0 under scripts/build-client-adapters.py --check
- [x] #3 adr-lint --strict, adr-index --check and the full python -m pytest -q suite pass on the release commit
- [x] #4 PR from release/v0.55.1 into main is green and merged by the maintainer
- [x] #5 Tag v0.55.1 points at the merged main commit and release-publish.yml completed green with a GitHub Release created from the CHANGELOG section
- [x] #6 main is merged back into dev and scripts/check-branch-sync.py reports in sync
- [x] #7 scripts/install-agent-envs.py --clients all advanced the local prepared-directory marketplace and each client reports 0.55.1
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-26 05:11
---
LOKALE GATES GROEN op release-commit `d19fe1d` (branch `release/v0.55.1`), PR [#127](https://github.com/rvdbreemen/adr-kit/pull/127) geopend tegen `main` met auto-merge (MERGE-methode) gewapend.

```
check-release-version.py --expect v0.55.1   pass, 14 publish surfaces op 0.55.1
build-client-adapters.py --check           pass, changed=0
adr-lint --strict docs/adr                 pass, 0 findings
adr-index --check docs/adr                 pass, 41 ADRs, changed: False
check-branch-sync.py                       pass, dev bevat elke commit van main
.githooks/pre-commit (adr-judge LLM-pass)  pass, 0 violations, 0 advisory
python -m pytest -q                         1824 passed, 12 skipped in 683.85s
```

WAAROM 0.55.0 WORDT OVERGESLAGEN — geverifieerd uit primaire bron, niet afgeleid. `git rev-parse v0.55.0^{}` = `77278c1` = de `origin/dev`-tip, niet een release-commit. Publish-run [32908217579](https://github.com/rvdbreemen/adr-kit/actions/runs/32908217579) faalde na 8 s; het joblog geeft `Expected release version: 0.55.0` gevolgd door `##[error]Process completed with exit code 1` — gate 1 (versieconsistentie), niet het npm-staging-job. `gh release list` toont v0.54.0 als laatste; er bestaat geen Release voor v0.55.0. De tag blijft staan.

TESTRUN-HYGIENE, want dit kostte drie runs. De eerste twee gaven F-lawines (run 1 vanaf 88%, run 2 vanaf 3%) en waren allebei artefact. Het mechanisme is nu vastgesteld in plaats van vermoed: een achtergrondtaak die als 'killed' wordt gerapporteerd, killt de wrapper en niet het pytest-kindproces. Na de kill-melding van run 2 draaide PID 47924 aantoonbaar door tot 70%. Run 3 draaide na `Stop-Process` op elke overlevende en een bevestigde telling van 0, losgekoppeld gestart via `Start-Process`, en is volledig schoon. Twee lawines en één schone run op dezelfde commit.
---

author: Claude
created: 2026-08-26 05:19
---
GEPUBLICEERD. PR [#127](https://github.com/rvdbreemen/adr-kit/pull/127) gemerged in `main` als merge-commit `3b5ca00`; alle twaalf checks groen (`validate`, `pytest`, en zes Python 3.10/3.12-combinaties over ubuntu/macos/windows).

TAG GEZET OP DE GEMERGEDE COMMIT, niet op de branch-tip — precies het verschil dat v0.55.0 fataal werd. Geverifieerd na de push:

```
git rev-parse v0.55.1^{}  -> 3b5ca0040db07019de2ecccfaa9bdba3c7b4c9bb
git rev-parse origin/main -> 3b5ca0040db07019de2ecccfaa9bdba3c7b4c9bb
```

Op die checkout van `main` gaven `check-release-version.py --expect v0.55.1` en `build-client-adapters.py --check` allebei groen vóór het taggen.

RELEASE-PUBLISH [32933199425](https://github.com/rvdbreemen/adr-kit/actions/runs/32933199425): `completed/success` op alle drie de jobs — `publish`, `Validate npm package before staging` en `Stage package for maintainer approval`. GitHub Release: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.55.1, body is de `## [0.55.1]`-sectie verbatim. Het npm-pakket staat gestaged en wacht op maintainer-goedkeuring met 2FA.

MERGE-BACK: `main` in de `dev`-lijn was een fast-forward, geen conflicten — `dev` zat volledig in `main`.

AC#7 IS NIET GEHAALD VOOR CODEX, en dat is een lokaal machineprobleem, geen releaseprobleem. `install-agent-envs.py --clients all` eindigde met exit 1:

```
claude   0.55.1  ok
copilot  0.55.1  ok
codex    0.51.0  FAILED (os error 32: file in use)
```

De rollback-waarschuwing ("codex may now have less than it had before this run") is **niet** uitgekomen: `codex plugin list` toont adr-kit nog steeds als `installed, enabled` op 0.51.0. Codex is dus niet stuk, alleen niet bijgewerkt.

Oorzaak, geverifieerd via `Win32_Process`: PID 29840 (`python C:/Users/rvdbr/AppData/Local/adr-kit/marketplaces/0.51.0//bin/adr-mcp`, gestart 2026-08-25 21:23) houdt een handle op de 0.51.0-boom, waardoor `codex plugin remove` de cache-entry niet kan wissen. Die PID is een kind van `claude.exe` PID 37584 — een andere levende Claude Code-sessie, niet van Codex. Niet gekild: dat breekt de MCP-tools van die sessie tot herstart, en dat is een keuze van de maintainer.

HERSTEL: sluit die Claude-sessie (of kill PID 29840) en draai `python scripts/install-agent-envs.py --clients codex`. Herstart daarna elke client om 0.55.1 te laden.
---

author: Claude
created: 2026-08-26 17:57
---
AFGEROND. Merge-back PR [#128](https://github.com/rvdbreemen/adr-kit/pull/128) is gemerged in `dev` als `34645d3`; `check-branch-sync.py` geeft nu:

```
[ok] origin/dev contains every commit from origin/main
[info] origin/dev is 2 commit(s) ahead, which is expected for unreleased work
```

AC#7 IS ALSNOG GEHAALD. De diagnose in comment #2 was juist over het symptóóm maar wees de verkeerde dader aan: ik schreef PID 29840 (`adr-mcp` uit de 0.51.0-marketplace, kind van een andere Claude-sessie). Killen daarvan veranderde niets — de fout bleef identiek. De werkelijke houder was **PID 41880**, `"C:\Python312\python.exe" ./bin/adr-mcp`, een kind van de drááiende `codex.exe` (PID 36692). Het relatieve pad is het bewijs: zijn working directory *is* `C:\Users\rvdbr\.codex\plugins\cache\rvdbreemen-adr-kit-codex\adr-kit\0.51.0`, en een cwd vergrendelt die map op Windows. Codex hield dus zijn eigen plugin-cache vast tegen zijn eigen `plugin remove`.

Na `Stop-Process -Id 41880`:

```
install_exit=0
validation: PASS (codex)
ADR Kit install complete for: codex
```

Eindstand over de drie clients, uit `plugin list`:

```
claude   adr-kit@rvdbreemen-adr-kit          0.55.1  enabled
codex    adr-kit@rvdbreemen-adr-kit-codex    0.55.1  installed, enabled
copilot  adr-kit@rvdbreemen-adr-kit-copilot  0.55.1
```

LES DIE BREDER GELDT DAN DEZE RELEASE: bij `os error 32` op een plugin-cache is de eerste verdachte niet een verweesd proces, maar de client zelf. Een MCP-server die de client start met een relatief commando erft de cache-map als cwd en blokkeert daarmee zijn eigen upgrade. Zoek op ouder-kindrelatie, niet op padnaam in de commandline — die laatste matcht ook je eigen shell.
---

author: Claude
created: 2026-08-26 18:03
---
TWEE CORRECTIES OP DIT RECORD, in de append-only vorm die dit project ook voor TASK-127 gebruikte — de eerdere comments blijven staan zoals ze geschreven zijn.

**1. Comment #2 wijst de verkeerde dader aan.** Wie daar begint te lezen krijgt PID 29840 als oorzaak, en dat klopt niet: killen daarvan veranderde niets. De werkelijke houder was PID 41880, een kind van de drááiende `codex.exe`. Zie comment #3 voor de volledige diagnose. Ik laat #2 staan omdat de gevolgde redenering leerzaam is — hij is fout op precies het punt waar hij op de padnaam in de commandline zocht in plaats van op de ouder-kindrelatie.

**2. De herkomstzin in commit `d19fe1d` klopt niet.** Het commit-bericht zegt: "Bump every declared version site from 0.54.0 to 0.55.1 via `scripts/bump-version.py` and regenerate the codex/ and copilot/ adapters." Ik heb geen van beide commando's gedraaid. De 0.55.1-waarden stonden al ongecommit in de werkboom toen ik begon; ik heb ze geverifieerd in plaats van geschreven, met `check-release-version.py --expect v0.55.1` (14 surfaces akkoord) en `build-client-adapters.py --check` (`changed=0`).

De waarden zijn dus aantoonbaar juist en de poort bewijst dat onafhankelijk van wie ze heeft getypt. Alleen de herkomstbewering in het bericht is onjuist. De commit is publiek en zit in `main`, dus ik herschrijf hem niet — dit record is de correctie. Relevant voor ADR-013: die eist dat een versie via de registry wordt geschreven en niet met de hand, en op basis van dit commit-bericht alleen kun je niet vaststellen dát dat gebeurd is. De gate kan dat wel, en deed dat.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.55.1 is gepubliceerd naar de drie gecertificeerde marketplaces en het OpenCode-pakket staat gestaged voor npm.

ROUTE: PR #127 gemerged in `main` als `3b5ca00` (twaalf checks groen), tag `v0.55.1` gezet op die gemergede commit en geverifieerd gelijk aan `origin/main`, release-publish run 32933199425 groen op alle drie de jobs, GitHub Release aangemaakt uit de CHANGELOG-sectie. PR #128 daarna gemerged in `dev` als `34645d3`; `check-branch-sync.py` meldt weer in sync.

WAAROM 0.55.1 EN NIET 0.55.0: de tag v0.55.0 stond op de dev-tip `77278c1`, waar elk version site nog 0.54.0 las. Gate 1 van release-publish weigerde terecht te publiceren (`Expected release version: 0.55.0`, exit 1 na 8 s). Er is nooit iets als 0.55.0 gepubliceerd. De tag is blijven staan in plaats van verplaatst, omdat een gepushte tag een publieke ref is waar consumers een marketplace op kunnen registreren.

LOKALE INSTALL: alle drie de clients staan op 0.55.1, geverifieerd via `plugin list`. Codex kostte drie pogingen: `codex plugin remove` liep op `os error 32` omdat PID 41880 (`python ./bin/adr-mcp`, kind van de draaiende codex.exe) de plugin-cache als working directory had. Een cwd vergrendelt die map op Windows. Na `Stop-Process` op dat ene proces slaagde de install met `validation: PASS (codex)`.

NOG TE DOEN DOOR DE MAINTAINER: het npm-pakket goedkeuren met 2FA, en elke client herstarten om 0.55.1 te laden.
<!-- SECTION:FINAL_SUMMARY:END -->
