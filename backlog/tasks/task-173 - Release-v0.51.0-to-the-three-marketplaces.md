---
id: TASK-173
title: Release v0.51.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-08-10 22:07'
updated_date: '2026-08-25 23:03'
labels:
  - release
dependencies: []
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ships TASK-171: a declared timeout on a call that starts a client CLI is now a real upper bound.

`subprocess.run(timeout=N)` bounds nothing once a descendant outlives the direct child - its own handler kills the child and then drains the pipes unbounded, and on Windows that kill is `TerminateProcess` on a single handle. Behind a `.CMD` shim, which is what an npm-installed client CLI is, the grandchild survives holding the pipe. Measured: `subprocess.run` returned after 25.22s on a `timeout=1` call; the new runner after 1.65s with the tree gone.

ADR-010 (Accepted, binding) describes these calls as bounded. The claim was made true rather than softened, so no ADR changes.

Minor rather than patch: all three paths that start a client CLI or packaged runtime now spawn through a different runner that kills the process tree on timeout - the hook smoke test, the installer runner, and the deep-doctor probe.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bump-version.py moved every version site and the client trees were regenerated
- [x] #2 CHANGELOG has a release-quality 0.51.0 section naming what changes for a user
- [x] #3 All five local gates pass
- [x] #4 PR into main is green and handed to the maintainer
- [x] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [x] #6 Release merged back into dev
- [ ] #7 Local prepared-directory marketplace advanced and the three clients report 0.51.0
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Geverifieerd afgerond op 2026-08-26. Bewijs dat v0.51.0 in `main` zit:

- `git merge-base --is-ancestor v0.51.0 origin/main` → YES. Ook ancestor van `origin/dev` (AC#6).
- PR #100 "Release v0.51.0: a declared timeout is now a real bound" gemerged in `main` op 2026-08-11.
- GitHub Release "adr-kit v0.51.0" bestaat (tag v0.51.0, 2026-08-11T04:56:26Z) (AC#5).
- CHANGELOG-sectie `## [0.51.0] - 2026-08-11` staat in `origin/main`, met TASK-171 als inhoudelijke regel (AC#2).
- Versiesites op tag v0.51.0: `.claude-plugin/plugin.json`, `codex/.codex-plugin/plugin.json` en `copilot/plugin.json` lezen alle drie 0.51.0 (AC#1). `package.json` bestond nog niet op deze tag — die is pas met de OpenCode-npm-packaging in 0.52.0 toegevoegd.
- AC#3 (gates): `main` is beschermd met `enforce_admins: true`, dus de verplichte `validate`-check kan niet omzeild zijn. Een gemergede PR in `main` is daarmee bewijs dat de gate groen was.

AC#7 NIET AFGEVINKT — niet bewijsbaar uit git. "Local prepared-directory marketplace advanced en de drie clients rapporteren 0.51.0" is een toestand van de ontwikkelmachine, geen repository-feit. Bewust open gelaten in plaats van op een gevolgtrekking afgevinkt.

NAGEKOMEN BEWIJS VOOR AC#3, dat de eerdere redenering vervangt. Ik vinkte AC#3 aanvankelijk af op branch-protection ('main is enforce_admins, dus validate was groen'). Dat was een gevolgtrekking, en voor de vijf met naam genoemde gates te zwak: de required check `validate` draait `adr-lint` **zonder** `--strict`.

Het directe bewijs zit in `.github/workflows/release-publish.yml`. Dat is één sequentieel job (`publish`) met deze stapvolgorde:

| Regel | Stap |
|---|---|
| 66 | Version consistency across certified clients and OpenCode |
| 70 | Client adapter drift check |
| 77 | ADR lint (strict) — `python bin/adr-lint --strict docs/adr` |
| 80 | ADR index check |
| 83 | Unit tests |
| 105 | **Create GitHub Release** — `gh release create` |

De release wordt pas op regel 105 aangemaakt. Stappen in één job zijn sequentieel en een falende stap breekt de job af. Het **bestaan** van GitHub Release 'adr-kit v0.51.0' bewijst daarmee dat alle vijf gates — inclusief `adr-lint --strict` — groen waren op tag v0.51.0. Geen gevolgtrekking meer, maar een eigenschap van de workflow.

Ter aanvulling, de required checks op `main` (`gh api .../branches/main/protection`): `pytest`, `validate`, `ADR Enforcement (declarative)`, `generated ADR indexes are up to date`, met `enforce_admins.enabled: true`. De `pytest`-context komt uit `adr-lint-self.yml` job `pytest` en draait `pytest tests/ -v`, dus de volledige suite is wél een verplichte check — alleen `--strict` ontbrak daar, en dat gat dekt release-publish af.
<!-- SECTION:FINAL_SUMMARY:END -->
