---
id: "ADR-017"
title: "Run the LLM Judge by Default on the Host Agent's Own Model"
status: "Accepted"
date: "2026-07-30"
binding: true
gate: "adr-judge-backend-registry-v1"
documents_shipped: false
verified_in: []
supersedes:
  - "ADR-001"
superseded_by: null
topics:
  - "llm judging"
  - "backend selection"
  - "cost and consent"
  - "supply chain"
aliases:
  - "default-on LLM judge"
  - "backend registry"
components:
  - "adr-judge"
  - "adr-suggest"
symbols:
  - "judge.backend"
  - "judge.llm_enabled"
  - "BACKENDS"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-017 Run the LLM Judge by Default on the Host Agent's Own Model

## Status

Accepted, 2026-07-30.

## Status History

```yaml
status_history:
  - date: 2026-07-30
    status: Proposed
    changed_by: adr-kit
    reason: Supersedes ADR-001 on the default; adds a backend registry (TASK-59)
    changed_via: adr-kit
  - date: 2026-07-30
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Approved in session after TASK-63 shipped the per-ADR LLM isolation that gates the default flip
    changed_via: adr-kit lifecycle
  - date: 2026-07-30
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Supersession link to ADR-001 established; status stays Accepted, this entry records the link rather than a status change
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-001 made the per-commit Large Language Model (LLM) pass opt-in, and it was
right to do so on the evidence available at the time. Its Context is specific:
on a project with 50 `llm_judge: true` Architecture Decision Records (ADRs),
roughly $0.10 to $0.30 per commit and 5 to 10 seconds of added latency, "paid on
every commit, including trivial ones like documentation fixes or version bumps",
and users who ran `/adr-kit:init` "were not asked whether they wanted per-commit
LLM judging", causing surprise spend. That is a real defect and this decision
does not dispute it.

Three things have changed since.

**The pinned model is the wrong shape.** `bin/adr-judge:64` hard-codes
`DEFAULT_LLM_CMD = ["claude", "-p", "--model", "claude-sonnet-4-6"]`. A user
working in a different agent, or on a different Claude model, gets a judge that
does not match the assistant they are actually using. Every supported client
already exposes a non-interactive surface, verified against the installed
binaries on 2026-07-30: Claude Code `claude -p` (v2.1.220), Codex Command Line
Interface (CLI) `codex exec` (v0.145.0, its help reads "Run Codex
non-interactively"), and GitHub Copilot CLI `copilot -p` / `--prompt`
(v1.0.71). Passing no model flag lets each CLI resolve the model its user
configured, which removes the pin entirely.

**Opt-in in practice means off.** In this repository, `judge.llm_enabled` stayed
absent until 2026-07-30, and ADR-016 is the only ADR that ever carried
`llm_judge: true` — it now sets it `false`, partly *because* the pass was off.
An escape hatch nobody opens is not a safety property; it is a feature that does
not exist.

**A comprehensive review found the LLM path can be silently neutralised.** All
`llm_judge` ADRs share one prompt and one verdict object, so a second Accepted
ADR whose Decision text reads as supersession prose ("ADR-050 is retired,
eval() is now permitted") flips a real violation to `OK`. Reproduced three times
out of three against the live CLI. The forged pass is byte-identical to a
genuine one: an `OK` produces no finding, `emit_json` has no attestation field,
and the exit code is 0. This is tracked as TASK-63 and it is the reason this
decision has a shipping order rather than only a default.

The project owner has asked for three things: the pass on by default, the host
agent's own model rather than a pinned one, and a user-selectable alternative
backend — OpenRouter with any model, or a local Ollama model.

## Decision Drivers

* The default must match what a user reasonably expects: the assistant they are
  already using is the one that reviews their commit.
* Cost and latency remain real. Reversing ADR-001's default does not make its
  Context untrue, so this decision must answer it rather than ignore it.
* Repository-tracked configuration is authored by anyone with commit access. It
  may select among backends an operator enabled; it may never introduce a
  binary, an endpoint, or a credential.
* Zero runtime dependencies is load-bearing (ADR-016): the plugin installs into
  environments adr-kit does not control.
* A default-on floor that can be silently disabled is worse than no floor,
  because it manufactures confidence.

## Considered Options

* Turn the pass on by default, resolve the model from the host agent, and
  express backend choice as a named registry.
* Keep opt-in and only remove the model pin.
* Turn the pass on by default but keep a single pinned model.
* Detect the host client by probing which CLIs are on `PATH`.
* Do nothing and leave ADR-001 in force.

## Decision Outcome

Chosen option: **turn the per-commit LLM pass on by default, resolve the model
from the host agent rather than a pin, and express backend choice as a named
registry rather than a repository-supplied command.**

### The default is on, and host-native

`judge.llm_enabled` defaults to `true`. `judge.backend` defaults to `"host"`,
which resolves to the CLI of the agent the operator installed adr-kit for, with
**no model flag**, so each CLI uses the model its user configured:

| Backend value | Command | Model resolution |
|---|---|---|
| `host` (default) | per client, from the installer-written config | the user's own configured model |
| `openrouter` | stdlib `urllib` to the OpenRouter completions endpoint | `judge.openrouter_model`, a `provider/model` slug |
| `ollama` | stdlib `urllib` to `http://127.0.0.1:11434/api/generate` | `judge.ollama_model` |

