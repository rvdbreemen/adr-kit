---
id: TASK-174
title: Add generic OpenCode support through portable ADR Kit surfaces
status: Done
assignee: []
created_date: '2026-08-13 22:14'
updated_date: '2026-08-25 23:24'
labels:
  - opencode
  - generic
  - compatibility
  - discovery
dependencies: []
references:
  - 'https://opencode.ai/docs/skills/'
  - 'https://opencode.ai/docs/rules/'
  - 'https://opencode.ai/docs/mcp-servers/'
  - 'https://opencode.ai/docs/plugins/'
  - >-
    backlog/archive/tasks/task-40.9 -
    Build-and-certify-the-shared-Kilo-Code-and-OpenCode-adapter-family.md
documentation:
  - docs/clients/opencode.md
modified_files:
  - clients/generic/
  - tests/fixtures/opencode/
  - tests/test_opencode_generic_discovery.py
  - docs/clients/opencode.md
  - docs/client-support.md
  - README.md
  - INSTALL.md
  - AGENTS.md
priority: medium
type: enhancement
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide tested generic compatibility for OpenCode without adding a native TypeScript plugin, installer mutation, or native hook adapter. Reuse ADR Kit's existing portable skills, project AGENTS.md guidance, and stdio MCP server through OpenCode's documented discovery paths. Document unsupported native lifecycle, doctor, update, and certification claims honestly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 OpenCode can discover ADR Kit workflows from a documented generic skill path with valid OpenCode frontmatter.
- [ ] #2 OpenCode receives ADR Kit project guidance through AGENTS.md without replacing user-owned content.
- [ ] #3 OpenCode can use the local adr-kit MCP server through documented opencode.json configuration without a product-specific runtime bridge.
- [ ] #4 Focused discovery tests validate supported and unsupported surfaces and do not add OpenCode to the three-client native registry or release gate.
- [ ] #5 Documentation explains setup, opt-out/manual MCP registration, evidence scope, and the boundary between generic compatibility and native support.
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: OpenCode
created: 2026-08-16 20:07
---
Investigation 2026-08-16: the reported OpenCode desktop error
o such column: name is an upstream OpenCode 1.18.18 SQLite migration failure, not an ADR Kit plugin failure. Desktop logs show it before the native plugin development session; upstream issue #40470 and PR #37707 document the same legacy migration-journal bug. The local opencode.db was rebuilt successfully at 2026-08-13T21:57:43Z. ADR Kit's plugin loads via opencode debug config, and the focused package/plugin suite passes 10 tests. No repository code was changed during this investigation; TASK-174 remains In Progress because its generic-support acceptance criteria are separate from ADR-039's native-plugin work.
---

author: OpenCode
created: 2026-08-16 20:07
---
Correction: the exact logged error is Error: no such column: name. The previous comment lost Markdown backticks because PowerShell uses them as escapes; the intended command name is opencode debug config.
---

author: OpenCode
created: 2026-08-16 21:31
---
ADR-039 was explicitly accepted on 2026-08-16. Native OpenCode support is now the approved architectural direction while the certified three-client gate remains unchanged. TASK-174's original generic-only description is now a separate compatibility track and should not be treated as the native-plugin decision.
---

author: Claude
created: 2026-08-25 23:01
---
VERIFICATIE 2026-08-26 — NIET AFGESLOTEN. Het is niet zo dat dit werk in `main` zit onder een andere naam; de generieke ondersteuning is nooit gebouwd. Er is iets **anders** gebouwd.

WAT ER NIET IN `main` STAAT (`git ls-tree -r --name-only origin/main`):
- `clients/generic/` — bestaat niet, in geen enkele tree.
- `tests/test_opencode_generic_discovery.py` — bestaat niet. Een grep op `generic` over heel `origin/main` geeft alleen dit taakbestand zelf en een niet-gerelateerde ADR uit het OTGW-testcorpus.

