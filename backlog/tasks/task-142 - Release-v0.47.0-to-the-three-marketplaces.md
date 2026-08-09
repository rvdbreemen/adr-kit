---
id: TASK-142
title: Release v0.47.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-08-07 07:24'
updated_date: '2026-08-07 18:43'
labels: []
dependencies: []
ordinal: 113500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Cut v0.47.0 from `dev` into `main` per `docs/RELEASING.md` and ADR-012.

Carries the work of the 2026-08-06 backlog sweep and the C4 documentation refresh:

- **ADR-035** — `adr-suggest` now runs by default, on the same terms ADR-017 set for the judge. The opt-in rested on ADR-001, which ADR-017 superseded without carrying its reasoning to the second entry point. User-facing behaviour change, hence the minor bump.
- **ADR-034** — the hook manifest declares `network_allowed` per event rather than for the whole set; `pr-create` and `user-prompt-submit` override it with a stated reason.
- Two features that were wired, tested and dead end to end are now alive: ADR-024's pull-request nudge (the guard read `stdout` while `adr-suggest` writes to `stderr`) and `ADR_KIT_SUGGEST_DISABLE` (honoured by one caller only).
- The generated client-support matrix stopped granting a fail-closed edit tier that ADR-004 lists under its rejected alternatives.
- Eleven ADRs stopped explaining why their gate was null after it had shipped.
- One bump writer instead of two, and the CHANGELOG compare-link block is now a declared version site.

This is the first release whose compare-link block is written by the canonical tool rather than backfilled by hand.
<!-- SECTION:DESCRIPTION:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.47.0 gepubliceerd. https://github.com/rvdbreemen/adr-kit/releases/tag/v0.47.0

**Runbook volledig doorlopen.** Tag `v0.47.0` op `ed55d69`, `release-publish.yml` groen (run 31206943494), Release aangemaakt uit de CHANGELOG-sectie, geen draft, geen prerelease.

**Gates, op elke stap opnieuw gedraaid:**

| gate | uitkomst |
|---|---|
| `check-release-version.py --expect v0.47.0` | exit 0, 12 oppervlakken eens |
| `build-client-adapters.py --check` | changed=0 |
| `bin/adr-lint --strict docs/adr` | exit 0 |
| `bin/adr-index --check docs/adr` | exit 0 |
| `pytest` | 1873 passed, 13 skipped (3x: voor de PR, na de reviewfix, op het merge-resultaat) |

**Eerste release met een door het gereedschap geschreven compare-link.** Het blok verouderde bij elke vorige release omdat er twee bump-writers waren en de runbook de zwakste noemde; na v0.46.0 wees het nog naar v0.45.0 en misten zeven headings een target. Nu één canonieke writer plus een gedeclareerde version site, dus `check-release-version.py` faalt de release als de link niet met de tag klopt.

**Copilot vond een echt defect in mijn eigen test** (PR #79). `test_the_declared_true_is_true_a_configured_backend_is_reached` beweerde de guard te draaien maar draaide een losse judge-stub en ging `hooks/adr_pr_guard.py` nooit binnen — hij was groen gebleven als de guard helemaal zou stoppen met een judge starten. Copilot koos de docstring-fix; ik nam de andere optie die het zelf aanbood en liet de test de echte keten lopen (guard → judge → model-CLI). Bewezen door de judge-aanroep weg te knippen: faalt, en slaagt weer na herstel. Dit herstelt ook ADR-034's Confirmation, die anders onwaar was geworden.

Dezelfde bugklasse als de nudge die deze release repareert, één laag hoger: een test die tegen een zelfverzonnen stand-in toetst in plaats van tegen het programma.

**Ook gevonden:** `base_ref` valt terug op `init.defaultBranch`, een machinebrede instelling. Waar die `master` leest diffte de guard tegen een `origin/master` die de fixture nooit maakte. Nu lokaal vastgezet in de fixture.

**Merge-back naar dev gedaan** (PR #81), de stap die twee keer eerder is overgeslagen. `check-branch-sync.py`: "origin/dev contains every commit from origin/main", 0 commits achter.

**Lokale marketplace bijgewerkt**, alle drie de clients op 0.47.0 bevestigd uit hun eigen manifest: claude `.claude-plugin/plugin.json`, codex `.codex-plugin/plugin.json`, copilot `installed-plugins/.../plugin.json`. Clients moeten herstart worden om de nieuwe versie te laden.

**PR's:** #79 (release, gemerged naar main), #81 (merge-back naar dev), #80 (CLAUDE.md-sessieleringen, los, naar dev).
<!-- SECTION:FINAL_SUMMARY:END -->
