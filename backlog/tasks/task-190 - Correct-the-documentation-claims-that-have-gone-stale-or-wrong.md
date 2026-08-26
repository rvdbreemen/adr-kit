---
id: TASK-190
title: Correct the documentation claims that have gone stale or wrong
status: In Progress
assignee: []
created_date: '2026-08-26 19:11'
updated_date: '2026-08-26 19:42'
labels: []
dependencies: []
references:
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
  - >-
    docs/adr/ADR-040-grow-the-mcp-tool-surface-only-with-read-only-deterministic-cycle-tools.md
  - packaging/version-sites.json
priority: high
type: docs
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A sweep of the shipped documentation, prompted by finding `SECURITY.md` naming v0.33.x as the latest supported line while the project ships 0.55.1. The sweep found six defects in three classes. Historical records (CHANGELOG, ADR Context sections, `docs/reviews/`, `docs/plans/`, `.github/release-notes-*.md`, dated field checks in ROADMAP) are deliberately out of scope: they are correct as history.

CLASS A - A CAPABILITY CLAIM THAT IS SIMPLY WRONG

1. `README.md` calls the MCP server a "five-tool MCP server" at lines 139, 244, 259 and 298, while the same README says "Seven tools, all key-free" at line 439 and "Why only seven tools?" at line 469. The server really exposes seven: adr_context, adr_judge, adr_lint, adr_quality, adr_readiness, adr_related, adr_status. ADR-040 is the decision that grew the surface from five to seven, so the five-tool phrasing predates it. The README contradicts itself, which is worse than either number being wrong on its own.

CLASS B - VERSION CLAIMS THAT ARE FALSE

2. `SECURITY.md:43-44` lists `v0.33.x (latest) | Supported.` and `v0.32.x and earlier | No routine security backports.` A reporter reads that 0.55.1 receives no routine backports and that a line twenty-two minor versions old is current. The table also contradicts the prose directly above it, which already states the policy correctly: "Only the latest minor release line is supported with security fixes."

3. `ROADMAP.md:8` states "`adr-kit` is at v0.40.0 and remains pre-1.0."

4. `README.md:312` and `:316` point OpenCode users at the published package `@rvdbreemen/adr-kit-opencode@0.52.0`. The newest version npm actually serves is 0.52.2.

CLASS C - REGISTRY GAPS, WHICH ARE WHY CLASS B KEEPS HAPPENING

5. `templates/github-workflows/adr-readiness.yml:16` pins `rvdbreemen/adr-kit/.github/actions/adr-readiness@v0.37.0` and is not declared in `packaging/version-sites.json`. This is a template users copy into their own repositories, so it hands them an action pinned eighteen minor versions back. The comparable README pin for `adr-judge` IS declared and correctly reads v0.55.1. ADR-013 exists to prevent exactly this: a version-bearing file that no writer, gate, generator or test knows about.

6. `.github/ISSUE_TEMPLATE/bug.yml:23` uses "v0.33.0, or another exact release tag" as its placeholder. Cosmetic, but it rots on the same clock.

FOUND AND DELIBERATELY NOT FIXED HERE

`.adr-kit/ADR-guide.md` is git-tracked and stamped `v0.35.0`. It is not a copy of `templates/adr-kit-guide.md` (104 lines against 357, and a different document with its own "Generated ADR Kit guidance" header), so refreshing it means running the install or upgrade flow rather than editing a stamp. Bumping the stamp alone would be worse than leaving it: a fresh number over stale content. `.githooks/pre-commit` shows the project already registry-manages its own dogfood copies, so this file is a genuine gap - it just needs its own task.

`docs/RELEASING.md:57` says "Four tools read that one file" and the table below it lists exactly four. Checked, accurate, no change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README describes the MCP server as seven-tool everywhere and no longer contradicts its own Seven tools section
- [x] #2 SECURITY.md states the supported-versions policy without naming a version that can go stale, and agrees with the prose above the table
- [x] #3 ROADMAP.md no longer asserts a current version number that has to be maintained by hand
- [x] #4 README points OpenCode users at a package version npm actually serves
- [x] #5 templates/github-workflows/adr-readiness.yml is declared in packaging/version-sites.json, reads 0.55.1, and the two generated client copies follow from one regeneration rather than a hand edit
- [x] #6 docs/RELEASING.md's list of declared sites names the new registry entry
- [x] #7 python scripts/check-release-version.py --expect v0.55.1 and python scripts/build-client-adapters.py --check both pass
- [ ] #8 The change lands in dev through a pull request with green CI
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-26 19:42
---
UITGEVOERD. Negen bestanden gewijzigd, twee toegevoegd. De sweep vond onderweg twee dingen die het oorspronkelijke record niet had.