WAT ER WÉL IN `main` STAAT — de native lijn van ADR-039:
- `opencode/plugin.ts`, `opencode.json`, `tests/test_opencode_plugin.py`, `tests/test_opencode_package.py`, `.github/workflows/publish-opencode-npm.yml`, `docs/clients/opencode.md`.
- `opencode.json` in `main` luidt `{"plugin": ["./"]}` — dat is native plugin-registratie, niet de generieke MCP-serverconfiguratie die AC#3 beschrijft.
- `docs/clients/opencode.md` heeft kopjes Install / Native Surface / Hooks / CI / Support Boundary. Er is geen sectie over generieke discovery, opt-out of handmatige MCP-registratie (AC#5).

DE ACs ZIJN DUS NIET GEHAALD, en AC#4 is bovendien inhoudelijk ingehaald: die eist expliciet 'do not add OpenCode to the ... native registry', terwijl ADR-039 (Accepted 2026-08-16) precies native ondersteuning als de goedgekeurde richting vastlegde. Comment #3 op dit record zei dat al op de dag zelf.

DIT IS SUPERSESSIE, GEEN VOLTOOIING — en dat onderscheid is hier het punt. Een aanvaarde richting stil laten doodbloeden is precies het faalpatroon dat TASK-187 in dit project blootlegde. Ik sluit deze taak daarom niet op eigen gezag.

AAN DE MAINTAINER, drie opties met hun gevolg:
(a) Sluiten als 'superseded by ADR-039 / TASK-176' — eerlijk over de uitkomst, en de generieke track verdwijnt bewust.
(b) Open houden en de ACs herschrijven naar wat generieke ondersteuning náást de native plugin nog moet betekenen — zinvol als niet-Claude-clients zonder plugin ADR Kit moeten kunnen vinden.
(c) Open houden zoals hij is — niet aan te raden: AC#4 spreekt een aanvaarde ADR tegen, dus het record veroudert verder.

Mijn advies is (a), tenzij je generieke discovery nog echt wilt.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GESLOTEN ALS SUPERSEDED op 2026-08-26, op beslissing van de maintainer. Niet afgerond — de generieke ondersteuning is nooit gebouwd en wordt bewust niet meer gebouwd.

WAT DEZE TAAK ZOU BOUWEN, en wat aantoonbaar niet in `main` staat (`git ls-tree -r --name-only origin/main`):
- `clients/generic/` — bestaat niet, in geen enkele tree.
- `tests/test_opencode_generic_discovery.py` — bestaat niet. Een grep op `generic` over heel `origin/main` geeft alleen dit taakbestand zelf en een niet-gerelateerde ADR uit het OTGW-testcorpus.

Geen van de vijf ACs is daarmee gehaald; alle vijf blijven ongevinkt. Dat is de eerlijke eindstand.

WAT IN PLAATS DAARVAN SHIPTE — de native lijn van ADR-039 "Add a Native OpenCode Plugin Without Expanding the Certified CLI Gate" (Accepted 2026-08-16), in `main`: `opencode/plugin.ts`, `opencode.json`, `tests/test_opencode_plugin.py`, `tests/test_opencode_package.py`, `.github/workflows/publish-opencode-npm.yml`, `docs/clients/opencode.md`. Uitgeleverd via TASK-176 (v0.52.0), TASK-177/178 (npm-publicatie), TASK-179 en TASK-184 (reference-shape voor 1.18.18). Het npm-pakket `@rvdbreemen/adr-kit-opencode` staat gepubliceerd op 0.52.0 en 0.52.2.

WAAROM SUPERSESSIE EN NIET VOLTOOIING. `opencode.json` in `main` luidt `{"plugin": ["./"]}` — native plugin-registratie, niet de generieke MCP-serverconfiguratie die AC#3 beschrijft. `docs/clients/opencode.md` heeft kopjes Install / Native Surface / Hooks / CI / Support Boundary; geen sectie over generieke discovery, opt-out of handmatige MCP-registratie (AC#5). Er is dus niets dat deze ACs onder een andere naam vervult.

AC#4 IS INHOUDELIJK INGEHAALD, en dat is de kern van de supersessie: die AC eist expliciet "do not add OpenCode to the three-client native registry", terwijl ADR-039 op 2026-08-16 precies native ondersteuning als goedgekeurde richting vastlegde. Comment #3 op dit record signaleerde dat op de dag zelf. Een taak openhouden waarvan een AC een aanvaarde ADR tegenspreekt, laat het record alleen verder verouderen.

DE BESLISSING IS EXPLICIET GENOMEN, niet stilzwijgend. Dat onderscheid telt in deze repo: TASK-187 documenteert wat er gebeurt als een aanvaarde richting stil blijft liggen terwijl de tooling naleving meldt. Hier is de keuze gemaakt en vastgelegd.

ALS GENERIEKE DISCOVERY OOIT ALSNOG GEWENST IS: dat is een nieuwe taak met eigen ACs, geschreven náást de native plugin in plaats van in plaats daarvan. Deze ACs zijn daarvoor niet herbruikbaar, want ze zijn geformuleerd onder de aanname dat er geen native plugin komt.
<!-- SECTION:FINAL_SUMMARY:END -->
