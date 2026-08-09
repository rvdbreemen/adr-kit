---
id: TASK-89
title: Derive the signer from git config when it names a person
status: Done
assignee: []
created_date: '2026-08-03 16:44'
updated_date: '2026-08-03 17:22'
labels:
  - R8
  - lifecycle
  - signer
  - usability
dependencies: []
modified_files:
  - bin/adr
  - spec.md
  - CHANGELOG.md
  - templates/adr-kit-guide.md
  - .claude/adr-kit-guide.md
  - skills/setup/SKILL.md
  - skills/init/SKILL.md
  - skills/upgrade/SKILL.md
  - tests/test_adr_signer_discovery.py
  - tests/test_adr_lifecycle.py
priority: high
ordinal: 94500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`resolve_signer` (bin/adr:1076) resolves the actor from `--changed-by`, then `lifecycle.signer`, then refuses. `git_user_name()` already exists but only builds a hint inside the refusal message — its docstring says "offered as a proposal. Never adopted silently."

**The refusal is stricter than the spec asks for.** R8.1 requires the actor to be "a configured value, not a literal baked into a command line or a default that names the tool". That forbids the old `adr-kit` default, where the tool wrote itself into the record as the decider. `git config user.name` is not the tool naming itself: it is the identity the human configured on that machine and already signs every commit with. It is a configured value.

**The cost of the current strictness is real, not theoretical.** It shipped as a breaking change in v0.44.0: every fresh clone, container and CI runner now fails at the first lifecycle command, including `bin/adr new`. That is friction at exactly the moment someone is trying the tool for the first time.

**What must not be lost.** On CI runners `user.name` is often `github-actions[bot]` or a generic placeholder. Adopting that silently would put a bot's name under a human acceptance, which is what R8 exists to prevent ("evidence of which human accepted"). So: filter identities that look like a bot or a CI default, and announce the derivation rather than performing it silently. "Never adopted silently" survives; only "never adopted" goes.

Resolution order becomes: `--changed-by` → `lifecycle.signer` → `git config user.name` (announced, person-shaped only) → refuse.

Open question for the maintainer: whether this warrants an ADR. On the reading above it implements R8.1 rather than amending it, so a task plus tests is proportionate — but it does change who can end up recorded as having accepted a decision, which is the integrity property R8 protects.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A repository whose git config names a person yields a working signer with no manual step
- [x] #2 The derived name is announced on use, never adopted silently
- [x] #3 A bot or CI identity (github-actions[bot], *[bot], empty, generic placeholders) is refused rather than adopted
- [x] #4 --changed-by and lifecycle.signer still win over the derived value, in that order
- [x] #5 The refusal message still names both manual routes when nothing usable is found
- [x] #6 bin/adr signer reports which source the current signer comes from
- [x] #7 The shipped guide and CHANGELOG describe the new order
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Twee lagen, want ze lossen verschillende problemen op.

**Bij install en upgrade: voorstellen.** `bin/adr signer --suggest` leest het ingelogde GitHub-account (`gh api user`, alleen wanneer de CLI beschikbaar is) en `git config user.name`, rangschikt ze en toont bij elk de bron — een voorstel dat je niet kunt herleiden kun je niet beoordelen, en deze waarde belandt in een onwijzigbare historie. Identieke waarden vallen samen. Het schrijft niets; `--format json` geeft een aanroeper dezelfde lijst. `/adr-kit:setup`, `:init` en `:upgrade` draaien het nu, en bij `init` als stap 1b — vóór de stap die ADR's aanmaakt, want de weigering halverwege een batch ontdekken is het slechtste moment.

**Op de lifecycle-paden: afleiden, met melding.** `git config user.name` wordt overgenomen als `User: <naam>` en op stderr gemeld. R8.1 verbiedt "een default die het gereedschap zelf noemt" — de oude `adr-kit`-actor. Een git-identiteit is het tegenovergestelde: een waarde die de mens op deze machine instelde en waarmee elke commit in de repo al ondertekend is.

**Een machine is geen mens.** `github-actions[bot]`, `dependabot[bot]`, `runner`, `jenkins`, `root`, een kale `user` — geconfigureerde waarden die een machine noemen. Die vallen door naar de weigering, want R8 vraagt bewijs van welke *mens* accepteerde. De weigering zegt nu ook waaróm die specifieke waarde niet is overgenomen.

Volgorde: `--changed-by` → `lifecycle.signer` → afgeleide git-identiteit → weigeren.

**Spec-wijziging, expliciet en niet stilzwijgend.** R8.1 vroeg het install-voorstel al letterlijk; de implementatie deed het nooit. De runtime-afleiding gaat wél verder dan R8.1, want die neemt over met een *melding* in plaats van een *bevestiging*. Vastgelegd als **R8.2** in `spec.md`, met de redenering en de twee voorwaarden — niet als stille uitbreiding.

34 nieuwe tests in `tests/test_adr_signer_discovery.py`. Die sluiten de omgeving af (`GIT_CONFIG_GLOBAL`, `GH_CONFIG_DIR`, lege tokens), anders meten ze de machine van de uitvoerder in plaats van de code — dezelfde fout die de v0.44.0-PR op zes runners rood maakte. `test_lifecycle_refuses_to_sign_on_the_users_behalf` moest om dezelfde reden mee: die eiste een weigering maar vond in deze repo mijn git-naam.

Suite zonder PyYAML: 1468 geslaagd, 16 overgeslagen, 0 gefaald. Markdownlint, adapter-drift en ADR-lint schoon.
<!-- SECTION:FINAL_SUMMARY:END -->
