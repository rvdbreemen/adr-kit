---
id: TASK-140
title: >-
  Hook policy declares network_allowed false, but the pr-create guard can spawn
  a model CLI
status: To Do
assignee: []
created_date: '2026-08-06 06:06'
labels:
  - hooks
  - policy
  - defect
  - governance
dependencies: []
references:
  - 'hooks/manifest.json:6'
  - 'hooks/adr_pr_guard.py:191'
  - 'hooks/adr_pr_guard.py:205-222'
  - 'bin/adr-suggest:547'
  - 'bin/adr-suggest:748'
  - docs/adr/ADR-024-ask-for-a-missing-adr-at-the-pull-request-moment.md
  - >-
    docs/adr/ADR-025-separate-what-tracked-configuration-may-select-from-what-only-a-machine-may-introduce.md
priority: high
ordinal: 111500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`hooks/manifest.json:6` declares a flat policy:

```json
"policy": { "fail_open": true, "network_allowed": false, "future_clients_allowed": false }
```

The `pr-create` event can reach the network anyway.

**The path.** `hooks/adr_pr_guard.py:_nudge()` (added for ADR-024) spawns `bin/adr-suggest` as a subprocess with `--diff -`, `--adr-dir` and `--llm-timeout`. `bin/adr-suggest` calls `run_llm_suggest(prompt, backend, llm_timeout_s)` at `:748` **unconditionally** — there is no `if args.llm:` guard and no `ADR_KIT_NO_LLM` check on that path. Whether anything leaves the machine therefore depends entirely on whether `resolve_backend()` (`:547`) finds one, and its precedence is `--llm-cmd` > `ADR_KIT_LLM_CMD` env > `judge.backend`.

The guard's own comment acknowledges the child process reaches a model: "killing the child does not reach the model CLI it spawned".

**How bad is it, stated precisely.** With nothing configured, `resolve_backend` returns `None` and no network call happens, so the default posture is closed. This is a *declaration* defect rather than an unconditional leak: the manifest states a flat property that is conditionally false. Declared properties are what integrators and reviewers rely on, and `network_allowed: false` reads as a guarantee, not a default.

ADR-025 is the relevant governance: it separates what tracked configuration may select from what only a machine may introduce. `ADR_KIT_LLM_CMD` is exactly the machine-introduced case, and the hook policy does not model it.

**Decide, do not just reword.** Three coherent outcomes, and the task is to pick one:

1. The policy is right and the code is wrong — the nudge path suppresses the LLM (pass a no-LLM flag, or have `_nudge` call a declarative-only mode). `pr-create` then genuinely makes no network call.
2. The code is right and the policy is wrong — `network_allowed` becomes per-event, and `pr-create` declares `true` with the condition stated. Every other event keeps `false`.
3. The property is conditional by nature and the schema should say so — e.g. `network_allowed: "only-when-backend-configured"` — with the gate reading it that way.

Option 1 is the smallest change but removes the LLM from the moment ADR-024 argued it is most useful, so it is not obviously right.

Found while refreshing the C4 architecture documentation, by an agent that traced the claim rather than repeating it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One of the three outcomes is chosen and recorded, with the reasoning, rather than the wording being adjusted to fit current behaviour
- [ ] #2 `hooks/manifest.json`'s network declaration matches what the code can actually do on every one of the eight events, including `pr-create`
- [ ] #3 A test spawns the `pr-create` guard with a backend configured and asserts the declared network property holds — whatever it is declared to be
- [ ] #4 If the declaration becomes per-event or conditional, `hooks/manifest.json`'s schema and every reader of the policy block are updated together
- [ ] #5 The generated client mirrors carry the same declaration and `python scripts/build-client-adapters.py --check` reports changed=0
<!-- AC:END -->