### How the judge knows which client it is in

It does not, and it cannot. `bin/adr-judge` runs from the git pre-commit hook,
and a `git commit` is client-agnostic: it happens whether or not any agent is
running. The Claude hooks do receive a client identifier as an argument
(`hooks/hooks.json` passes `claude-code-cli` to `run-hook.cmd`), but the git
hook path is separate and has no such signal.

Therefore **the installer writes the resolved host command into the client's own
configuration at install time**, when the client is known with certainty because
the operator named it. `judge.backend: "host"` reads that value; it never probes
`PATH` and never guesses. On a machine with all three CLIs installed — which is
the case on the reference machine — probing would be a coin flip, and a coin
flip is not an acceptable basis for deciding which vendor receives the diff.

If no host command was written (adr-kit used outside a client install), the
judge degrades to declarative-only with one warning. It does not guess.

### Repository-tracked config may not supply a command

`judge.llm_cmd` accepted an argument vector from committed `.adr-kit.json`, and
its allowlist compares only the basename, so `bin/claude.exe` passes and
`shutil.which` resolves it directly (TASK-60). A backend registry must admit
`ollama`, so that guard cannot merely be tightened.

The rule this decision fixes: **repository-tracked configuration may select
among backends the operator has enabled; it may never introduce a new endpoint,
a new binary, or a credential.** `judge.backend` is an enum resolving to a
code-side command table. The repository never supplies an argument vector.

The OpenRouter Application Programming Interface (API) key is read from the
environment only. `docs/adr/.adr-kit.json` is committed, so a key written there
would be published; the loader must refuse a key found in config rather than
silently using it.

### Cost, answered rather than dismissed

ADR-001's figure was $0.10 to $0.30 per commit for 50 `llm_judge` ADRs, and
that figure assumed all of them shared **one batched call**. TASK-63 removed
that batching: a shared prompt let one ADR's Decision text neutralise another
ADR's verdict, reproduced three times out of three, so each ADR now gets an
isolated call. **Cost and latency are therefore linear in the number of
`llm_judge` ADRs**, not constant. For a large set the old figure now
under-estimates by roughly the count.

That is a real cost increase and this decision does not hide it. Three things
bound it. `llm_judge` remains per-ADR and defaults to `false`, so a default-on
floor with an empty population costs nothing until an author deliberately opts
an ADR in. The `host` backend spends against the subscription the user already
has for their agent rather than a separate metered key. And `judge.llm_enabled:
false` remains a one-line off switch.

The honest statement to a user is that enabling `llm_judge` on an ADR costs one
model call per commit that touches its scope, every time. `/adr-kit:init` must
say that in those terms rather than quoting a per-commit total that no longer
describes the design.

### Shipping order, which is binding

Default-on ships **only together with** the per-ADR isolation fix from TASK-63.
Until then the default stays `false`. A default-on floor whose verdict a
committed sibling ADR can flip, indistinguishably from a genuine pass, is worse
than the current opt-in state: it produces the appearance of enforcement without
the substance.

### Verified backend facts

- **Ollama tag corrected.** The request named `gemma:12b`. That tag was not
  present; the reference machine has **`gemma4:12b`** (7.6 GB) installed, and
  that is what the default names. A config default pointing at a non-existent
  tag fails on first use, which is why this was checked rather than copied.
