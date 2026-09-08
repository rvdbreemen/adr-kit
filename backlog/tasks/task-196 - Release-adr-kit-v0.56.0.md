---
id: TASK-196
title: Release adr-kit v0.56.0
status: Done
assignee: []
created_date: '2026-08-27 05:13'
updated_date: '2026-08-27 05:42'
labels: []
dependencies:
  - TASK-195
references:
  - docs/RELEASING.md
  - >-
    docs/adr/ADR-042-drive-the-release-from-the-maintainer-s-machine-and-create-the-tag-from-the-merge.md
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
priority: high
type: chore
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release adr-kit v0.56.0 to the three certified coding-agent marketplaces and stage the OpenCode npm package, following docs/RELEASING.md and ADR-012 as amended by ADR-042.

A minor bump rather than a patch, for two reasons. ADR-042's tag-from-the-merge is a new capability, not a fix. And issue #118 changes behaviour a consumer can observe: frontmatter inference now leaves an unreadable status undetermined instead of defaulting to "Proposed", so adr-migrate reports and refuses where it previously rewrote the record with an invented status.

FIRST RELEASE UNDER ADR-042. The tag must NOT be created by hand. release-publish.yml now triggers on a push to main, reads the canonical CHANGELOG version, and creates the tag on the commit that carries it before publishing in the same run. This release is that mechanism's first real exercise, so verifying it is part of the work: after the merge, the peeled tag must equal origin/main, and the tag must have been created by the workflow rather than by a person.

Contents: ADR-042 accepted and its first half implemented; the #118 and #119 lifecycle fixes; the documentation sweep from TASK-190; the marketplace description refresh from TASK-189; two new version sites in the registry.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The CHANGELOG carries a 0.56.0 section written to release-note quality
- [x] #2 Every publish surface reports 0.56.0, written by bump-version.py rather than by hand
- [x] #3 build-client-adapters.py --check reports changed=0
- [x] #4 adr-lint --strict, adr-index --check and the full pytest suite pass on the release commit
- [x] #5 The PR into main is green on all four required checks and merged
- [x] #6 The tag is created by release-publish.yml rather than by a person, and the peeled tag equals origin/main
- [x] #7 release-publish.yml completes green and the Release body is the 0.56.0 CHANGELOG section
- [x] #8 main is merged back into dev and check-branch-sync.py reports in sync
- [x] #9 The local prepared-directory marketplace is advanced and each client reports 0.56.0
- [x] #10 npm dist-tags.latest names 0.56.0 after the maintainer approves the staged package
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-27 05:29
---
GEPUBLICEERD, EN DE TAG-AUTOMATISERING HEEFT ZIJN EERSTE ECHTE PROEF DOORSTAAN.

