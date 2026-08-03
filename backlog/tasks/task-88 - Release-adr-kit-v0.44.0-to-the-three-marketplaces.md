---
id: TASK-88
title: Release adr-kit v0.44.0 to the three marketplaces
status: In Progress
assignee: []
created_date: '2026-08-03 05:41'
updated_date: '2026-08-03 09:52'
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
- [ ] #5 All five local gates pass: check-release-version, build-client-adapters --check, adr-lint --strict, adr-index --check, pytest
- [ ] #6 The PR into main is green and handed to the maintainer to merge; no --admin, no branch-protection bypass
- [ ] #7 The tag v0.44.0 is pushed only after explicit maintainer confirmation, and release-publish.yml goes green
- [ ] #8 main is merged back into dev through its own PR, verified with scripts/check-branch-sync.py
- [ ] #9 install-agent-envs.py --clients all advances the local prepared-directory marketplace and all three clients report v0.44.0
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
<!-- SECTION:NOTES:END -->