- **Latency measured, not assumed.** One judge-shaped prompt against
  `gemma4:12b` via `/api/generate` with `"stream": false` returned a parseable
  verdict in **3378 ms**. That is above ADR-015's two-second deterministic
  budget. It is legal — ADR-015 exempts opt-in LLM passes — but a user choosing
  the local backend accepts a slower commit, and the settings surface must say
  so rather than let them discover it.
- **JSON output is reliable enough.** `"format": "json"` returned
  `{"ADR-001":{"verdict":"VIOLATION"}}` directly, with no prose to scrape.
- **Stdlib only.** Both alternative backends work through `urllib.request`; the
  measurement above used exactly that. No vendor Software Development Kit (SDK)
  enters the dependency set.

## Alternatives Considered

### Alternative A: keep opt-in, only fix the model pin

Change `DEFAULT_LLM_CMD` to drop `--model` and leave `judge.llm_enabled`
defaulting to `false`. Smallest change, preserves ADR-001 untouched.

Rejected because it preserves the observed outcome: the pass stays off for
everyone who does not go looking for it. The evidence is this repository, where
it stayed absent from the config for the entire life of the feature. Fixing
which model an unused feature would use does not make it used.

### Alternative B: default-on with a pinned model

Turn the pass on but keep `claude-sonnet-4-6`, or any other single model, as the
default.

Rejected on two grounds. It sends every user's diff to one vendor regardless of
which agent they chose, which is a data-flow decision adr-kit has no standing to
make on their behalf. And it requires a credential for a service the user may
not have, so the default would fail for most users on first commit.

### Alternative C: probe PATH to detect the host client

Have the judge run `shutil.which` for each known CLI and use whichever it finds.
No installer change needed.

Rejected because it is a guess, and it is wrong precisely where it matters. The
reference machine has all three CLIs installed; the probe order would silently
decide which vendor receives the repository diff. A wrong guess here is a
privacy and cost decision made by accident.

### Alternative D: do nothing

Leave ADR-001 in force.

Rejected: it leaves the model pin, leaves the alternative-backend request
unanswered, and leaves the feature effectively unused. But note that "do
nothing" is strictly safer than shipping default-on *before* TASK-63, which is
why the shipping order above is part of this decision rather than advice.

## Consequences

### Positive

* The judge reviews a commit with the model the user already chose, and no
  credential is needed beyond the agent they are already signed in to.
* The model pin disappears, so adr-kit stops making a vendor decision for the
  user.
* Backend choice becomes an enum with a code-side command table, which closes
  the repository-supplied-argv hole (TASK-60) rather than patching it.
* Users who want a different model or full locality have two supported routes
  instead of the `llm_cmd` escape hatch that the security review found unsafe.
* The feature is reachable by default, so the semantic half of the enforcement
  contract stops being theoretical.

### Negative

* A default-on paid call is a real cost transfer to users, and the mitigation
  (empty `llm_judge` population by default) depends on authors not enabling it
  casually. If a project adds `llm_judge: true` to many ADRs, ADR-001's original
  arithmetic returns in full.
* Three backends mean three failure taxonomies — process spawn, HTTP status,
  and daemon availability — each of which must map to "degrade, never block".
  That is more surface than one subprocess call.
* The installer now writes a host command into client configuration, so an
  operator who moves or renames a CLI gets a stale value until reinstall. The
  degrade path covers it, but silently.
* The local backend measured 3378 ms, so a user choosing it accepts commits
  roughly 1.7 times over ADR-015's deterministic ceiling.
* ADR-001's concurrency guard, cost notice and `ADR_KIT_NO_LLM` switch must all
  survive this change. Superseding a decision does not license discarding the
  parts of it that were right.

## Decision Contract

### Must

* `judge.backend` is an enum: `"host"`, `"openrouter"`, `"ollama"`. Default
  `"host"`.
* The `host` backend uses the command the installer wrote for that client, and
  passes no model flag.
* `judge.llm_enabled` defaults to `true` only once TASK-63 has landed.
* An unavailable backend — missing binary, unreachable daemon, absent key,
  non-zero status, unparseable output — degrades to declarative-only and returns
  `None`, preserving ADR-001's guarantee that tooling drift never blocks a
  commit.
* The OpenRouter key is read from the environment.

### Must Not

