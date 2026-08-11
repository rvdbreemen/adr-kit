---
id: TASK-169
title: >-
  The installer never records judge.host_client, so the LLM judge is dead by
  default
status: Done
assignee: []
created_date: '2026-08-09 20:38'
updated_date: '2026-08-10 21:03'
labels:
  - bug
  - installer
  - judge
  - adr-drift
dependencies: []
references:
  - >-
    docs/adr/ADR-036-retire-the-vector-layer-and-run-the-judge-on-the-host-model-only.md
  - docs/adr/ADR-017-run-the-llm-judge-by-default-on-the-host-agent-model.md
  - bin/adr_llm.py
  - scripts/install-agent-envs.py
  - skills/init/SKILL.md
modified_files:
  - bin/adr-judge
  - clients/installer/judge_backend.py
  - scripts/install-agent-envs.py
  - tests/test_agent_installer.py
  - tests/test_release_allowlist.py
  - CHANGELOG.md
priority: high
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-036 (Accepted, binding) states the resolution rule plainly:

> **Judge.** `judge.backend` resolves to the host client's CLI recorded at install time (`claude -p`, `codex exec`, `copilot -p`), exactly as ADR-017 shipped it.

ADR-017, which ADR-036 supersedes but explicitly carries forward here, is more direct still:

> Therefore **the installer writes the resolved host command into the client's own configuration at install time**, when the client is known with certainty because the operator named it. `judge.backend: "host"` reads that value; it never probes `PATH` and never guesses.

The installer does not do this. `grep -rn host_client scripts/install-agent-envs.py clients/installer/*.py` returns nothing. The only writer is `bin/adr-judge --set-backend host --host-client <id>`, and the only thing that calls it is a human or an agent working through `/adr-kit:init`, which asks `LLM pass? [1] on (host CLI) [2] off` as an interactive question. `skills/judge/SKILL.md` and `skills/upgrade/SKILL.md` document the same manual command.

Consequence: anyone who installs with `scripts/install-agent-envs.py` and never runs the interactive init gets `judge.backend = host` with no client recorded. Every commit then prints

```
[adr-judge] WARN: judge.backend is 'host' but no client was recorded in .adr-kit.local.json; the LLM pass will not run.
[adr-judge] WARN: LLM pass DEGRADED to declarative-only: no LLM backend is configured
```

and the LLM half of the gate silently never runs. This repository is the proof: `docs/adr/.adr-kit.local.json` here contains only `lifecycle.signer`, and every commit in this session degraded to declarative-only. adr-kit fails to govern itself on exactly the drift it exists to catch.

ADR-017's "never guesses" argument is about probing `PATH` on a machine with three CLIs, where the choice would be a coin flip. It is not an argument against recording the client the operator just named on the command line: `--clients copilot` is not a coin flip.

One design question has to be answered before implementing, and it is why this is a task rather than a one-liner. `judge.host_client` is a single field in a per-project, per-machine file, while `--clients all` installs three clients against that one project. Options worth weighing: write it only when the run selects exactly one client; write it always using a fixed preference order; never overwrite a value that is already there; or make the field per-client and have the judge resolve by whichever client is asking. The last one changes the schema and deserves its own ADR if chosen.

Note for whoever picks this up: check whether ADR-036's Enforcement block should gate this, since the rule it states is currently unimplemented and nothing failed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Installing with scripts/install-agent-envs.py for a single named client records judge.host_client in the project's gitignored docs/adr/.adr-kit.local.json, without an interactive step
- [x] #2 The multi-client case has a decided, documented rule and does not silently pick a winner
- [x] #3 An existing recorded host_client is never overwritten without the operator asking for it
- [x] #4 Regression coverage asserts that a single-client install leaves a resolvable judge backend, so this drift cannot return unnoticed
- [x] #5 docs/adr/.adr-kit.local.json in this repository records a host client and commits stop degrading to declarative-only
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented in the v0.49.0 release (TASK-168) at the maintainer's request.

The design question is answered by refusing to answer it in the ambiguous case, which is what ADR-017's reasoning already required. A run installing exactly one client records it; a run installing several records nothing and prints the per-client command, because picking one would decide which vendor receives the repository diff. An already recorded client is never overwritten - an operator's choice outranks anything an install infers. No schema change, so no new ADR is needed.

The installer must not write the tracked `.adr-kit.json`, which is what `--set-backend host` does (it writes judge.backend there and strips retired keys). Since ADR-036 left exactly one backend - `DEFAULT_BACKEND = BACKEND_HOST`, `BACKEND_NAMES = (BACKEND_HOST,)` - the tracked file needs no edit at all: recording the machine-local client is sufficient for the backend to resolve. So `bin/adr-judge` gained `--record-host-client <id>`, which writes only the gitignored local file through the existing `write_local_host_client` (keeping the git-exclude registration in one place), and `clients/installer/judge_backend.py` calls it. No writer logic is duplicated.

Proven end to end on this repository, which was itself the evidence for the defect:
```
Judge host client: recorded claude-code-cli for D:\...\adr-kit\docs\adr
adr-judge --show-config -> Resolved backend: host (claude-code-cli): claude -p
```
and `lifecycle.signer` survived the merge into the local file untouched.

Criterion #4's regression asserts the property rather than the file: it records a client into a temporary project, then runs the real `bin/adr-judge --show-config` against it and requires a resolved backend with no 'no client was recorded' warning. Three more tests cover the multi-client refusal (no subprocess runs, all three commands printed), the no-overwrite rule, and that the tracked config is never created.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.49.0. The installer now records the judge host client, so the LLM pass is on after an install instead of silently off.

ADR-036 states that `judge.backend` resolves to the host client's CLI "recorded at install time" and ADR-017 said the installer writes it. No installer ever did - drift between a binding ADR and the code, in the repository that dogfoods the kit. Anyone who installed without walking through the interactive `/adr-kit:init` got `judge.backend = host` with no client recorded, and every commit degraded to declarative-only behind two warnings.

The ambiguous case is answered by refusing to answer it, which is what ADR-017's own reasoning required: a run installing exactly one client records it; a run installing several records nothing and prints the command per client, because choosing would decide which vendor receives the repository diff. An already recorded client is never overwritten.

The tracked `.adr-kit.json` is never touched. `--set-backend host` writes there, but since ADR-036 left exactly one backend, recording the machine-local client is sufficient for it to resolve - so `bin/adr-judge` gained `--record-host-client <id>`, writing only the gitignored local file through the existing writer.

Criterion 4 was implemented at the time and is verified now: `test_a_single_client_install_leaves_a_resolvable_judge_backend` records a client into a temporary project, runs the real `bin/adr-judge --show-config` against it, and requires a resolved backend with no "no client was recorded" warning. It asserts the property rather than the file, so the drift cannot return unnoticed. Three sibling tests cover the multi-client refusal, the no-overwrite rule, and that the tracked config is never created. 3 passed.

The task sat In Progress after the release only because the tick was never set; nothing was outstanding.
<!-- SECTION:FINAL_SUMMARY:END -->
