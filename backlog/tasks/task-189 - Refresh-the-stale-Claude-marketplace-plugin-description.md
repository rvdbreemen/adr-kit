---
id: TASK-189
title: Refresh the stale Claude marketplace plugin description
status: In Progress
assignee: []
created_date: '2026-08-26 18:58'
updated_date: '2026-08-26 19:01'
labels: []
dependencies: []
references:
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
  - scripts/client_generation_model.py
priority: medium
type: docs
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`.claude-plugin/marketplace.json` describes the adr-kit plugin entry with a frozen version marker: "... MCP server; and v0.33 local governance tools: frontmatter, strict lint, lifecycle commands, indexes, adr-doctor." The repository ships 0.55.1, so the description advertises a set of capabilities as if they were new in a release that is twenty-two minor versions old.

This is the description Claude Code users read in the marketplace listing before installing, so it is the first thing the project says about itself. It is a SOURCE file for the generator (`scripts/client_generation_model.py:SOURCE_FILES`), not generated output, so it is edited by hand and then confirmed with `build-client-adapters.py --check`.

Found while correcting the GitHub repository About, which carried two separate errors: it listed Cursor as a supported client (never supported; the only `cursor` occurrences in the tree are loop variables) and it omitted OpenCode. That metadata is fixed directly on GitHub and needs no commit.

Related finding, deliberately NOT in this task's scope: `SECURITY.md:43` states `v0.33.x (latest) | Supported.` The supported-versions table names a version that is twenty-two minor releases behind, which is a stronger defect than a marketing description because it tells a reporter which versions receive fixes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The plugins[0].description in .claude-plugin/marketplace.json names no frozen version marker and describes the capabilities that ship at 0.55.x
- [x] #2 python scripts/build-client-adapters.py --check reports changed=0 after the edit
- [x] #3 The generated codex/ and copilot/ trees are not hand-edited
- [ ] #4 The change lands in dev through a pull request with green CI
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-26 19:01
---
GEWIJZIGD. Één regel in `.claude-plugin/marketplace.json`, geen enkel ander bestand.

Was (309 tekens):

> Drop-in ADR toolkit for AI coding agents: /adr-kit:init bootstrap + audit; bin/adr-judge pre-commit/CI enforcement; /adr-kit:adr authoring; Guardian staleness detection; layered context injection; MCP server; and **v0.33 local governance tools**: frontmatter, strict lint, lifecycle commands, indexes, adr-doctor.

Is (323 tekens):

> Drop-in ADR toolkit for AI coding agents: bootstrap and audit with /adr-kit:init, guided authoring with /adr-kit:adr, pre-commit and CI enforcement with file:line citations, context injection over a generated graph index, Guardian staleness detection, lifecycle commands, strict lint, adr-doctor, and a key-free MCP server.

De bevroren versiemarkering is weg, `file:line` is toegevoegd omdat dat het onderscheidende kenmerk van de enforcement is, en `indexes` is `a generated graph index` geworden — preciezer over wat ADR-007 daadwerkelijk oplevert. Geen lengtelimiet gevonden in de generator of in enig schema; het nieuwe getal ligt binnen de orde van het oude.

AC#3 GEVERIFIEERD IN PLAATS VAN AANGENOMEN. Ik heb eerst uitgezocht of dit bestand bron of output is voordat ik het aanraakte: `scripts/client_generation_model.py:SOURCE_FILES` noemt `.claude-plugin/marketplace.json`, `codex/.codex-plugin/plugin.json` én `copilot/plugin.json` als **bron**. Dat is een nuance op de regel uit CLAUDE.md dat `codex/` en `copilot/` nooit met de hand bewerkt worden: twee manifesten in die bomen zijn wel degelijk bron. Ik heb ze hier geen van beide aangeraakt.

```
python scripts/build-client-adapters.py          Generated three client adapters; changed=0, written=0
python scripts/build-client-adapters.py --check  Validated three client adapters; changed=0, written=0
git status                                       alleen .claude-plugin/marketplace.json gewijzigd
```

`changed=0` bij de generatie bevestigt dat deze beschrijving niet naar de codex- en copilot-bomen doorwerkt, en dat hoort ook zo: het is de listing van de Claude Code-marketplace.

OVERIGE POORTEN:

```
check-release-version.py --expect v0.55.1   pass, alle surfaces op 0.55.1
adr-lint --strict docs/adr                  pass, 0 findings
adr-index --check docs/adr                  pass, 41 ADRs, changed: False
pytest (gericht, 3 bestanden)               38 passed in 72.34s
```

De gerichte run dekt `test_client_adapter_generation.py`, `test_release_allowlist.py` en `test_bump_version.py` — de drie bestanden die de manifesten en de generator toetsen. De volledige suite draait op de PR; voor een eenregelige beschrijvingswijziging is dat de juiste verdeling, en ik meld dit expliciet in plaats van 'alle tests groen' te schrijven op basis van een deelverzameling.
---
<!-- COMMENTS:END -->