WAT ER BOVENOP KWAM:

* `README.md:244` en `ROADMAP.md:9` claimden **15 workflows**; `clients/workflows.json` declareert er 17. Dezelfde README-zin zei **six bounded hooks**; `hooks/manifest.json` declareert acht events.
* `README.md:799` had een **vijfde** vindplaats van de tool-telling, in cijfervorm (`a 5-tool MCP server`), in een vergelijkingstabel. Die had ik met de hand gemist. De guard vond hem.
* `ROADMAP.md:8` noemde alleen Claude, Codex en Copilot als distributies; OpenCode ontbrak, terwijl ADR-039 dat pakket in 0.52.0 heeft opgeleverd.

DE REGISTRY-FIX, LANGS DE VOORGESCHREVEN WEG:

```
$ python scripts/bump-version.py 0.55.1
CHANGELOG heading '## [0.55.1] - 2026-08-26' already correct
Wrote 0.55.1 to 1 site(s):
  - templates/github-workflows/adr-readiness.yml (readiness workflow template action pin)

$ python scripts/build-client-adapters.py
Generated three client adapters; changed=2, written=2
$ python scripts/build-client-adapters.py --check
Validated three client adapters; changed=0, written=0
```

De pin is niet met de hand gezet: de registry-entry is toegevoegd en de writer heeft hem geschreven, precies wat ADR-013 voorschrijft. De twee kopieen in `codex/templates/` en `copilot/templates/` komen uit de generatie, niet uit een handmatige edit.

WAAROM ER TESTS BIJ ZITTEN, IN EEN TAAK DIE DOCUMENTATIE HEET. Correcte getallen invullen zonder guard is dezelfde fout met verse cijfers. Geen enkele test las de README. `tests/test_readme_counts.py` toetst de drie tellingen tegen hun manifest, en ik heb hem falsifieerbaar gemaakt in plaats van aangenomen dat hij werkt: met `seven-tool` teruggedraaid naar `five-tool` faalt hij met `README calls it a ['five'] MCP server; bin/adr-mcp exposes 7 tools (seven)`, en na herstel is hij weer groen.

`tests/test_bump_version.py` moest mee: `test_fixture_covers_every_declared_site` faalde meteen op de nieuwe registry-entry. Dat is de repo die zijn werk doet - zes tests werden rood tot de fixture het nieuwe site droeg. Precies de bedoeling van TASK-71.

VOLLEDIGE SUITE: `3 failed, 1824 passed, 12 skipped in 1058.40s`. Alle drie onderzocht in plaats van weggeschreven:

1. `test_cli_performance.py::test_lint_and_retire_meet_hard_ceiling_on_this_repo` - `adr-lint p50 2216ms exceeds the 2000ms user-wait ceiling`. Machinelast: dezelfde suite deed er eerder vandaag 683 s over en nu 1058 s. Slaagt bij herdraaien in isolatie.
2. en 3. `test_agent_installer.py::test_rollback_proves_the_client_is_back_before_reporting_success` en `::test_failed_install_removes_a_marketplace_this_run_registered[copilot]`. **Niet van mij, en dat is bewezen in plaats van beredeneerd**: beide falen identiek op een schone `git worktree` van `origin/dev` (`66701a3`), zonder een van mijn wijzigingen.

DE ECHTE OORZAAK VAN 2 EN 3, EN EEN LOSSE BEVINDING WAARD. De foutboodschap noemt een pad op de machine zelf:

```
RuntimeError: copilot's plugin directory cannot be replaced ...
  directory: C:\Users\rvdbr\.copilot\installed-plugins\rvdbreemen-adr-kit-copilot
  reason:    [WinError 5] Access is denied
```

Deze twee tests grijpen naar de **live Copilot-installatie** in plaats van naar `tmp_path`. Ze falen dus voor iedere ontwikkelaar die Copilot open heeft staan, en ze slagen op CI omdat de runner geen Copilot-installatie heeft. Dat is het spiegelbeeld van 'tests groen onder condities die het defect maskeren': hier is de test rood om een reden die niets met de code te maken heeft. Verdient een eigen taak; ik heb er hier niets aan veranderd.
---
<!-- COMMENTS:END -->
