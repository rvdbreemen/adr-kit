---
id: TASK-183
title: Release adr-kit v0.53.0
status: Done
assignee: []
created_date: '2026-08-19 22:03'
updated_date: '2026-08-25 23:04'
labels:
  - release
dependencies: []
priority: medium
type: task
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release v0.53.0 per docs/RELEASING.md and ADR-012. Carries ADR-040 (Accepted): MCP server grows from five to seven tools (adr_lint, adr_related), agent guide rewritten for autonomous operation, doctor/installer smoke on the seven-tool contract. Depends on PR #115 (feat/mcp-lint-related into dev). Minor bump: new user-facing capability, no breaking changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PR #115 merged into dev
- [x] #2 bump-version.py 0.53.0 + adapters regenerated; no hand-edited versions
- [x] #3 CHANGELOG 0.53.0 section at release-note quality; README reflects seven MCP tools
- [x] #4 All local gates pass (check-release-version, adapters --check, adr-lint --strict, adr-index --check, full pytest)
- [x] #5 Release PR into main green; maintainer merges
- [x] #6 Tag v0.53.0 pushed after maintainer confirmation; release-publish.yml green
- [x] #7 Merge-back PR into dev opened
- [ ] #8 Local prepared-directory marketplaces re-registered for all three clients
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Geverifieerd afgerond op 2026-08-26. Bewijs dat v0.53.0 in `main` zit:

- `git merge-base --is-ancestor v0.53.0 origin/main` → YES. Ook ancestor van `origin/dev`.
- AC#1: PR #115 "feat(mcp): expose adr_lint and adr_related per ADR-040" gemerged in `dev` op 2026-08-19T22:03:39Z.
- AC#2: alle vijf versiesites op tag v0.53.0 lezen 0.53.0 — `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `codex/.codex-plugin/plugin.json`, `copilot/plugin.json`, `package.json`.
- AC#3: CHANGELOG-sectie `## [0.53.0] - 2026-08-20` staat in `origin/main`. README op tag v0.53.0 bevat de MCP-tooltabel met alle zeven regels: `adr_context`, `adr_judge`, `adr_status`, `adr_quality`, `adr_readiness`, `adr_lint`, `adr_related`. `bin/adr-mcp` op diezelfde tag declareert 7 tools.
- AC#4: `main` is beschermd met `enforce_admins: true`; de verplichte `validate`-check kan niet omzeild zijn, dus de merge van PR #116 bewijst dat de gates groen waren.
- AC#5: PR #116 "chore(release): v0.53.0" gemerged in `main` op 2026-08-20T04:34:09Z.
- AC#6: tag v0.53.0 gepusht; `release-publish.yml`-run op die tag rapporteert `success`. GitHub Release "adr-kit v0.53.0" bestaat.
- AC#7: merge-back naar dev is voltooid, zij het niet in één keer. De PR-keten #122 → #123 → #125 → #126 (allemaal in `dev`, 2026-08-25) herstelde de main→dev-ancestry; v0.53.0 is nu ancestor van `origin/dev`.

AC#8 NIET AFGEVINKT — niet bewijsbaar uit git. "Local prepared-directory marketplaces re-registered for all three clients" is een toestand van de ontwikkelmachine, geen repository-feit. Bewust open gelaten in plaats van op een gevolgtrekking afgevinkt.

DATUM-AFWIJKING, vastgelegd omdat hij verwarrend is: de GitHub Release voor v0.53.0 draagt tijdstempel 2026-08-25T22:37:23Z, terwijl PR #116 al op 2026-08-20 in `main` landde. De succesvolle `release-publish.yml`-run op tag v0.53.0 dateert eveneens van 2026-08-25. De release is dus vijf dagen na de merge gepubliceerd.

NAGEKOMEN BEWIJS VOOR AC#4, dat de eerdere redenering vervangt. AC#4 noemt vijf gates bij naam: `check-release-version`, `adapters --check`, `adr-lint --strict`, `adr-index --check`, volledige pytest. Ik vinkte hem eerst af op branch-protection, en dat dekt die opsomming niet: de required check `validate` draait `adr-lint` **zonder** `--strict`.

Het directe bewijs zit in `.github/workflows/release-publish.yml`, één sequentieel job `publish`:

| Regel | Stap | AC#4-gate |
|---|---|---|
| 66 | Version consistency across certified clients and OpenCode | check-release-version |
| 70 | Client adapter drift check | adapters --check |
| 77 | `python bin/adr-lint --strict docs/adr` | adr-lint --strict |
| 80 | ADR index check | adr-index --check |
| 83 | Unit tests | pytest |
| 105 | **Create GitHub Release** | — |

De `release-publish.yml`-run op tag v0.53.0 rapporteert `success` en GitHub Release 'adr-kit v0.53.0' bestaat. Alle vijf met naam genoemde gates zijn daarmee aantoonbaar groen gedraaid op de exacte tag. Alle vijf gedekt, geen gevolgtrekking meer.

Ter aanvulling, de required checks op `main`: `pytest`, `validate`, `ADR Enforcement (declarative)`, `generated ADR indexes are up to date`, met `enforce_admins.enabled: true`. De `pytest`-context komt uit `adr-lint-self.yml` job `pytest` (`pytest tests/ -v`, volledige suite), dus ook op de PR-route was de hele suite verplicht.
<!-- SECTION:FINAL_SUMMARY:END -->
