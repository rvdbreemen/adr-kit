---
id: TASK-72
title: >-
  adr-suggest still pins a model and reads the deprecated judge.llm_model,
  against ADR-017
status: Done
assignee: []
created_date: '2026-07-31 04:54'
updated_date: '2026-07-31 05:49'
labels:
  - judge
  - adr-017
  - bug
dependencies: []
references:
  - 'bin/adr-suggest:85'
  - docs/adr/ADR-017-run-the-llm-judge-by-default-on-the-host-agent-model.md
  - 'bin/adr-judge:590'
modified_files:
  - bin/adr_llm.py
  - bin/adr-suggest
  - bin/adr-judge
  - docs/adr/ADR-017-run-the-llm-judge-by-default-on-the-host-agent-model.md
  - schemas/adr-kit-config.schema.json
  - tests/test_adr_suggest.py
priority: high
ordinal: 77500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-017 removed the pinned model and replaced repository-supplied commands with a code-side backend registry. `bin/adr-judge` implements that. **`bin/adr-suggest` does not**, and ADR-017 names `adr-suggest` in its `components` list, so it is in scope for the decision rather than adjacent to it.

`bin/adr-suggest:85` still reads:

```python
# Default LLM invocation — identical shape to adr-judge. Overridable via
# --llm-cmd, ADR_KIT_LLM_CMD env, or .adr-kit.json suggest.llm_cmd / judge.llm_cmd.
DEFAULT_LLM_CMD = ["claude", "-p", "--model", "claude-sonnet-4-6"]
```

Three separate problems in those four lines:

1. **The model is pinned.** ADR-017's Decision is that the host backend passes no model flag so each CLI resolves the model its user configured. A user on Codex or Copilot gets a judge matching their agent and a suggester that silently calls Claude.
2. **The comment is now false.** It claims the shape is "identical to adr-judge"; adr-judge's `DEFAULT_LLM_CMD` is gone, replaced by `BACKENDS` at `bin/adr-judge:590`.
3. **It reads config keys the judge now refuses.** `suggest.llm_cmd` / `judge.llm_cmd` are exactly the repository-supplied argument vectors ADR-017's Must Not forbids. The judge ignores them with a warning; adr-suggest still honours them, so the guarantee "repository-tracked configuration may never introduce a command" holds for one entry point and not the other.

**Why the enforcement floor did not catch it.** ADR-017's `forbid_pattern` is scoped `path_glob: {bin,codex/bin,copilot/bin}/adr-judge`, so `bin/adr-suggest` is outside every rule. The ADR governs it by `components` but enforces nothing on it. That gap is worth fixing in the same change: either widen the glob or state in the ADR why adr-suggest is exempt.

Found by the TASK-59 implementer while closing out the backend registry, and confirmed by reading the file.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `bin/adr-suggest` resolves its invocation through the same backend registry as `bin/adr-judge`, with no pinned model on the host path
- [x] #2 `suggest.llm_cmd` and `judge.llm_cmd` no longer supply an argument vector to adr-suggest; a config containing them is ignored with a warning, matching the judge
- [x] #3 An unavailable backend degrades adr-suggest to a no-op that never blocks a commit, matching ADR-001's guarantee as ADR-017 preserves it
- [x] #4 ADR-017's Enforcement globs either cover `bin/adr-suggest` or the ADR states explicitly why it is exempt; the current silent gap is closed either way
- [x] #5 A regression test proves the pin is gone and that a repo-tracked command in either config key is not executed
- [x] #6 The stale comment claiming the shape is 'identical to adr-judge' is corrected or removed
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Done. The agent had not sent a final report when I closed this, so everything below is my own verification against the running code.

**The fix shares code rather than duplicating it.** A new `bin/adr_llm.py` holds the backend registry, and both `bin/adr-judge` and `bin/adr-suggest` load it as a sibling. That is the right call: two divergent registries would have been worse than the single violation this task described, and `bin/adr-suggest:144` records that a copy of this logic is exactly what drifted in the first place.

`bin/adr-suggest` now carries **zero** occurrences of `claude-sonnet-4-6` or `DEFAULT_LLM_CMD`. Its module docstring states the precedence explicitly — `--llm-cmd` > `ADR_KIT_LLM_CMD` > `judge.backend` — and why the split exists: the first two come from the operator running the command, the third from whoever last opened a pull request.

**The three security properties, each verified by attack rather than by reading:**

| Test | Result |
|---|---|
| `judge.openrouter_api_key` in committed `.adr-kit.json` | **exit 2**, names `$.judge.openrouter_api_key`, says the key is already published and must be rotated |
| `judge.backend: openrouter` with no key in the environment | **exit 0** — degrades, never blocks |
| `suggest.llm_cmd` carrying a real payload that writes a file | **payload never executed** |

That last one is the one worth running rather than reasoning about. I put an actual command vector in the committed config, pointed at a file it would create, and confirmed the file does not exist afterwards. The guarantee "repository-tracked configuration may never introduce a command" now holds at both entry points, not just the judge.

The asymmetry is preserved and is correct: a published credential **blocks**, because it is a user error that has to be seen; an unavailable backend **degrades**, because that is tooling drift and ADR-001's guarantee — which ADR-017 explicitly keeps — is that it never blocks a commit.

**Criterion #4, the enforcement gap, is closed properly.** ADR-017's globs were `{bin,codex/bin,copilot/bin}/adr-judge`, so `bin/adr-suggest` sat outside every rule — the ADR governed it through `components` and enforced nothing, which is precisely how this survived. The globs are now `{bin,codex/bin,copilot/bin}/adr{-judge,-suggest,_llm.py}`, and a second rule forbids `DEFAULT_LLM_CMD` in any entry point, with the message pointing at `bin/adr_llm.py` as the only place a command, endpoint or model may live. So the specific mistake this task fixed cannot recur silently in any of the three executables across any of the three distributions.

Editing the Enforcement block of an Accepted ADR is sanctioned here: ADR-016 records that adding a declarative rule later is "a mechanical tightening rather than a change to the decision". No Decision, Context, Consequences or Alternatives text was touched.

**Verification:** `bin/adr-judge --dry-run-enforcement ADR-017` 0/0. Full working-tree diff through the enforcement floor: 0 violations, 0 advisory. `bin/adr-lint --strict docs/adr` 17/17 PASS. Mirrors in sync, `--check` reports changed=0. Full suite **1224 passed, 11 skipped, 0 failed**.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
