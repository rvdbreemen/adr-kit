---
id: TASK-138
title: Generated client-support.md attributes to ADR-004 the option ADR-004 rejected
status: To Do
assignee: []
created_date: '2026-08-06 05:53'
labels:
  - docs
  - generated
  - governance
  - defect
dependencies: []
references:
  - 'scripts/client_certification.py:334'
  - 'docs/client-support.md:51-58'
  - 'docs/adr/ADR-004-layered-adr-context-injection.md:135'
  - 'docs/adr/ADR-004-layered-adr-context-injection.md:154-158'
  - clients/capabilities.json
priority: medium
ordinal: 109500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`scripts/client_certification.py:334` emits a paragraph into the generated `docs/client-support.md` (and both client mirrors) that states:

> ADR-004 names the pre-edit tier the *fail-closed* floor of the injection model: the one place that refuses rather than degrades, because an edit is the last moment before a decision is violated in code.

ADR-004 says the opposite, twice.

- `docs/adr/ADR-004-layered-adr-context-injection.md:135` — "**One fail-closed floor.** `bin/adr-judge` at pre-commit (and the CI action) remains the **only** mechanism that blocks. Injection hooks never block; they steer."
- `:154-158` — a fail-closed edit gate is listed under the REJECTED options: "brittle and hostile. Legitimate compliant edits touch governed paths constantly; a fail-closed edit gate produces false positives and contradicts the advisory posture that the pre-commit judge already backstops. Blocking belongs at commit, not keystroke."

So the generated text presents a considered-and-rejected alternative as the accepted decision.

Two consequences follow from that, both user-visible:

1. The section is headed "Known degradation: no fail-closed edit floor on GitHub Copilot CLI". Per ADR-004 there is no pre-edit floor on *any* client, so this is not a degradation of Copilot — it describes a floor that was never decided on. The Copilot capability entry may be carrying a degradation that does not exist.
2. The paragraph contradicts itself. It ends with "The enforcement that does not weaken is the pre-commit hook, which is client-independent: a violation is caught before the commit lands on every client, including this one" — which is ADR-004's actual position, stated four sentences after the opposite claim.

Found while refreshing the C4 architecture documentation; the C4 context document uses ADR-023's corrected framing (two fail-closed tiers: pre-commit and the pull-request guard) rather than propagating this error.

This is not a typo in a hand-written file. `docs/client-support.md` carries `<!-- Generated from certification evidence; do not edit. -->`, so the fix belongs in `scripts/client_certification.py` and the regenerated output has to flow through `scripts/build-client-adapters.py` into `codex/` and `copilot/`.

Worth stating plainly: this is a governance tool publishing a false claim about one of its own governing decisions, in the document that tells users what each client guarantees.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `scripts/client_certification.py` no longer attributes a fail-closed pre-edit floor to ADR-004; the generated text states ADR-004's actual position, that `bin/adr-judge` at pre-commit is the only fail-closed floor and that injection hooks steer rather than block
- [ ] #2 The Copilot section is re-examined: if the absence of a pre-tool-use event is not a degradation against ADR-004's actual model, the heading and the `clients/capabilities.json` degradation entry are corrected rather than reworded
- [ ] #3 ADR-023's second fail-closed tier (the pull-request guard, `hooks/adr_pr_guard.py`) is reflected wherever the generated text enumerates fail-closed tiers
- [ ] #4 `docs/client-support.md`, `codex/` and `copilot/` are regenerated and `python scripts/build-client-adapters.py --check` reports changed=0
- [ ] #5 A test asserts the generated support document does not claim a fail-closed edit tier, so the claim cannot come back silently
<!-- AC:END -->