PR [#136](https://github.com/rvdbreemen/adr-kit/pull/136) gemerged als `0548ed5`. De push naar `main` triggerde `release-publish.yml`, die de versie uit de CHANGELOG las, de tag op die commit maakte en in dezelfde run publiceerde. **Geen mens heeft getagd.**

```
git rev-parse v0.56.0^{}  -> 0548ed5b61af27a27a01e60aae7ecc3fcb540fed
git rev-parse origin/main -> 0548ed5b61af27a27a01e60aae7ecc3fcb540fed
MATCH
```

Dat is exact de gelijkheid die v0.55.0 had gered. Run [33042302516](https://github.com/rvdbreemen/adr-kit/actions/runs/33042302516), alle vier de jobs groen:

```
Resolve the release tag                       success
publish                                       success
Validate npm package before staging           success
Stage package for maintainer approval         success
```

Release: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.56.0

NPM (AC#10): de maintainer keurde 0.56.0 goed met 2FA. Geverifieerd met een cache-omzeilende read: `versions` bevat 0.56.0, `dist-tags.latest` is 0.56.0, `npm view ... version` geeft 0.56.0, en het pakket draagt zijn SLSA-provenance uit de OIDC-staging. Anders dan bij v0.55.1 stond er maar één versie gestaged, dus de volgordeval kon niet toeslaan.

MERGE-BACK (AC#8): PR [#137](https://github.com/rvdbreemen/adr-kit/pull/137) gemerged als `111e70d`; `check-branch-sync.py` meldt in sync.

AC#9 IS NIET GEHAALD, en verder dan vorige keer. `install-agent-envs.py --clients all` eindigde met exit 1 en bracht alleen Claude Code naar 0.56.0:

```
claude   0.55.1 -> 0.56.0   SELECTED, install complete
codex    0.55.1            FAILED, os error 32 op de plugin-cache
copilot  0.55.1            FAILED, plugin directory cannot be replaced
```

Dezelfde klasse als bij v0.55.1, maar nu op twee clients tegelijk. `Win32_Process` toont **vier** `./bin/adr-mcp`-processen die alle vier kind zijn van de draaiende `codex.exe` (PID 36692); het relatieve pad betekent dat hun working directory de plugin-cache zelf is, en een cwd vergrendelt die map op Windows.

EEN VERSCHIL MET DE VORIGE KEER DAT AANDACHT VERDIENT: de codex-poging meldde nu ook `rollback error: codex validation failed: adr-kit MCP server not listed`. Dat klinkt alsof de rollback iets kapot liet, maar `codex plugin list` toont adr-kit nog gewoon als `installed, enabled` op 0.55.1. De installatie is dus intact; de rollback-validatie faalde omdat de MCP-server niet reageerde terwijl zijn eigen map op slot zat. Niets verloren, wel een misleidende foutboodschap - kandidaat voor TASK-191's scope.

HERSTEL: sluit Codex (of stop de vier adr-mcp-kinderen van PID 36692) en het proces dat de Copilot-pluginmap vasthoudt, en draai dan `python scripts/install-agent-envs.py --clients codex copilot`.
---

author: Claude
created: 2026-08-27 05:42
---
AC#9 ALSNOG GEHAALD. Alle drie de clients staan op 0.56.0:

```
claude   0.56.0
codex    0.56.0
copilot  v0.56.0
npm      0.56.0 (latest)
```

Drie pogingen nodig, en de tweede lag aan mij. De maintainer sloot Codex en Copilot, maar `codex.exe` (PID 36692, WindowsApps-pakket, draaiend sinds 25-08) overleefde dat met **vijf** `adr-mcp`-kinderen - ik had er vier geteld, er kwam er tussen tellen en stoppen nog een bij. Na `Stop-Process` op die vijf was de teller onder 36692 nul.

De tweede poging faalde met exit 2 op `unrecognized arguments: copilot`: ik schreef `--clients codex copilot` met een spatie terwijl `install-agent-envs.py` een kommalijst verwacht. Met `--clients codex,copilot` slaagde hij meteen, `validation: PASS` voor beide.

Dat is het derde exit-code-signaal in deze sessie dat niet betekende wat het leek: eerst `tail` dat npm's falen maskeerde, toen een rollback-melding die geen schade beschreef, en nu een usage-fout die als installatiefout kon worden gelezen. De les die daar telkens onder ligt: lees de foutregel zelf, niet alleen de exit-status.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.56.0 is uitgebracht naar de drie gecertificeerde marketplaces en gepubliceerd op npm. Alle tien de acceptatiecriteria gehaald.

DE KERN VAN DEZE RELEASE: de tag-automatisering uit ADR-042 deed het bij haar eerste echte gebruik. De push naar `main` triggerde `release-publish.yml`, die de versie uit de CHANGELOG las, de tag op die commit maakte en in dezelfde run publiceerde. Geen mens heeft getagd, en `git rev-parse v0.56.0^{}` is gelijk aan `git rev-parse origin/main` (`0548ed5`) - precies de gelijkheid die v0.55.0 had gered.

ROUTE: PR #136 gemerged in `main`, run 33042302516 groen op alle vier de jobs, Release aangemaakt uit de CHANGELOG-sectie (89 regels, geverifieerd met het awk-programma uit de workflow-YAML zelf). PR #137 bracht `main` terug naar `dev`; `check-branch-sync.py` in sync.

NPM: de maintainer keurde 0.56.0 goed met 2FA. `dist-tags.latest` is 0.56.0 en het pakket draagt zijn SLSA-provenance. Anders dan bij v0.55.1 stond er maar één versie gestaged, dus de volgordeval kon niet toeslaan.

LOKALE INSTALL: uiteindelijk alle drie de clients op 0.56.0, maar het kostte drie pogingen. De eerste faalde omdat vijf `adr-mcp`-processen - kinderen van de draaiende `codex.exe` - de plugin-cache als working directory hadden en die map daarmee vergrendelden. De tweede faalde op een fout van mij: `--clients codex copilot` met een spatie, terwijl de installer een kommalijst eist en met exit 2 afsloot op `unrecognized arguments`. Pas de derde poging, met `--clients codex,copilot` na het stoppen van die processen, slaagde met `validation: PASS` voor beide.

WAT DIT BLOOTLEGT VOOR TASK-191: de codex-poging meldde `rollback error: codex validation failed: adr-kit MCP server not listed`, wat klinkt alsof de rollback iets sloopte. Dat was niet zo - `codex plugin list` toonde adr-kit onveranderd als `installed, enabled`. De rollback-validatie faalde omdat de MCP-server niet kon antwoorden terwijl zijn eigen map op slot zat. Een misleidende foutboodschap bovenop de al gerapporteerde test-isolatie.
<!-- SECTION:FINAL_SUMMARY:END -->
