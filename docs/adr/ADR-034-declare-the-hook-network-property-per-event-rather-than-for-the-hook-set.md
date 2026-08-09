---
id: "ADR-034"
title: "Declare the Hook Network Property Per Event Rather Than for the Hook Set"
status: "Accepted"
date: "2026-08-06"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-017"
  - "ADR-018"
  - "ADR-023"
  - "ADR-024"
  - "ADR-025"
  - "ADR-031"
  - "ADR-036"
topics:
  - "hooks"
  - "declared contract"
  - "network"
  - "governance"
aliases:
  - "network_allowed"
  - "hook policy block"
  - "per-event network declaration"
components:
  - "hook manifest"
  - "pull-request guard"
symbols:
  - "network_allowed"
  - "adr_pr_guard"
  - "resolve_llm_backend"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-034 Declare the Hook Network Property Per Event Rather Than for the Hook Set

## Status

Accepted, 2026-08-06.

## Status History

```yaml
status_history:
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: The hook manifest declares network_allowed false for all eight events while pr-create can spawn a model CLI through two separate children.
    changed_via: adr-kit
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-017
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-018
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-023
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-024
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-025
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-031
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Maintainer accepted: the pull-request moment can reach a model on a normally installed machine, so the manifest declares that capability per event rather than averaging it away."
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Accepted
    changed_by: adr-kit
    reason: Related to ADR-036
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`hooks/manifest.json` declares one flat policy for all eight events:

```json
"policy": { "fail_open": true, "network_allowed": false, "future_clients_allowed": false }
```

Two of the eight events can reach the network. `pr-create` reaches a generative
model, through two children rather than one. `user-prompt-submit` reaches an
embedding endpoint.

**The judge, which is the larger path.** `hooks/adr_pr_guard.py:judge_branch`
spawns `bin/adr-judge` unconditionally on every `gh pr create`. ADR-017 turned
the judge's LLM pass **on by default** (`judge.llm_enabled` defaults to `true`
at `bin/adr-judge:1995`), opt-out via `ADR_KIT_NO_LLM=1`. Nothing on the guard's
path sets that variable. ADR-031 then bought this event a 5000 ms budget in
precisely so the pass could finish there.

**The suggestion nudge, which the task record found first.**
`hooks/adr_pr_guard.py:_nudge` spawns `bin/adr-suggest`, which calls
`run_llm_suggest` with no `if args.llm:` guard. That path is double-gated behind
`suggest.enabled` / `ADR_KIT_SUGGEST=1` (ADR-024), so it is the *narrower* of
the two, not the whole story.

**Whether anything leaves the machine is therefore a question about backend
resolution, and the default is not what it looks like.** Measured against
`bin/adr_llm.resolve_llm_backend` on 2026-08-06:

| Configuration | Backend resolved | Reaches out |
|---|---|---|
| Nothing recorded anywhere | `None` (one warning) | no |
| `judge.host_client` in `.adr-kit.local.json` | `SubprocessBackend(["claude", "-p"])`, `unavailable_reason()` is `None` | **yes** |
| `ADR_KIT_LLM_CMD` in the environment | `SubprocessBackend`, unrestricted | **yes** |
| `judge.backend: "openrouter"` in tracked `.adr-kit.json` | `OpenRouterBackend` | **yes**, once a model slug is set |

The second row is the one that matters. `judge.host_client` is written by the
installer and by `/adr-kit:init`, so it is present on a normally installed
machine rather than exceptional. The claim in the task record that "with nothing
configured the default posture is closed" holds only for a checkout where nobody
ran the installer.

The fourth row matters for a different reason: it is repository-tracked
configuration selecting a network backend, which ADR-025 expressly permits. So
the condition is not "a machine-local override was introduced". Tracked
configuration alone is enough.

**The second event, which reaches an endpoint rather than a model.**
`hooks/adr-hook.py:108` declares `EMBEDDING_EVENTS = {"UserPromptSubmit"}` and
builds a query embedder for that event alone. `adr_embed_query.embedder_for`
loads `bin/adr-embed` by file path -- deliberately outside the import gate --
and calls `_resolve_embed_backend`, which goes through the same
`resolve_llm_backend` registry. Where a vector store exists and the resolved
backend embeds, that is an HTTP request: `localhost:11434` for `ollama`, and
whatever `base_url` names for `openai-compatible`, which ADR-020 permits to be
remote when the user selected it through the settings surface. It fails soft to
lexical ranking on any doubt, which makes it quieter than the guard, not closed.
The same file's comment already says the entrypoint "is already the one
hook-path file allowed to reach out"; the manifest never said it twice.

**ADR-023 already found this and the manifest never caught up.** Recording the
pull-request guard as a fail-closed tier required examining ADR-019's premise
that all hooks are model-free, and it states the finding plainly: "The first
support is false, as the guard demonstrates." The manifest kept the property
that the ADR corpus had already retired.

Nothing in the tree *reads* `policy.network_allowed`; it is a declaration, and
declarations are what integrators and reviewers rely on. `network_allowed:
false` reads as a guarantee. In a governance toolkit, a false guarantee about
its own hooks is the expensive kind of wrong.

## Decision Drivers

* A declared property is read as a guarantee whether or not code enforces it,
  so it must be true of every event it covers.
* The property that is actually stable per event is *capability* -- can this
  event reach the network at all -- not *behaviour on this machine today*.
* Six of the eight events have a structural reason to be closed, and that reason
  should stay visible rather than be diluted by the two that are not.
* Reaching a generative model and reaching an embedding endpoint are different
  costs and different exposures, and a reader deserves to see which is which.
* Removing the model from the pull-request moment would contradict two Accepted
  ADRs that put it there deliberately.

## Considered Options

* **Declare the property per event**, true where the handler can reach out and
  false everywhere else, with the policy block carrying the default.
* **Suppress the LLM on the `pr-create` path** so the flat `false` becomes true.
* **Make the property conditional in the schema**, for example
  `network_allowed: "only-when-backend-configured"`.

## Decision Outcome

Chosen option: **declare the property per event**, because the difference
between the two events that can reach out and the six that cannot is real,
structural, and worth showing rather than averaging away.

`policy.network_allowed` stays, and becomes the default every event inherits.
An event may override it. Two do:

```json
{ "id": "user-prompt-submit", "network_allowed": true, "network_reason": "..." }
{ "id": "pr-create",          "network_allowed": true, "network_reason": "..." }
```

The six that keep `false` keep it for a reason a reader can check rather than
trust: they are served by `hooks/adr_hook_core.py` alone, whose ADR-018 gate
forbids importing `subprocess`, `socket`, `urllib`, `http`, `ssl`, `requests`,
`httpx` and `asyncio`. A retrieval hook cannot reach a model because it cannot
spawn one and cannot open a socket.

The two overrides are the two places the entrypoint steps outside that module,
and it steps outside for each of them by name: `_pr_guard` for `pr-create`, and
`_embedder_for` gated on `EMBEDDING_EVENTS` for `user-prompt-submit`. The
declaration now follows the same line the code is already split along, which is
what makes it checkable rather than remembered.

`network_reason` carries the distinction the boolean cannot: `pr-create` reaches
a generative model and bills for it, `user-prompt-submit` reaches an embedding
endpoint that is local by default and remote only where the user selected a
remote one (ADR-020).

**Why not suppress the LLM.** It is the smallest change and it contradicts two
Accepted ADRs. ADR-024 put the suggestion at the pull-request moment on the
argument that this is where a missing decision is most worth asking about, and
ADR-031 raised this event's budget to 5000 ms with the explicit reasoning that
"the branch judge keeps the LLM pass at the moment it is most useful". Making
the manifest true by deleting the capability would spend both of those to fix a
sentence.

**Why not a conditional string.** `"only-when-backend-configured"` is accurate
and it is the wrong shape for a declaration. A reader who has not configured a
backend concludes the condition does not apply to them -- and the measurement
above says they are probably wrong, because the installer configured one for
them. It reintroduces the same false comfort in longer words, and it makes a
one-line boolean into a value every reader must parse and evaluate. A capability
declaration answers "can this event reach the network", and `true` is the honest
answer for `pr-create` whatever today's configuration says. What is conditional
belongs in `network_reason`, as prose, where nobody will mistake it for a
guarantee.

### Confirmation

`hooks/manifest.json` declares `network_allowed: true` for `pr-create` and for
`user-prompt-submit`, and inherits `false` for the other six. A test drives the
pull-request path with a backend configured and observes the child being
invoked, so that `true` is asserted against behaviour rather than restated. A
second test reads `EMBEDDING_EVENTS` from `hooks/adr-hook.py` and asserts that
every event in it declares `true`, so widening that set cannot silently outrun
the declaration. A third asserts that every event declaring `false` is served by
`adr_hook_core` alone, whose ADR-018 gate forbids the imports a reach-out would
need, so the `false` is structural. A synthetic manifest that declares `false`
for either reaching event fails.

## Decision Contract

### Must

* Declare `network_allowed` for every event, by inheritance or by override.
* Declare `true` where the handler can spawn a model or open a connection,
  whatever the reading machine is configured with.
* Give every `true` a `network_reason`.
* Keep the client mirrors carrying the same declaration.

### Must Not

* Do not declare `false` for an event that can reach out under any supported
  configuration.
* Do not express a conditional capability as a declared value.
* Do not drop the model pass from the pull-request moment to make a declaration
  true.

### Exceptions

* None. An event that cannot be classified declares `true`.
* A local-only endpoint still counts: `ollama` on `localhost:11434` opens a
  socket, and the same path reaches a remote host when pointed at one.

### Verification

* `adr-hook-network-declaration-v1`: the gate this decision is to be anchored
  by. It does not exist yet, so `gate` is null and `binding` is false. Both
  fields flip together when it ships, covering the configured-backend case, the
  structural-closure case, and the misdeclared-event case.

## Consequences

### Positive

* The manifest stops making a claim about `pr-create` that ADR-023 had already
  recorded as false.
* The embedding path at `user-prompt-submit` is declared for the first time. It
  was reachable, permitted by ADR-020, and stated nowhere a reader of the
  manifest would look.
* The six closed events gain a stated structural reason instead of sharing an
  averaged one.
* An integrator reading the manifest can see which moments reach outward and
  what each one reaches, which is the question they are actually asking.

### Negative

* The policy block no longer answers the network question on its own; a reader
  must look at the event. Mitigated by keeping the default in the policy block,
  so the common answer is still one line up.
* `network_allowed: true` on `pr-create` will read as alarming to somebody who
  has configured no backend and never will. That is the intended direction of
  the error: it overstates a capability rather than understating it.
* This is a contract change to a published manifest, so anything downstream that
  read the flat property must be updated with it.

## Pros and Cons of the Options

### Declare the property per event

* Good, because the declaration follows the same split the code already has.
* Good, because it keeps the model where two Accepted ADRs put it.
* Bad, because it makes the schema slightly larger and the policy block slightly
  less self-contained.

### Suppress the LLM on the pr-create path

* Good, because the flat `false` becomes true with no schema change.
* Bad, because it removes the check from the moment ADR-024 argued is the most
  useful one, and spends the budget ADR-031 bought for it.
* Bad, because it makes a governance question look like a wording problem.

### Make the property conditional in the schema

* Good, because it is literally accurate.
* Bad, because a reader evaluates the condition against what they believe their
  machine does, and the measurement says that belief is usually wrong.
* Bad, because every reader of the manifest must now parse a value instead of
  reading one.

## Open Questions

* None.

## Related Decisions

* ADR-017 makes the judge's LLM pass on by default, which is what puts a model
  on this path.
* ADR-018's import gate is what makes the other seven events structurally
  closed.
* ADR-023 records the pull-request guard as a fail-closed tier and states that
  the model-free premise is false.
* ADR-024 puts the suggestion nudge at this moment.
* ADR-025 separates what tracked configuration may select from what only a
  machine may introduce; tracked configuration can select a network backend.
* ADR-031 gives this event the budget the model pass needs.

## References

* `hooks/manifest.json` -- the `policy` block and the `pr-create` entry.
* `hooks/adr_pr_guard.py` -- `judge_branch` and `_nudge`, both spawning
  children.
* `bin/adr_llm.py` -- `resolve_llm_backend`, `_host_backend`, `HOST_COMMANDS`.
* `bin/adr-judge` -- `judge.llm_enabled` defaulting to true.
* `docs/adr/ADR-023-record-the-pull-request-guard-as-a-fail-closed-tier.md`

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
