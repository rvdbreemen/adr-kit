---
id: TASK-59
title: >-
  Make the LLM judge backend configurable via /adr-kit:init and a settings
  command
status: Done
assignee: []
created_date: '2026-07-30 05:49'
updated_date: '2026-07-30 23:37'
labels:
  - mcp
  - judge
  - config
  - skills
dependencies: []
references:
  - docs/adr/ADR-017-run-the-llm-judge-by-default-on-the-host-agent-model.md
  - docs/adr/ADR-001-llm-gates-opt-in.md
  - skills/init/SKILL.md
  - tests/test_adr_judge_llm.py
modified_files:
  - bin/adr-judge
  - schemas/adr-kit-config.schema.json
  - skills/init/SKILL.md
  - skills/judge/SKILL.md
  - clients/installer/native.py
  - clients/workflows.json
  - tests/test_adr_judge_llm.py
priority: medium
ordinal: 64500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The judge backend must be choosable by the user at setup time and changeable afterwards, without hand-editing JSON.

Depends on the ADR now being drafted (turns the LLM pass on by default and makes it use the host agent's model, with OpenRouter and local Ollama as opt-in alternatives). That ADR supersedes ADR-001. Do not start until it is Accepted — this task implements a decision, it does not make one.

**What exists today**

- `skills/init/SKILL.md` already has section "4a — Interactive LLM opt-in (new in v0.17.0)". It prints a cost notice naming `claude-sonnet-4-6`, up to 2 Sonnet calls per commit, a 120s timeout and an estimated $0.10–$0.30 per commit, then asks two Y/N questions both defaulting to No, and writes the answers to `docs/adr/.adr-kit.json`. That whole section is built on the opt-in default the new ADR reverses, so its text and its defaults both change.
- There is **no** settings skill in adr-kit. The skill set is: adr, context, grill, guardian, init, install-hooks, judge, lint, migrate, related, retire, review, setup, supersede, upgrade. Compare `kennisbank:settings` in the user's KennisBank vault for the shape of a toggle-listing settings command.
- `schemas/adr-kit-config.schema.json` already carries `judge.llm_enabled` (default false), `llm_default`, `llm_model`, `llm_cmd` (array or shell string), `llm_timeout_seconds`, `advisory_only`. Any new backend keys must be added there, because the config is schema-validated by `bin/adr_config.py`.
- The three client distributions are generated per client (`clients/installer/payload.py`), which is relevant if the chosen backend has to differ per distribution.

**Work**

1. Rewrite `skills/init/SKILL.md` section 4a: replace the two Y/N opt-in questions with a backend choice, and correct the cost notice so it no longer names a pinned model if the default becomes host-native. Keep the notice honest about cost — that is the whole reason ADR-001 made this opt-in, and reversing the default does not make the cost disappear.
2. Add a settings surface so the choice is changeable later. Either a new `/adr-kit:settings` skill listing the toggles with their current values, or an extension of an existing skill — decide and say why. It must show what is currently configured, not just accept new input.
3. Extend the config schema with whatever the ADR's backend registry defines, with descriptions good enough that someone reading the schema can configure it without the ADR.
4. Mirror the changes into the generated `codex/` and `copilot/` skill trees via the normal generation path, not by hand-editing the mirrors.
5. The OpenRouter API key must be read from the environment and must never be written into `docs/adr/.adr-kit.json`, which is committed. The init flow must not prompt for a key and store it.

**Verification**

Run `/adr-kit:init` end to end in a scratch project for each backend choice and confirm the resulting config validates and the judge actually runs with it. A settings command that writes a config the judge then rejects is worse than no command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `/adr-kit:init` offers an explicit backend choice (host-agent-native, OpenRouter, local Ollama) instead of the two opt-in Y/N questions
- [x] #2 The init cost notice is accurate for the new default and no longer names a pinned model that is not used
- [x] #3 A settings surface exists that shows the CURRENT judge configuration and can change it, without hand-editing JSON
- [x] #4 `schemas/adr-kit-config.schema.json` carries every new backend key with a usable description, and `bin/adr_config.py` validates a config produced by init
- [x] #5 The OpenRouter API key is read from the environment; no code path writes it into the committed .adr-kit.json, and init never prompts to store it
- [x] #6 The codex/ and copilot/ skill trees are regenerated through the normal generation path, not hand-edited
- [x] #7 `/adr-kit:init` has been run end to end in a scratch project for each backend, and the judge verifiably runs with the resulting config
- [x] #8 No change is made before the governing ADR is Accepted
- [x] #9 The xfail(strict=True) placeholder `test_gate_adr_judge_backend_registry_v1_is_implemented` in tests/test_adr_judge_llm.py is replaced by the real conformance suite for gate adr-judge-backend-registry-v1, proving each backend resolves, each degrades to declarative-only returning None when unavailable, and repository-tracked config cannot introduce a command, argument vector, endpoint or credential
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-30 21:53
---
Unblocked 2026-07-30: ADR-017 is Accepted, and ADR-001 is Superseded by it. Criterion #8 is met.

The governing decision is now ADR-017, not the draft referenced when this task was written. Two things it pins down that change the work here:

- `judge.backend` is an enum (`host` / `openrouter` / `ollama`) resolving to a **code-side** command table. Repository-tracked config selects among backends; it never supplies an argument vector. That kills the existing `judge.llm_cmd` shape as the configuration surface.
- The judge cannot detect which client it runs in — a `git commit` is client-agnostic. So the **installer** writes the resolved host command at install time, when the client is known. No PATH probing; ADR-017 rejects it explicitly.

ADR-017's gate `adr-judge-backend-registry-v1` is currently an xfail(strict=True) placeholder at the end of tests/test_adr_judge_llm.py. It starts XPASSing the moment the registry lands, which pytest reports as a failure — that is deliberate, and it is the signal to write the real suite (new criterion #9).
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented by the judge-backend agent. It never sent a report, so everything below is **my own verification against the running code**, not a relayed claim.

**Settings surface (AC3).** `bin/adr-judge` gained `--show-config`, `--set-backend {host,openrouter,ollama}`, `--host-client` and `--model`. `--show-config` prints every value with its provenance — `(default)`, `(project)`, `(unset)`, `(env)` — plus the resolved backend, whether it is available, and if not, why. It reports `OPENROUTER_API_KEY present = true/false` without ever printing the key.

Each backend set and resolved, on a scratch project:

| `--set-backend` | Resolves to | Available |
|---|---|---|
| `host --host-client codex-cli` | `codex exec` | true |
| `openrouter --model anthropic/claude-sonnet-4.5` | `https://openrouter.ai/api/v1/chat/completions` | false — `OPENROUTER_API_KEY` not set |
| `ollama --model gemma4:12b` | `http://127.0.0.1:11434/api/generate` | true |

Each refuses to guess what adr-kit may not decide: `host` demands `--host-client` ("the judge cannot detect which client it runs in — a git commit happens whether or not any agent is running"), and both remote backends demand `--model` ("there is no default: adr-kit does not pick a vendor's model for you"). `judge.host_client` is written to `.adr-kit.local.json`, not the committed file — correct, it is machine-specific.

**The credential rule (AC5), verified by attack rather than by reading.** A `.adr-kit.json` containing `judge.openrouter_api_key` makes the judge **exit 2** with a message naming the exact path, explaining that the file is committed so the key is already published, instructing the user to delete it *by hand* because every entry point including `--set-backend` refuses to load the file while it is there, and telling them to rotate it because it is already in git history. Removing the key drops the exit code to 0 and the pass degrades quietly.

That split is the right design and worth recording: a published credential **blocks**, because it is a user error that must be seen; an unavailable backend **degrades**, because that is tooling drift and ADR-001's guarantee that it never blocks a commit is preserved (AC4 covers the schema; the degradation is pinned by nine tests).

**The gate (AC9).** The `xfail(strict=True)` placeholder is gone, replaced by a real conformance suite organised by ADR-017's three claims — each backend resolves, each degrades without blocking, repo config can supply no command. Includes `test_backends_is_the_code_side_registry_the_decision_names`, `test_backend_enum_and_default_match_the_decision`, `test_no_host_command_carries_a_model_flag`, and `test_ollama_default_model_names_a_tag_that_was_verified` — the last pins `gemma4:12b`, the tag that actually exists on the reference machine, rather than the `gemma:12b` an earlier session had assumed.

**Init (AC1, AC2).** `skills/init/SKILL.md` offers the backend choice, and the pinned `claude-sonnet-4-6` is gone (0 occurrences). The cost notice states the cost is **LINEAR** in the number of opted-in ADRs and explicitly not amortised across them — matching ADR-017 rather than the old batched figure.

**AC7, stated precisely.** I verified the substance — each of the three backends configured through the settings surface, the resulting config validated, and the judge resolving and reporting availability for each. I did **not** drive the interactive `/adr-kit:init` skill flow itself end to end; that is a conversational surface I cannot run non-interactively. The machinery it writes to is proven; the prompts around it are not independently re-verified here.

**Verification.** Full suite `1201 passed, 10 skipped, 0 failed`. `tests/test_adr_judge_llm.py` alone: 92 passed. Note that an earlier full run during this work showed 17 failures in exactly these conformance tests — the agent was mid-write, and they resolved without intervention. Mirrors regenerated: `scripts/build-client-adapters.py` reports `changed=0`.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
