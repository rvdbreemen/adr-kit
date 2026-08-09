---
id: TASK-88
title: Release adr-kit v0.44.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-08-03 05:41'
updated_date: '2026-08-03 16:19'
labels:
  - release
  - v0.44.0
dependencies: []
priority: high
ordinal: 93500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release v0.44.0 per docs/RELEASING.md and ADR-012. The three coding-agent marketplaces (Claude Code, Codex, GitHub Copilot) all resolve adr-kit from the public repository, so every version site must agree before the tag is pushed.

**What ships.** The spec-gap programme from TASK-73 through TASK-87, plus ADR-018 (local precomputed vector layer, superseding ADR-014) and ADR-019 (end-of-session hooks stay silent). Five new entrypoints: `bin/adr-discover`, `bin/adr-embed`, `bin/adr-settings`, `bin/adr_history_scan.py`, `bin/adr_quality_core.py` — plus `bin/adr-audit` rebuilt as lint-plus-judge and new `adr relate` / `adr answer` / `adr signer` subcommands.

**One breaking change.** `bin/adr-audit` used to be the init discovery scanner; that is now `bin/adr-discover`. Anyone invoking `bin/adr-audit` directly from a script or CI job gets a different command. It carries an explicit `### Breaking changes` callout in the release notes rather than a buried bullet.

Version chosen as a minor bump: under 0.x this project has bumped minor for feature releases, and a breaking change in 0.x belongs in a minor rather than a patch. 0.43.1 would tell a reader "bugfixes only" and they would skip the rename.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The release runs on a branch, never committed directly to main
- [x] #2 scripts/bump-version.py 0.44.0 writes every declared version site; no version is hand-edited
- [x] #3 CHANGELOG.md carries a release-note-quality [0.44.0] section that leads with the bin/adr-audit breaking change
- [x] #4 README describes what actually ships, including the new commands
- [x] #5 All five local gates pass: check-release-version, build-client-adapters --check, adr-lint --strict, adr-index --check, pytest
- [x] #6 The PR into main is green and handed to the maintainer to merge; no --admin, no branch-protection bypass
- [x] #7 The tag v0.44.0 is pushed only after explicit maintainer confirmation, and release-publish.yml goes green
- [x] #8 main is merged back into dev through its own PR, verified with scripts/check-branch-sync.py
- [x] #9 install-agent-envs.py --clients all advances the local prepared-directory marketplace and all three clients report v0.44.0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
**Drie defecten gevonden door CI die alle lokale gates passeerden.** Alle drie dezelfde oorzaak: de ontwikkelmachine heeft dingen die de runners niet hebben, en niets in de release-procedure controleerde dat.

1. `skills/setup/SKILL.md` eindigde op twee lege regels (markdownlint MD012). Geen enkele van de vijf runbook-gates leest Markdown.
2. `import yaml` in `tests/test_adr_lifecycle.py`. CI installeert alleen `pytest` (ADR-016: nul runtime-dependencies is dragend); lokaal stond PyYAML toevallig geïnstalleerd. Zes pytest-jobs faalden tegelijk.
3. `next(adr_dir.glob("ADR-*.md"))` ving het gegenereerde `ADR-INDEX.md`. `glob` geeft bestandssysteem-volgorde, niet gesorteerde volgorde — Windows gaf toevallig het record eerst, Linux de index. Dook pas op toen defect 2 hem niet langer maskeerde.

Alle drie zaten er sinds TASK-77/87: feature-branches draaien `validate` niet, dus ze wachtten tot de release-PR.

**Structureel opgelost.** `docs/RELEASING.md` stap 3 beloofde "dezelfde gates die CI draait" en somde er vijf op die dat niet waren. Er staat nu markdownlint bij (versie en globs gepind, gelijk aan `validate.yml`) plus een suite-run die third-party imports blokkeert via een meta-path finder. Fix bewezen door de runner-omgeving te reproduceren, niet door erover te redeneren: 1434 geslaagd, 16 overgeslagen, 0 gefaald zonder PyYAML.

**Ontwerpkeuze bij de yaml-test:** `pytest.importorskip` alleen zou de test op élke runner overslaan, terwijl hij de bug bewaakt die drie geshipte ADR's corrumpeerde. De gequote vorm wordt nu onvoorwaardelijk getoetst; PyYAML levert alleen nog het zwaardere parse-bewijs waar het bestaat.

**CI groen op acab870 (2026-08-03).** Alle 12 checks SUCCESS: validate, pytest, de zes Python-matrixjobs (3.10/3.12 × ubuntu/macos/windows), ADR Enforcement, adr-readiness, adr-lint smoke, generated ADR indexes. PR-head is identiek aan lokale HEAD.

Overdracht aan de maintainer voor de merge naar `main`. Niet gemerged met `--admin`, geen branch protection omzeild. Daarna: tag v0.44.0 (aparte toestemming), merge-back naar dev via eigen PR, en `install-agent-envs.py --clients all` met per-client verificatie.

