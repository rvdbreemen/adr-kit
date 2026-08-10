---
id: TASK-170
title: One ADR yields no usable verdict and degrades the whole LLM pass
status: To Do
assignee: []
created_date: '2026-08-09 21:28'
labels:
  - judge
  - llm
dependencies: []
references:
  - bin/adr_llm.py
  - bin/adr-judge
  - >-
    docs/adr/ADR-037-keep-per-adr-judge-verdicts-in-the-advisory-per-machine-guardian-state.md
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
- [ ] #2 It is decided and recorded whether one unusable verdict should degrade the whole pass or only that ADR, with the reasoning written down
- [ ] #3 If per-ADR degradation is chosen, a run where one ADR fails still reports the verdicts of the others
- [ ] #4 Regression coverage pins whichever behaviour is chosen
<!-- AC:END -->
