---
id: TASK-180
title: Release adr-kit v0.52.2
status: Done
assignee: []
created_date: '2026-08-18 18:20'
updated_date: '2026-08-25 23:04'
labels:
  - release
  - github
  - npm
dependencies: []
references:
  - docs/RELEASING.md
  - 'https://github.com/rvdbreemen/adr-kit/actions/workflows/release-publish.yml'
modified_files:
  - .claude-plugin/marketplace.json
  - .claude-plugin/plugin.json
  - .githooks/pre-commit
  - .github/plugin/marketplace.json
  - CHANGELOG.md
  - README.md
  - codex/.codex-plugin/plugin.json
  - codex/templates/adr-kit-guide.md
  - codex/templates/cc-settings/guardian-hook-entry.json
  - codex/templates/githooks/pre-commit
  - copilot/plugin.json
  - copilot/templates/adr-kit-guide.md
  - copilot/templates/cc-settings/guardian-hook-entry.json
  - copilot/templates/githooks/pre-commit
  - docs/clients/opencode.md
  - package.json
  - templates/adr-kit-guide.md
  - templates/cc-settings/guardian-hook-entry.json
  - templates/githooks/pre-commit
  - tests/certification/simulated-pass.json
priority: high
type: chore
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Publish the OpenCode reference-shape fix and refreshed certification evidence as adr-kit v0.52.2 through the protected GitHub release workflow, then stage @rvdbreemen/adr-kit-opencode for npm approval. The previously pushed v0.52.1 tag remains unchanged and unpublished because its workflow correctly stopped on stale evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All declared version sites and generated adapters agree on v0.52.2.
- [x] #2 The documented release gates pass on the release branch.
- [x] #3 The GitHub release workflow creates the v0.52.2 release and stages the npm package for approval.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refresh the stale certification fixture and finalize v0.52.2 release notes and version sites. 2. Run the documented release gates. 3. Open the release PR into main and, after maintainer merge, tag the exact merged commit to trigger GitHub Release and npm staging.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The first v0.52.1 tag workflow stopped before publication because CI correctly detected the simulated certification fixture contract_date 2026-07-19 as stale on 2026-08-19. The tag is retained unchanged; refresh the fixture and publish the next coherent patch v0.52.2 instead of force-moving history.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Geverifieerd afgerond op 2026-08-26. Bewijs dat v0.52.2 in `main` zit:

- `git merge-base --is-ancestor v0.52.2 origin/main` → YES. Ook ancestor van `origin/dev`.
- PR #113 "chore(release): v0.52.2" gemerged in `main` op 2026-08-19T17:35:07Z.
- AC#1: alle vijf versiesites op tag v0.52.2 lezen 0.52.2 — `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `codex/.codex-plugin/plugin.json`, `copilot/plugin.json`, `package.json`.
- AC#2: `main` is beschermd met `enforce_admins: true`; de verplichte `validate`-check kan niet omzeild zijn, dus de merge zelf bewijst dat de gates groen waren.
- AC#3: GitHub Release "adr-kit v0.52.2" bestaat (2026-08-19T17:39:16Z). `npm view @rvdbreemen/adr-kit-opencode versions` geeft `["0.52.0","0.52.2"]` — 0.52.2 is niet alleen gestaged maar daadwerkelijk gepubliceerd.

NUANCE OP AC#3, vastgelegd omdat het uit de runhistorie blijkt: de `release-publish.yml`-run op tag v0.52.2 van 2026-08-19 rapporteert `failure`. Een latere run op `main` diezelfde dag rapporteert `success`, na PR #114 "fix(ci): update npm trusted publishing client". De uitkomst is dus via een herstelde run bereikt, niet in één keer. De artefacten — GitHub Release plus npm-versie 0.52.2 — bewijzen de uitkomst ongeacht welke run hem produceerde.

De v0.52.1-tag blijft ongewijzigd en ongepubliceerd, zoals de Implementation Notes beschrijven. Bevestigd: geen GitHub Release voor v0.52.1, en npm kent geen 0.52.1.

TITEL/BESTANDSNAAM-AFWIJKING: het bestand heet `task-180 - Release-adr-kit-v0.52.1.md` terwijl de titel v0.52.2 zegt. De titel is leidend en is tegen v0.52.2 geverifieerd; de bestandsnaam is een fossiel van het aanmaakmoment.

NAGEKOMEN BEWIJS, dat de eerdere redenering op AC#2 vervangt en de 'NUANCE OP AC#3' hierboven precies maakt.

AC#2 stond eerst afgevinkt op branch-protection ('main is enforce_admins'). Te zwak: de required check `validate` draait `adr-lint` **zonder** `--strict`. Het directe bewijs zit in `.github/workflows/release-publish.yml`, één sequentieel job `publish`: version consistency (:66) → adapter drift check (:70) → ADR lint strict (:77) → ADR index check (:80) → unit tests (:83) → **Create GitHub Release (:105)**. Een falende stap breekt de job af, dus het bestaan van de release bewijst dat alle vijf gates groen waren.

DE FAILURE OP DE v0.52.2-TAGRUN IS UITGEZOCHT, run 32282623752:

```
publish:                                                        success
Stage OpenCode package for npm / Validate npm package:          success
Stage OpenCode package for npm / Stage package for approval:    failure
```

Het `publish`-job — gates plus release-aanmaak — is **geslaagd**. Alleen het aparte `stage-opencode-npm`-job (`needs: publish`) faalde op de laatste stap, waardoor de run als geheel `failure` rapporteert. Dat is de npm trusted-publishing-fout die PR #114 diezelfde dag verhielp; de daaropvolgende geslaagde run op `main` heeft 0.52.2 alsnog gepubliceerd.

De eerdere formulering 'de uitkomst is via een herstelde run bereikt' klopte in de conclusie maar was onnodig vaag over wát er faalde. Precies: de release was er meteen, alleen de npm-staging moest over.
<!-- SECTION:FINAL_SUMMARY:END -->