**v0.44.0 gepubliceerd (2026-08-03).** PR #55 gemerged door de maintainer naar `main` (`a456258`). Voor het taggen eerst geverifieerd dat de merge de release echt draagt: `check-release-version.py --expect v0.44.0` groen op main, CHANGELOG-sectie `[0.44.0]` bovenaan, breaking-change-callout aanwezig, alle vier entrypoints op main, ADR-019 Accepted.

Tag `v0.44.0` gezet op `a456258` na expliciete toestemming. `release-publish.yml` completed/success; GitHub Release https://github.com/rvdbreemen/adr-kit/releases/tag/v0.44.0 gepubliceerd (geen draft, geen prerelease), body opent met de breaking change.

**Stap 6 klaar en per client geverifieerd** — de runbook waarschuwt dat een gecombineerde run er één half kan laten, dus alle drie apart gecontroleerd: Claude `Version: 0.44.0` (enabled, user scope), Codex marketplace `…\marketplaces\0.44.0`, Copilot `(v0.44.0)`. Alle drie validation PASS.

**Stap 5 loopt:** `sync/release-to-dev` opnieuw aangemaakt vanaf `origin/dev` en `origin/main` erin gemerged — 0 conflicten. Er stond nog een lokale branch van de v0.42.0-sync (al gemerged via PR #50, 0 commits voor op dev); eerst geïnspecteerd, toen pas vervangen. Vijf gates groen op het merge-resultaat; suite draait.

**Stap 5 klaar tot aan de merge.** PR #56 (`sync/release-to-dev` → `dev`) open, 19/19 checks SUCCESS, `mergeable=MERGEABLE state=CLEAN`. Draagt 29 commits; `git diff origin/main..HEAD` is leeg, dus het merge-resultaat is byte-identiek aan `main` — `dev` had geen eigen commits sinds de release, geen conflicten en geen inhoudelijke keuzes. `[Unreleased]` staat boven `[0.44.0]` zoals de runbook eist. Vijf gates plus markdownlint groen op het merge-resultaat; suite 1437 geslaagd, 13 overgeslagen.

AC #8 blijft open tot de maintainer #56 merget: het criterium vraagt dat `check-branch-sync.py` schoon rapporteert, en dat kan pas daarna. Nu meldt hij nog `origin/dev is missing 29 commit(s)` + `v0.44.0 not on origin/dev` — exact de toestand die deze PR opheft.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**v0.44.0 gepubliceerd naar alle drie de marketplaces** op 2026-08-03.

| | |
|---|---|
| Release | https://github.com/rvdbreemen/adr-kit/releases/tag/v0.44.0 |
| Tag | `v0.44.0` op `a456258` — de merge-commit van PR #55 zelf |
| `release-publish.yml` | completed/success |
| Merge-back | PR #56 gemerged; `dev` op `b24446e` |
| `check-branch-sync.py` | `origin/dev contains every commit from origin/main` — exit 0 |
| Clients | Claude `Version: 0.44.0`, Codex `…\marketplaces\0.44.0`, Copilot `(v0.44.0)` |

**Wat er ships.** TASK-73 t/m TASK-87, plus ADR-018 (lokale precomputed vectorlaag, supersedeert ADR-014) en ADR-019 (end-of-session hooks blijven stil). Nieuw: `bin/adr-discover`, `bin/adr-embed`, `bin/adr-settings`, `bin/adr-audit` als lint-plus-judge, en de subcommando's `adr relate` / `adr answer` / `adr signer`.

**De breaking change staat vooraan in de release-body**, niet als bullet: `bin/adr-audit` was de init-discovery-scanner en is dat niet meer. Wie het uit een script aanriep, moet hernoemen naar `bin/adr-discover`.

**Drie defecten die alle lokale gates passeerden**, allemaal met dezelfde oorzaak — de ontwikkelmachine heeft dingen die de runners niet hebben: een dubbele lege regel (markdownlint), een `import yaml` (CI installeert alleen pytest), en een `glob("ADR-*.md")` die per OS een ander bestand koos. Alle drie zaten er sinds TASK-77/87, want feature-branches draaien `validate` niet. Structureel opgelost in `docs/RELEASING.md`: markdownlint met gepinde versie en globs, plus een suite-run die third-party imports blokkeert via een meta-path finder. Fix bewezen door de runner na te bouwen (1434 geslaagd, 0 gefaald zonder PyYAML), niet door erover te redeneren.

**Twee vondsten in code die nieuw was in deze release**, dus nooit kapot geshipt: `adr-settings` printte een opgeslagen API-key voluit terug ondanks een docstring die het tegendeel beloofde, en een kale `bin/adr-audit` las lege stdin en meldde `verdict: exit 0 (on course)` — precies de stille-groene-vink-valkuil voor wie het hernoemde commando nog in CI had staan. Beide gerepareerd met regressietests.

**Procesnotities.** Geen `--admin`, geen branch protection omzeild: beide merges waren de maintainer-actie, en de tag is pas gezet na expliciete toestemming én na verificatie dat `main` de release echt droeg. Er stond nog een lokale `sync/release-to-dev` van v0.42.0; eerst geïnspecteerd (al gemerged via PR #50, 0 commits voor), toen pas vervangen.
<!-- SECTION:FINAL_SUMMARY:END -->
