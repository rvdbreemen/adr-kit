<!-- ADR-KIT CLAUDE START -->
## ADR Kit

Read `.adr-kit/ADR-guide.md` before architectural changes. Architecture decisions live in `docs/adr/`. Use `/adr-kit:context` before implementation, `/adr-kit:adr` for new decisions, and `/adr-kit:judge` before commit.
<!-- ADR-KIT CLAUDE END -->

## Backlog.md

This repository uses Backlog.md (`backlog/`) as the source of truth for work.

- Search for an existing task before starting any meaningful implementation or
  design work.
- If no task exists, create one before editing code or docs.
- Prefer the Backlog MCP tools for reading, searching, creating, and updating
  tasks. Use the `backlog` CLI only as a fallback.
- Keep tasks small enough to complete in one focused pass.
- Do not edit files in `backlog/tasks/` directly.

## Werken in deze repo

- Reproduceer de oorzaak die een backlog-taak noemt voordat je een fix ontwerpt; corrigeer daarna het record. In twee sweeps klopte respectievelijk 3 van 4 en 4 van 12. Toets ook de ernstinschatting en de volledigheid van een opsomming, niet alleen de genoemde oorzaak.
- `python -m pytest -q` duurt ~11 minuten en is verplicht voor een merge of release. Gerichte runs missen guards in bestanden die je wijziging niet aanraakt: een modulesplitsing brak een check in `tests/test_setup_project_command.py`.
- Wissel nooit van branch tijdens een testrun. Een run die op branch A start en op B eindigt rapporteert failures die artefacten van de checkout zijn.
- Maak eerst alle wijzigingen in canonieke bestanden, regenereer daarna één keer met `python scripts/build-client-adapters.py`, en bevestig met `--check` (verwacht `changed=0`). Bewerk `codex/` en `copilot/` nooit met de hand.
- `python bin/adr relate ADR-A --to ADR-B` schrijft beide kanten; ADR-028's gate laat een eenzijdige link niet door de lint. `python bin/adr accept ADR-N` weigert zonder `--confirm`: acceptatie zet een naam in een onveranderlijke historie en moet expliciet gevraagd worden.
- ADR-010 begrenst regels per bestand, afgedwongen in `tests/test_release_allowlist.py`: entrypoints in `scripts/` maximaal 300 regels, support-modules 400. Splits langs de naad die de docstring al beschrijft en voeg de nieuwe module toe aan die lijst.
- `main` en `dev` zijn beschermd met `enforce_admins: true`, dus `gh pr merge --admin` omzeilt de verplichte `validate`-check niet. Gebruik `--auto`: dat verzwakt niets en mergt zodra de checks slagen. Mergen naar `main` is de actie van de maintainer.
