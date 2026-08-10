---
id: TASK-170
title: One ADR yields no usable verdict and degrades the whole LLM pass
status: Done
assignee: []
created_date: '2026-08-09 21:28'
updated_date: '2026-08-10 20:15'
labels:
  - judge
  - llm
dependencies: []
references:
  - bin/adr_llm.py
  - bin/adr-judge
  - >-
    docs/adr/ADR-037-keep-per-adr-judge-verdicts-in-the-advisory-per-machine-guardian-state.md
modified_files:
  - bin/adr-judge
  - >-
    docs/adr/ADR-038-cost-an-unusable-llm-verdict-to-that-adr-alone-not-the-whole-pass.md
  - tests/test_adr_judge_llm.py
  - C4-Documentation/c4-component-enforcement-engine.md
priority: medium
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Observed 2026-08-09, immediately after TASK-169 gave this machine a working judge backend for the first time. A pre-commit judge run over a real staged diff printed:

```
[adr-judge] running LLM pass over 5 llm_judge ADR(s) with host (claude-code-cli): claude -p, one isolated call each...
[adr-judge] WARN: LLM call failed. Rerun with ADR_KIT_DEBUG=1 for details.
[adr-judge] WARN: LLM pass DEGRADED to declarative-only: no usable verdict for ADR-030; whole LLM pass degraded to declarative-only
[adr-judge] OK - 0 violations, 0 advisory
```

Two separate things to look at.

**1. One bad verdict discards every good one.** Four of the five ADRs were judged; ADR-030 produced no usable verdict and the whole pass degraded to declarative-only. ADR-037 made the guardian record verdicts per ADR precisely because a long sweep that is interrupted should keep what it established. The same argument applies here: a single unusable answer should cost that ADR's verdict, not the other four. Whether the current behaviour is deliberate fail-closed caution or an accident is the first question to settle - if it is deliberate, the reasoning belongs in the record.

**2. Why ADR-030 specifically.** The backend itself is fine: `echo "Reply with exactly: OK" | claude -p` returns `OK` with exit 0 on this machine, and four other ADRs were judged in the same run. So this is about that one call - a timeout on a larger prompt, an unparseable answer, or something in ADR-030's Enforcement block. `ADR_KIT_DEBUG=1` on a run with a real staged diff will name it; an empty diff judges nothing and reproduces nothing.

Not blocking: the judge degrades rather than blocking a commit, which is the ADR-001 floor working as designed. But a gate that silently gives up its LLM half on one bad answer is weaker than its own record claims.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The cause of ADR-030's unusable verdict is identified from a debug run over a real staged diff, not inferred
- [x] #2 It is decided and recorded whether one unusable verdict should degrade the whole pass or only that ADR, with the reasoning written down
- [x] #3 If per-ADR degradation is chosen, a run where one ADR fails still reports the verdicts of the others
- [x] #4 Regression coverage pins whichever behaviour is chosen
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude Opus 5
created: 2026-08-10 20:02
---
Criterion 1 stays unchecked on a Done task, deliberately. Why ADR-030 specifically produced no usable verdict was never established: it needs a debug run over a real staged diff against a live backend, and inferring it from the four calls that succeeded would be a guess dressed as a finding. Ticking it would have made the record claim an investigation that did not happen.

The task is Done because its substance - the decision about degradation granularity and the code implementing it - is complete, and because the fix demotes the remaining question from urgent to routine: whatever is fragile about that one call now costs its own verdict instead of the other four. If ADR-030 keeps failing after ADR-038 ships, that is a new observation with a live backend to debug against, and it deserves its own task rather than keeping this one open indefinitely.
---

author: Claude Opus 5
created: 2026-08-10 20:15
---
ADR-038 accepted by the maintainer on request, 2026-08-10: `python bin/adr accept ADR-038 --confirm`. The status history now carries both transitions signed "User: Robert van den Breemen" per ADR-027. Index regenerated (38 ADRs, changed: False) and `adr-lint --strict` passes with 0 advisory findings, so the decision governs and the code already implements it. Nothing outstanding on this task beyond acceptance criterion 1, which stays unchecked for the reason in comment #1.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The discard was deliberate, not an accident of control flow - and it was the wrong remedy for a right concern.

**Question 1, why the whole pass died.** `bin/adr-judge` `run_llm_batch` returned `None` and force-cleared `attestation["evaluated"]` on the first unusable call. Its docstring stated the reason: "a partially-evaluated pass reported as complete is precisely the failure mode this hardening exists to remove." The premise holds; the remedy does not. The danger is a partial pass reported *as complete*, and the attestation already exists to say otherwise. Discarding true positives to avoid mislabelling them pays with the answer to protect the label. The repo's own test asserted this: a VIOLATION established for ADR-001 was thrown away when ADR-002's call failed, and the run printed `OK`.

**Question 2, why ADR-030 specifically.** Not answered, and deliberately not guessed at. Reproducing it needs a debug run over a real staged diff with a live backend, and the fix makes the question far less urgent: whatever is fragile about that one call now costs its own verdict instead of the other four. Left in the record as the open half.

**The decision, recorded as ADR-038** (Proposed): one unusable call costs that ADR's verdict alone. `run_llm_batch` returns what it established, `evaluated` lists the ADRs that answered, `degraded` is true whenever any did not, and `degraded_reason` names them plus how many of the targets were still judged. `None` survives for the case where nothing answered, so callers keep one meaning for "the LLM pass produced nothing". ADR-037 settled the same granularity question for the guardian on the same argument, which is why this follows rather than invents.

**The consequence the first plan missed,** now in the ADR's Negative section: the short-circuit was bounding a broken backend at one call by accident. Running the full loop means a uniformly unresponsive CLI costs N x `llm_timeout_seconds` - on this repository 5 x 120 s. `schemas/adr-kit-config.schema.json` already documents the worst case as "N x this value on a single commit", so this restores the documented bound rather than inventing a cost, but it is a real change and `ADR_KIT_NO_LLM=1` is the per-commit escape.

**Also a contract change worth stating plainly:** `degraded: true` no longer implies `evaluated == []`. It can now coexist with a populated `evaluated` and with a non-zero exit. That shape is new to every consumer, so it is a Must in the ADR's Decision Contract rather than a footnote.

Coverage: `test_one_failed_call_costs_only_that_adrs_verdict` replaces `test_one_failed_call_discards_the_whole_pass` - the old test pinned the behaviour ADR-038 changes, so leaving it would have been pinning the defect. `test_a_pass_where_no_adr_answers_still_degrades_to_none` keeps the None contract honest. The `_make_recording_claude` helper gained an `EXIT:<n>` entry type so a fake CLI can fail the way a real one does. 93 passed in tests/test_adr_judge_llm.py.

C4-Documentation/c4-component-enforcement-engine.md:107 asserted the old contract in almost the docstring's words and now describes the new one, with the old behaviour named as pre-0.50.0 rather than deleted.

**Needs the maintainer:** ADR-038 is Proposed and reads `ready-for-confirmation`. Accepting it is a human action per ADR-027, so the record ships as Proposed and the code implements it; `python bin/adr accept ADR-038 --confirm` closes that.
<!-- SECTION:FINAL_SUMMARY:END -->
