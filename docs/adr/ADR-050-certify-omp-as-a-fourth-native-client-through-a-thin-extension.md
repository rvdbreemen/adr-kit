---
id: "ADR-050"
title: "Certify OMP as a Fourth Native Client Through a Thin Extension"
status: "Accepted"
date: "2026-10-21"
binding: false
gate: null
documents_shipped: false
verified_in:
  - "tests/test_omp_extension.py"
supersedes: []
superseded_by: null
related:
  - "ADR-010"
  - "ADR-039"
  - "ADR-048"
  - "ADR-049"
topics:
  - "OMP"
  - "oh-my-pi"
  - "native extension"
  - "client certification"
  - "lifecycle hooks"
aliases:
  - "OMP adapter"
  - "OMP extension"
  - "oh-my-pi extension"
  - "fourth certified client"
components:
  - "omp extension"
  - "client capability registry"
symbols:
  - "omp/extension.ts"
  - "HOST_COMMANDS"
  - "clients/capabilities.json"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-050 Certify OMP as a Fourth Native Client Through a Thin Extension

## Status

Accepted, 2026-10-21.

## Status History

```yaml
status_history:
  - date: 2026-10-21
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-21
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-010
    changed_via: adr-kit lifecycle
  - date: 2026-10-21
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-048
    changed_via: adr-kit lifecycle
  - date: 2026-10-21
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: The maintainer accepted certifying OMP as a fourth native client through a thin extension, amending ADR-010's client list; certification ships in v0.62.0 (grilled 2026-10-21).
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

OMP (oh-my-pi) installs Claude Code-format marketplace plugins through its own
plugin manager, so `omp plugin install adr-kit@rvdbreemen-adr-kit` already
yields the MCP server, the 17 skills and the `adr-generator` agent. Observed on
OMP 18.12.5 with adr-kit 0.60.0 (TASK-239), two parts of that install do not
work:

* OMP runs only TypeScript/JavaScript extension and hook factories. It never
  executes the command hooks in `hooks/hooks.json`: an OMP session in a project
  with `docs/adr/` did not write the `.adr-kit.local.json` that the SessionStart
  hook writes, while running the same hook by hand did. There is no session,
  prompt, edit, compaction or subagent context, no pull-request guard, and no
  judge host is recorded (ADR-049).
* OMP neither substitutes `${CLAUDE_PLUGIN_ROOT}` in skill bodies nor exports it
  to the shell. Ten skills resolve the engine as
  `${ADR_KIT_ROOT:-${CLAUDE_PLUGIN_ROOT}}` (ADR-044) and stop with
  `plugin root not found` unless the user sets `ADR_KIT_ROOT` by hand.

OMP loads extension modules a plugin declares under `omp.extensions` in its
`package.json`, also for marketplace installs. Its extension API offers
`session_start`, `before_agent_start` (system prompt and custom message
injection), `tool_call` (block, or passive `additionalContext`), `tool_result`,
and `session.compacting`, and runs on Bun.

ADR-010 names exactly three first-class clients and requires each to meet one
outcome contract, with every native shortfall declared in
`clients/capabilities.json`. ADR-048 certifies a client per platform only from
a fresh native record, and lets documentation claim certification only where
such a record exists. TASK-40.12 had planned OMP and Pi adapters and was
canceled by the 2026-07-19 three-client scope decision; ADR-039 then kept
OpenCode native but outside the certified gate. On 2026-10-21 the maintainer
chose to make OMP a certified client.

## Decision Drivers

* OMP users should get the lifecycle context, the pull-request guard and the
  judge host the other clients get, with no manual configuration after the
  marketplace install.
* The maintainer wants OMP held to the same guarantees as the certified
  clients: install, update, rollback, removal, doctor and native evidence.
* The Python engines stay the single implementation of retrieval, hook policy,
  MCP and enforcement (ADR-029).
* Hook work stays bounded and fail-open (ADR-004). OMP treats a throwing or
  timed-out `tool_call` handler as a block, so the adapter must never let a
  fault escape.
* Claims follow evidence (ADR-048): certification is stated only once a native
  OMP record exists.

## Considered Options

* Keep OMP as a documented compatibility path only: MCP and skills, no hooks,
  and a manual `ADR_KIT_ROOT`.
* Add a thin native OMP extension, but keep OMP outside the certified gate, as
  ADR-039 did for OpenCode.
* Add the thin native OMP extension and certify OMP as a fourth client under
  ADR-010's outcome contract.

## Decision Outcome

Chosen option: **certify OMP as a fourth native client, carried by a thin
extension**, because the maintainer wants OMP to carry the same guarantees as
the certified clients, and the extension closes both gaps through OMP's
documented API without a second governance engine.

This amends ADR-010 on one point: its list of first-class clients grows from
three to four with `omp-cli`. ADR-010's outcome contract, its capability
registry, its degradation rules and every other part of it keep governing, and
OMP must meet them in full.

The extension, `omp/extension.ts`, is declared in `package.json` under
`omp.extensions` so a marketplace install loads it. It sets `ADR_KIT_ROOT` in
its process environment when the user has not set it, so the skills resolve the
installed plugin. It runs the shared hook entrypoint for SessionStart,
UserPromptSubmit, PreToolUse and PostToolUse on edit and write tools,
PreToolUse on the shell tool for the pull-request guard, SubagentStart and
PreCompact. Context reaches the model as a hidden custom message, as passive
tool context, or as compaction context; static instructions are appended to the
system prompt. The pull-request guard may block a shell call on its explicit
deny; every other outcome is advisory. Each hook subprocess runs with
`ADR_KIT_HOST_CLIENT=omp-cli`, and `omp -p --no-extensions --no-session
--no-tools` joins `HOST_COMMANDS`, so the LLM layers run on OMP's own model
without loading the extension inside a judging call.

OMP's two native shortfalls are declared, not hidden. OMP delivers `tool_call`
context after the tool batch settles, so pre-edit context reaches the model
with the post-edit context: this is an `edit-governance` degradation in
`clients/capabilities.json`, whose backstop is the post-edit context and the
commit floor. OMP has no plan-exit event, which is mapped as no native event,
as for Codex and Copilot. Edits are never blocked to work around the first
(ADR-004).

Delivery is staged. v0.61.0 ships the extension and the `omp-cli` host, with
OMP documented as native and certification in progress. v0.62.0 adds OMP to
`clients/capabilities.json`, the schemas, the installer, `adr-doctor`, the
generated support matrix and the release gate, together with a native Windows
record at `tests/certification/omp/windows-native.json`. Until that record
exists and passes, no document claims OMP is certified (ADR-048).

### Confirmation

A Bun harness drives the extension's handlers against a fixture project and
checks the context each returns, the environment it exports, fail-open
behaviour when Python is missing, the guard's deny, and the host it names. A
real OMP session with the marketplace install shows ADR context in the model's
input, a skill resolving `ADR_KIT_ROOT`, and `omp-cli` recorded as the host.
Certification is confirmed when the native Windows record for `omp-cli` passes
every required outcome and the release gate accepts it.

## Decision Contract

### Must

* Keep `omp/` separate from the generated `codex/` and `copilot/` trees and
  from `opencode/`.
* Delegate every ADR operation to `hooks/adr-hook.py`, `bin/adr-mcp` and the
  other Python engines.
* Catch every fault and bound every hook's input, output and runtime, so a
  handler never blocks a tool call except on the guard's explicit deny.
* Name the host as `omp-cli` in every hook subprocess, and keep the `omp-cli`
  host command free of a model flag (ADR-043).
* Leave a user-set `ADR_KIT_ROOT` in place.
* Meet ADR-010's outcome contract for `omp-cli`: register it in
  `clients/capabilities.json`, the installer, `adr-doctor`, the support matrix
  and the release gate.
* Declare late pre-edit context as an `edit-governance` degradation with its
  reason, user effect and backstop, and map plan exit as no native event.
* Claim OMP certification only per platform where a passing native record
  exists (ADR-048).

### Must Not

* Implement ADR retrieval, judging or MCP in TypeScript.
* Forward a whole tool input, such as a written file's content, to the hook;
  only the paths an edit touches are sent.
* Block an edit to deliver pre-edit context earlier.
* Claim OMP is certified before its native record passes.

### Exceptions

* The extension reuses the Claude-shaped hook envelope internally, as the
  OpenCode plugin does (ADR-039), and names its own host through
  `ADR_KIT_HOST_CLIENT`.
* The pull-request guard may block an OMP shell call on an explicit
  `permissionDecision: deny`.
* Until v0.62.0 lands the registry work, OMP ships as a native but not yet
  certified client.

### Verification

* `tests/test_omp_extension.py`
* `tests/test_adr_judge_llm.py`
* `tests/certification/omp/windows-native.json` (from v0.62.0)
* `python scripts/build-client-adapters.py --check`
* `python -m pytest -q`

## Consequences

### Positive

* A marketplace install in OMP gets session, prompt, edit, compaction and
  subagent context, the pull-request guard and a recorded judge host with no
  manual step.
* Skills work in OMP without the user setting `ADR_KIT_ROOT`.
* Once certified, OMP carries the same install, update, rollback, doctor and
  evidence guarantees as the other certified clients.
* Fixes in the Python engines reach OMP without a TypeScript change.

### Negative

* Certification widens ADR-010's maintenance ceiling: every release must keep
  four native clients green, and OMP's extension API is versioned with the
  harness. The focused Bun harness and the native record make a breaking change
  visible as a failing test or an expired record rather than as silent loss of
  context.
* Pre-edit context reaches the model after the edit. The degradation is
  declared and the post-edit backstop and commit floor still hold (ADR-004).
* The hook bridge duplicates about a hundred lines of the OpenCode plugin's
  subprocess handling. OpenCode calls every export of its plugin module as a
  plugin, so the two packages cannot share a module without changing the
  OpenCode entrypoint.
* Between v0.61.0 and v0.62.0, OMP is native but not yet certified, and the
  documentation must say so.

## Pros and Cons of the Options

### Keep OMP as a compatibility path

* Good, because it needs no code and adds no maintained surface.
* Bad, because OMP users get no lifecycle context, no guard and no judge host,
  and must set `ADR_KIT_ROOT` by hand.

### Native extension outside the certified gate

* Good, because one small adapter closes both gaps with little release cost.
* Bad, because OMP would lack the installer, doctor and evidence guarantees the
  maintainer wants for it.

### Native extension and certification

* Good, because OMP gets both the native integration and the full set of
  certified-client guarantees.
* Bad, because it adds installer, doctor and evidence work and a fourth client
  every release must keep green.

## Open Questions

- [x] Which option does the maintainer choose for OMP: a compatibility path only, a native extension outside the certified gate, or full certification as a fourth client? — **Answered 2026-10-21 by User: Robert van den Breemen:** Full certification: OMP becomes a fourth certified client in clients/capabilities.json, the installer, adr-doctor and the release gate, carried by the native extension already built. Chosen by the maintainer on 2026-10-21 over the proposed native-but-uncertified option.
- [x] How does the record treat ADR-010, which names exactly three first-class clients? — **Answered 2026-10-21 by User: Robert van den Breemen:** ADR-050 amends ADR-010: only the first-class client list grows from three to four (adding omp-cli); ADR-010's outcome contract, registry and every other rule keep governing, and OMP must meet them in full.
- [x] Does certification hold back the release that ships the extension? — **Answered 2026-10-21 by User: Robert van den Breemen:** No. v0.61.0 ships the native extension with OMP documented as native, certification in progress (ADR-048: claims follow evidence). The registry, installer, doctor, schema and native Windows evidence work ships in v0.62.0 under its own backlog task; ADR-050 is accepted as the decision now.
- [x] How does the registry record OMP's late pre-edit context and its missing plan-exit event? — **Answered 2026-10-21 by User: Robert van den Breemen:** Declare both honestly. Late pre-edit context is an edit-governance degradation in clients/capabilities.json (reason: OMP delivers tool_call context after the tool batch settles; user effect: the governing ADR arrives with the post-edit context; backstop: post-edit context and the commit floor). Plan exit is mapped as no native event, as for Codex and Copilot. No blocking of edits (ADR-004).

## Related Decisions

* ADR-004 defines the fail-open context tiers and the commit floor.
* ADR-010 defines the outcome contract and capability registry; this record
  amends its client list.
* ADR-029 requires one shared retrieval engine.
* ADR-039 keeps OpenCode native but outside the certified gate.
* ADR-043 forbids a pinned model in a host command.
* ADR-044 defines the engine root resolver the skills use.
* ADR-048 certifies each client per platform from native evidence.
* ADR-049 records the judge host at the first session.

## References

* `hooks/adr-hook.py`
* `omp/extension.ts`
* `clients/capabilities.json`
* `docs/clients/omp.md`
* OMP repository: https://github.com/can1357/oh-my-pi
* OMP extension API: `docs/extensions.md` in the OMP repository

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "ADR_KIT_HOST_CLIENT: \"omp-cli\"",
      "path_glob": "omp/extension.ts",
      "message": "The OMP extension must name its own host, so its judge is not claude -p (ADR-050)."
    }
  ]
}
```
