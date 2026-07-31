---
id: TASK-72
title: >-
  adr-suggest still pins a model and reads the deprecated judge.llm_model,
  against ADR-017
status: To Do
assignee: []
created_date: '2026-07-31 04:54'
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
  - bin/adr-suggest
  - docs/adr/ADR-017-run-the-llm-judge-by-default-on-the-host-agent-model.md
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
- [ ] #1 `bin/adr-suggest` resolves its invocation through the same backend registry as `bin/adr-judge`, with no pinned model on the host path
- [ ] #2 `suggest.llm_cmd` and `judge.llm_cmd` no longer supply an argument vector to adr-suggest; a config containing them is ignored with a warning, matching the judge
- [ ] #3 An unavailable backend degrades adr-suggest to a no-op that never blocks a commit, matching ADR-001's guarantee as ADR-017 preserves it
- [ ] #4 ADR-017's Enforcement globs either cover `bin/adr-suggest` or the ADR states explicitly why it is exempt; the current silent gap is closed either way
- [ ] #5 A regression test proves the pin is gone and that a repo-tracked command in either config key is not executed
- [ ] #6 The stale comment claiming the shape is 'identical to adr-judge' is corrected or removed
<!-- AC:END -->
