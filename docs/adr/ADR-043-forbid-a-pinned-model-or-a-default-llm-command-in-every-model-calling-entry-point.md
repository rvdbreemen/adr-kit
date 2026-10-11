---
id: "ADR-043"
title: "Forbid a pinned model or a default LLM command in every model-calling entry point"
status: "Accepted"
date: "2026-10-06"
binding: true
gate: "adr-no-pinned-model-v1"
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-036"
topics:
  - "llm judge"
  - "model selection"
  - "host model"
  - "enforcement"
aliases:
  - "pinned model"
  - "DEFAULT_LLM_CMD"
  - "--model claude"
components:
  - "bin/adr_llm.py"
symbols:
  - "resolve_llm_backend"
  - "HOST_COMMANDS"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-043 Forbid a pinned model or a default LLM command in every model-calling entry point

## Status

Accepted, 2026-10-06.

## Status History

```yaml
status_history:
  - date: 2026-10-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-036
    changed_via: adr-kit lifecycle
  - date: 2026-10-06
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-017 decided that the LLM judge runs on the host agent's own model, and its
Enforcement block guarded that decision with two declarative rules: no entry
point may pass a pinned model flag (`--model ... claude`), and no entry point may
carry its own default command vector (`DEFAULT_LLM_CMD = ...`). Both rules exist
because each failure already happened once: `bin/adr-suggest` kept a pinned
`--model claude-sonnet-4-6` default for a day after ADR-017 was accepted
(ADR-017's 2026-07-31 enforcement note, TASK-72).

ADR-036 superseded ADR-017. It kept the host-model-only decision and retired the
HTTP backends, but it has no `## Enforcement` section, and `bin/adr-judge` reads
Enforcement only from Accepted ADRs (`bin/adr-judge:2786`). So since ADR-036 the
two rules have not been applied to any commit. This was found during the C4
refresh (TASK-219) and recorded as TASK-221 item 2.

The old scope also had a hole of its own. Its `path_glob` named `adr-judge`,
`adr-suggest` and `adr_llm.py`. `bin/adr-substance`, added in 0.58.0, calls the
model through the same resolver and was never covered. That is the drift
ADR-017's own note describes: a file that names a model, outside every rule.

## Decision Drivers

* The host-model-only decision (ADR-036) has no mechanical guard; a reviewer is
  the only thing between a pinned model and a commit.
* Both prohibited shapes have occurred in this repository before.
* The guard must follow the set of files that call a model, not a list someone
  has to remember to extend.

## Considered Options

* Carry the two rules in a new ADR and widen their scope to every model-calling
  entry point.
* Add an `## Enforcement` section to ADR-036.
* Leave the rules lapsed and rely on code review.

## Decision Outcome

Chosen option: **carry the two rules in a new ADR and widen their scope to every
model-calling entry point**, because it restores the guard without rewriting an
Accepted record, and the widened scope closes the hole that let
`bin/adr-substance` sit outside it.

**Decision Maker:** User: Robert van den Breemen chose this option over amending
ADR-036 (option A, which the agent recommended) on 2026-10-06, preferring a
clean history in which an Accepted ADR's enforcement is not edited after the fact.

### Confirmation

The gate `adr-no-pinned-model-v1` is a test in
`tests/test_no_pinned_model_gate.py`. It asserts that every file under `bin/`,
`codex/bin/` and `copilot/bin/` that resolves an LLM backend matches this ADR's
`path_glob`, that both patterns are valid, and that no file in scope matches
either pattern today.

## Decision Contract

### Must

* Every entry point that calls a model resolves its backend through
  `bin/adr_llm.py` (`resolve_llm_backend`), the only place a command vector may
  live (`HOST_COMMANDS`).
* A new model-calling entry point is added to this ADR's `path_glob` in the
  same change; the gate test fails until it is.

### Must Not

* Pass a model flag that pins a vendor model (`--model ... claude`) from any
  entry point in scope.
* Define a `DEFAULT_LLM_CMD` constant (or any equivalent default command vector)
  in an entry point.

### Exceptions

* None. An operator selects a different model per machine through
  `ADR_KIT_LLM_CMD` or `--llm-cmd`, which are environment and flag inputs, not
  code in an entry point (ADR-025).

### Verification

* `tests/test_no_pinned_model_gate.py` (gate `adr-no-pinned-model-v1`).
* The two `forbid_pattern` rules below, applied by `bin/adr-judge` to every
  staged diff that touches a file in scope.

## Consequences

### Positive

* The host-model-only decision is guarded again on every commit, by the
  declarative pass, which needs no model.
* `bin/adr-substance` is covered for the first time.
* The gate test turns a forgotten scope extension into a red test instead of a
  silent gap.

### Negative

* Two ADRs now speak about the judge's model: ADR-036 for the decision, this one
  for its enforcement. A reader of ADR-036 has to follow the link to find the
  rules. Mitigation: the two are linked both ways in `related`.
* The regex `--model["'\s,=]+claude` is narrow by design: it targets the pinned
  vendor model that occurred, not every conceivable flag. A differently spelled
  pin would pass. Mitigation: the second rule and the single-registry Must keep
  command vectors in one reviewed place.

## Pros and Cons of the Options

### Carry the rules in a new ADR

* Good, because no Accepted record is edited.
* Good, because the widened scope and its gate test are decided on their own.
* Bad, because the rules live apart from the decision they protect.

### Add an Enforcement section to ADR-036

* Good, because rules and decision sit in one record.
* Bad, because it changes an Accepted ADR after acceptance, which this
  repository otherwise reserves for supersession.

### Leave the rules lapsed

* Good, because it costs nothing now.
* Bad, because the failure it would miss has already happened once here.

## Open Questions

None.

## Related Decisions

* ADR-036 (Retire the vector layer and run the judge on the host model only):
  the decision these rules enforce.
* ADR-017 (Run the LLM judge by default on the host agent's own model,
  Superseded): the original source of both rules.
* ADR-025 (Separate what tracked configuration may select from what only a
  machine may introduce): why operator overrides are not an exception.

## References

* `bin/adr_llm.py` (`HOST_COMMANDS`, `resolve_llm_backend`).
* `bin/adr-judge:2786`: Enforcement is read from Accepted ADRs only.
* ADR-017, section "2026-07-31: the globs now cover every file that can name a
  model" (TASK-72).
* TASK-221 item 2; TASK-219 (where the gap was found).

## Enforcement

```json
{
  "forbid_pattern": [
    {
      "pattern": "--model[\"'\\s,=]+claude",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr{-judge,-suggest,-substance,_llm.py}",
      "message": "Do not pin a model: the host backend passes no model flag so each client CLI resolves the user's own model (ADR-043, ADR-036)."
    },
    {
      "pattern": "DEFAULT_LLM_CMD\\s*=",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr{-judge,-suggest,-substance,_llm.py}",
      "message": "No entry point may carry its own default command vector: bin/adr_llm.py is the only place a command may live (ADR-043, ADR-036)."
    }
  ],
  "forbid_import": [],
  "require_pattern": [],
  "llm_judge": false,
  "llm_judge_reason": "Both rules are exact textual prohibitions that the declarative pass checks completely; a model call would add cost on every touching commit and no judgement."
}
```
