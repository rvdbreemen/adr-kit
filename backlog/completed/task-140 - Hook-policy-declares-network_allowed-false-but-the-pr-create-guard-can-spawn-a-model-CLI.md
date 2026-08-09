---
id: TASK-140
title: >-
  Hook policy declares network_allowed false, but the pr-create guard can spawn
  a model CLI
status: Done
assignee: []
created_date: '2026-08-06 06:06'
updated_date: '2026-08-06 18:33'
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
- [x] #1 One of the three outcomes is chosen and recorded, with the reasoning, rather than the wording being adjusted to fit current behaviour
- [x] #2 `hooks/manifest.json`'s network declaration matches what the code can actually do on every one of the eight events, including `pr-create`
- [x] #3 A test spawns the `pr-create` guard with a backend configured and asserts the declared network property holds — whatever it is declared to be
- [x] #4 If the declaration becomes per-event or conditional, `hooks/manifest.json`'s schema and every reader of the policy block are updated together
- [x] #5 The generated client mirrors carry the same declaration and `python scripts/build-client-adapters.py --check` reports changed=0
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed on `fix/backlog-todo-sweep` (commits 691abe1, fca6d43).

**AC#1 — outcome 2 chosen, per event.** Recorded in **ADR-034** (Accepted at the maintainer's instruction), not reworded into agreement with current behaviour.

**Two premises in this record were wrong, and both changed the answer.**

1. *"With nothing configured, resolve_backend returns None, so the default posture is closed."* Measured against `bin/adr_llm.resolve_llm_backend` on 2026-08-06: with `judge.host_client` recorded in `.adr-kit.local.json` — which the installer and `/adr-kit:init` write — it returns `SubprocessBackend(["claude","-p"])` with `unavailable_reason()` of `None`. The default posture on a normally installed machine is **open**. Tracked `judge.backend: "openrouter"` also reaches out, which ADR-025 expressly permits, so this is not only a machine-local case.

2. *The nudge is the path.* It is the **narrower** path. `judge_branch` spawns `bin/adr-judge` on every `gh pr create`, and ADR-017 made its LLM pass on by default; nothing on the guard's path sets `ADR_KIT_NO_LLM`. `adr-suggest` was double-gated behind `suggest.enabled`/`ADR_KIT_SUGGEST`. So **option 1 was dead**: suppressing the LLM in `_nudge` leaves the larger path untouched, and would also spend ADR-024's argument and the 5000 ms budget ADR-031 bought for exactly this pass.

**A third path the record did not mention.** `user-prompt-submit` is the sole member of `hooks/adr-hook.py`'s `EMBEDDING_EVENTS`; where a vector store exists, `adr_embed_query` loads `bin/adr-embed` outside ADR-018's import gate and posts to `localhost:11434` or to whatever `base_url` names, which ADR-020 permits to be remote. Two events reach out, not one.

**AC#2.** `policy.network_allowed` is now the inherited default; `pr-create` and `user-prompt-submit` override it to `true`, each with a `network_reason` naming what it reaches and under what condition. The other six inherit `false`, and that `false` is structural: they are served by `adr_hook_core.py`, whose ADR-018 gate forbids importing `subprocess`, `socket`, `urllib`, `http`, `ssl` or `asyncio`.

**AC#3.** Four tests in `tests/test_adr_pr_guard.py`: the `true` asserted against a spawned child with a backend configured; `EMBEDDING_EVENTS` read from source so widening it cannot outrun the declaration; the `false` shown structural through the import gate; and the mirrors matched. All verified failing against the flat declaration first.

**AC#4.** No code reads the policy block — it is purely declarative, which is why it drifted. Four C4 documents did repeat it and are corrected, including two further errors found in them: one claimed the judge "stays deterministic by omission" (ADR-017 makes it on by default), and one named `SessionStart` as an embedding event (only `UserPromptSubmit` is).

**AC#5.** `python scripts/build-client-adapters.py --check` reports changed=0.

**Also fixed here, found while tracing the path:** `_nudge` filtered `result.stdout` while `emit_advisory` writes every advisory line to `stderr`, so ADR-024's nudge could never reach a user. It was wired, unit-tested and dead end to end — every test fabricated a result carrying the text on stdout. Now covered by a test driving the real `bin/adr-suggest`.

**Separately, at the maintainer's request:** `adr-suggest` now runs by default (**ADR-035**, Proposed — awaiting acceptance), and `ADR_KIT_SUGGEST_DISABLE` is honoured by the script itself rather than only by the pre-commit template.

**Note for the next ADR:** the generated graph now clears its size budget by 703 bytes on CI. The next record has to pay for itself or the budget needs revisiting.
<!-- SECTION:FINAL_SUMMARY:END -->
