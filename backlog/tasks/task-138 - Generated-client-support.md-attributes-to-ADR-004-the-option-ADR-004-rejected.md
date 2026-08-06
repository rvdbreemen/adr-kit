---
id: TASK-138
title: Generated client-support.md attributes to ADR-004 the option ADR-004 rejected
status: Done
assignee: []
created_date: '2026-08-06 05:53'
updated_date: '2026-08-06 18:33'
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
- [x] #1 `scripts/client_certification.py` no longer attributes a fail-closed pre-edit floor to ADR-004; the generated text states ADR-004's actual position, that `bin/adr-judge` at pre-commit is the only fail-closed floor and that injection hooks steer rather than block
- [x] #2 The Copilot section is re-examined: if the absence of a pre-tool-use event is not a degradation against ADR-004's actual model, the heading and the `clients/capabilities.json` degradation entry are corrected rather than reworded
- [x] #3 ADR-023's second fail-closed tier (the pull-request guard, `hooks/adr_pr_guard.py`) is reflected wherever the generated text enumerates fail-closed tiers
- [x] #4 `docs/client-support.md`, `codex/` and `copilot/` are regenerated and `python scripts/build-client-adapters.py --check` reports changed=0
- [x] #5 A test asserts the generated support document does not claim a fail-closed edit tier, so the claim cannot come back silently
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed on `fix/backlog-todo-sweep` (commit a08ad80).

**AC#1.** The paragraph is gone. `scripts/client_certification.py` emitted "ADR-004 names the pre-edit tier the *fail-closed* floor of the injection model" — ADR-004 says the opposite twice, and lists a fail-closed edit gate under its rejected alternatives. Replaced by a derived `## Where enforcement is fail-closed` section stating ADR-004's actual model: three fail-open injection tiers, no pre-edit floor on any client, `bin/adr-judge` at pre-commit as the floor.

**Why it was wrong is the reusable part.** It was a hardcoded block — the same reason `_lifecycle_rows`' own docstring gives for the claims this document had to be rewritten to remove: nothing derived it, so nothing could contradict it. Both new sections derive from `hooks/manifest.json` and `clients/capabilities.json`.

**AC#2 — the entry stays, its text was corrected.** The absence of a pre-tool-use event on Copilot *is* a real degradation of ADR-004's edit tier, which is an injection tier rather than a floor, so `copilot-pretool-context-limit` is not a phantom. Its wording was wrong in the other direction: it read "Copilot PreToolUse cannot inject arbitrary model context", while `hooks/manifest.json` and the shipped `copilot/hooks.json` both say Copilot exposes no pre-tool-use event at all, and the stated user effect described a proactive guard that does not run there. Reason, user effect and backstop rewritten to match the registries. The heading "Known degradation: no fail-closed edit floor on GitHub Copilot CLI" is gone.

**AC#3 — client-qualified, not asserted flatly.** ADR-023's pull-request tier is enforced only where a client can return a permission decision. The generated table reads: Claude Code enforced at `PreToolUse`; Codex advisory only (`codex-pr-guard-advisory-only`); Copilot no native event. Stating "two fail-closed tiers" flatly in a per-client support document would have repeated the defect being fixed.

**AC#4.** `python scripts/build-client-adapters.py --check` reports changed=0. **Record correction:** the task says the document is mirrored into `codex/` and `copilot/`. It is not — `docs/client-support.md` has no client mirror; only the canonical source is generated, by the `--certify --support-output` path in `.github/workflows/validate.yml`.

**AC#5.** Two tests in `tests/test_client_certification.py`: one on the claims that must stay gone, matched over whitespace-collapsed text (matching bare words fails, because the sentence *denying* a fail-closed edit gate necessarily contains the phrase); one asserting every declared degradation is rendered, so the document cannot claim one that is not declared or omit one that is. Both verified failing against the previous generator.

**Collateral, found by making the above true:** `scripts/client_certification.py` reached 486 lines against ADR-010's 400-line support-module budget. Split along the seam its own docstring named — validation stays, rendering moves to `scripts/client_support_matrix.py`, re-exported so no caller changed. Added to the budgeted list in `tests/test_release_allowlist.py`.
<!-- SECTION:FINAL_SUMMARY:END -->