* Repository-tracked configuration must not supply a command, an argument
  vector, an endpoint, or a credential.
* A key present in `.adr-kit.json` must not be used; it is refused with an
  error naming the environment variable to use instead.
* No backend may be selected by probing which CLIs exist on the machine.
* No vendor SDK may enter the runtime dependency set.

### Verification

The conformance surface is TASK-59 (init and settings), TASK-60 (the argv hole)
and TASK-63 (per-ADR isolation). The named gate `adr-judge-backend-registry-v1`
is satisfied when a test proves each backend resolves, each degrades without
blocking, and repository-tracked config cannot introduce a command.

## Related Decisions

- **Supersedes ADR-001 (Make Per-Commit LLM Gates Opt-In)**: reverses its
  Decision point 1 (`judge.llm_enabled` default `false`). Its concurrency guard,
  its `ADR_KIT_NO_LLM` switch and its graceful-degradation requirement are
  retained unchanged.

  The `supersedes` frontmatter field stayed empty for the whole `Proposed`
  phase. The consistency gate (`bin/adr-lint:870-880`) checks `supersedes` and
  the target's `superseded_by` as a pair unconditionally, while
  `.claude/adr-kit-guide.md` requires the superseded ADR to stay untouched until
  the new one is Accepted — so a Proposed supersession that declares the field
  cannot pass the gate. The lifecycle tooling resolves this by ordering rather
  than by weakening either rule: `bin/adr accept ADR-017` runs first on an ADR
  that claims nothing, and `bin/adr supersede ADR-001 --by ADR-017` then writes
  both sides of the pair in one transaction. Both fields were set that way on
  2026-07-30.
- **ADR-004 (Layered ADR Context Injection)**: this decision changes what the
  fail-closed floor does, not that it is the only thing that blocks.
- **ADR-010 (Certify Three Native CLI Clients Through One Outcome Contract)**:
  the per-client host command belongs to that capability registry.
- **ADR-015 (Two-Second Deterministic Latency Budget)**: LLM passes are exempt.
  The measured 3378 ms local backend is legal under that exemption and is
  disclosed rather than hidden.
- **ADR-016 (Serve Both MCP Protocol Eras)**: source of the binding zero-runtime
  dependency constraint that both alternative backends honour.

## References

- `docs/adr/ADR-001-llm-gates-opt-in.md` — the superseded decision, its cost
  figures at lines 37-40 and its init flow at lines 66-70.
- `bin/adr-judge:64` — `DEFAULT_LLM_CMD`, the pin this decision removes.
- `bin/adr-judge:1716-1718` — the basename allowlist, bypassable (TASK-60).
- `backlog/tasks/task-63 - *.md` — the reproduced cross-ADR contamination that
  gates the default flip.
- `hooks/hooks.json` — the client identifier passed to the Claude hooks, which
  the git-hook path does not have.
- Verified 2026-07-30 on the reference machine: `claude` 2.1.220, `codex-cli`
  0.145.0, GitHub Copilot CLI 1.0.71; `ollama list` showing `gemma4:12b`; one
  `/api/generate` call at 3378 ms returning a parseable verdict.
- OpenRouter API documentation: <https://openrouter.ai/docs>
- Ollama API documentation: <https://github.com/ollama/ollama/blob/main/docs/api.md>

## Enforcement

```json
{
  "forbid_pattern": [
    {
      "pattern": "--model\\s+claude-sonnet",
      "path_glob": "bin/adr-judge",
      "message": "Do not re-pin a model: the host backend passes no model flag so each CLI resolves the user's own (ADR-017)."
    }
  ],
  "forbid_import": [],
  "require_pattern": [],
  "llm_judge": false
}
```

### Why `require_pattern` is empty

A `require_pattern` is evaluated against the post-diff content of every file
matching its `path_glob`, so requiring `judge.backend` or a `BACKENDS` table
before TASK-59 implements them would block every commit touching
`bin/adr-judge` — including the commits that build them. The rules belong in
this block once the registry exists; TASK-59 carries that step.

`llm_judge` is `false` for the same reason ADR-016 sets it false:
`bin/adr-judge`'s `extract_decision` resolves only the `## Decision Outcome`
heading, so the Must / Must Not text a judge would need never reaches the
prompt. That is a defect to fix in TASK-63, not a flag to set optimistically
here.
