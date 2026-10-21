---
id: "ADR-050"
title: "Add a Native OMP Extension Without Expanding the Certified CLI Gate"
status: "Proposed"
date: "2026-10-21"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-039"
  - "ADR-049"
topics:
  - "OMP"
  - "oh-my-pi"
  - "native extension"
  - "client compatibility"
  - "lifecycle hooks"
aliases:
  - "OMP adapter"
  - "OMP extension"
  - "oh-my-pi extension"
components:
  - "omp extension"
symbols:
  - "omp/extension.ts"
  - "HOST_COMMANDS"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-050 Add a Native OMP Extension Without Expanding the Certified CLI Gate

## Status

Proposed, 2026-10-21.

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
    reason: Related to ADR-039
    changed_via: adr-kit lifecycle
  - date: 2026-10-21
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-049
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
`package.json`, also for marketplace installs. The extension API offers
`session_start`, `before_agent_start` (system prompt and custom message
injection), `tool_call` (block, or passive `additionalContext`), `tool_result`,
and `session.compacting`, and runs on Bun.

TASK-40.12 planned OMP and Pi adapters together and was canceled by the
2026-07-19 scope decision that kept three first-class clients. ADR-039 then set
the precedent for a native client outside that certified registry. The
maintainer requested native OMP support on 2026-10-21.

## Decision Drivers

* OMP users should get the lifecycle context and judge host the other clients
  get, with no manual configuration after the marketplace install.
* The Python engines stay the single implementation of retrieval, hook policy,
  MCP and enforcement (ADR-029, ADR-039).
* The three certified clients, their generated trees and their certification
  gate (ADR-010, ADR-048) must not change.
* Hook work stays bounded and fail-open. OMP treats a throwing or timed-out
  `tool_call` handler as a block, so the adapter must never let a fault escape.

## Considered Options

* Keep OMP as a documented compatibility path only: MCP and skills, no hooks,
  and a manual `ADR_KIT_ROOT`.
* Add a thin native OMP extension at `omp/extension.ts`, declared in
  `package.json` `omp.extensions`, that exports `ADR_KIT_ROOT` and maps OMP's
  lifecycle events onto `hooks/adr-hook.py`, plus `omp-cli` as a judge host.
* Add OMP to `clients/capabilities.json`, the installer and the certification
  gate as a fourth certified client.

## Decision Outcome

Chosen option: **a thin native OMP extension**, because it closes both gaps
through OMP's documented extension API with one small adapter and no second
governance engine, and leaves ADR-010's certified registry untouched.

The extension sets `ADR_KIT_ROOT` in its process environment when the user has
not set it, so the shell commands in the skills resolve the installed plugin.
It runs the shared hook entrypoint for SessionStart, UserPromptSubmit,
PreToolUse and PostToolUse on edit and write tools, PreToolUse on the shell
tool for the pull-request guard, SubagentStart and PreCompact. Its context
reaches the model as a hidden custom message, as passive tool context, or as
compaction context; static instructions are appended to the system prompt. The
pull-request guard may block a shell call when it returns its explicit deny;
every other outcome is advisory. Each hook subprocess runs with
`ADR_KIT_HOST_CLIENT=omp-cli`, and `omp -p --no-extensions --no-session
--no-tools` joins `HOST_COMMANDS`, so the LLM layers run on OMP's own model
without loading the extension inside a judging call.

The marketplace entry, `.mcp.json` and the skills stay as they are; OMP keeps
reading them through its Claude-compatible provider. OMP is documented
separately in `docs/clients/omp.md` and gains no identifier in the certified
registry, the generated `codex/` and `copilot/` trees, the installer, the
doctor or the support matrix.

### Confirmation

A Bun harness drives the extension's handlers against a fixture project and
checks the context each one returns, the environment it exports, fail-open
behaviour when Python is missing, and the host it names. A real OMP session
with the marketplace install shows ADR context in the model's input and a
skill resolving `ADR_KIT_ROOT`. The three-client adapter drift check and the
full Python suite run unchanged.

## Decision Contract

### Must

* Keep `omp/` separate from the generated three-client trees and from
  `opencode/`.
* Delegate every ADR operation to `hooks/adr-hook.py`, `bin/adr-mcp` and the
  other Python engines.
* Catch every fault and bound every hook's input, output and runtime, so a
  handler never blocks a tool call except on the guard's explicit deny.
* Name the host as `omp-cli` in every hook subprocess, and keep the
  `omp-cli` host command free of a model flag (ADR-043).
* Leave a user-set `ADR_KIT_ROOT` in place.
* Document OMP support and its unsupported moments separately from the
  three-client certification matrix.

### Must Not

* Add `omp` to `clients/capabilities.json`, `clients/workflows.json`, the
  three-client installer, or the certification gate.
* Implement ADR retrieval, judging or MCP in TypeScript.
* Forward a whole tool input, such as a written file's content, to the hook;
  only the paths an edit touches are sent.

### Exceptions

* The extension reuses the Claude-shaped hook envelope internally, as the
  OpenCode plugin does (ADR-039), and names its own host through
  `ADR_KIT_HOST_CLIENT`.
* The pull-request guard may block an OMP shell call on an explicit
  `permissionDecision: deny`.

### Verification

* `tests/test_omp_extension.py`
* `tests/test_adr_judge_llm.py`
* `python scripts/build-client-adapters.py --check`
* `python -m pytest -q`

## Consequences

### Positive

* A marketplace install in OMP gets session, prompt, edit, compaction and
  subagent context, the pull-request guard and a recorded judge host with no
  manual step.
* Skills work in OMP without the user setting `ADR_KIT_ROOT`.
* Fixes in the Python engines reach OMP without a TypeScript change.

### Negative

* A fifth surface adds OMP API drift. OMP's extension API is versioned with the
  harness, and the focused Bun harness pins the handler contract, so a breaking
  change shows up as a failing test rather than as silent loss of context.
* OMP delivers `tool_call` context after the tool batch settles, so pre-edit
  context reaches the model after the edit rather than before it. The
  post-edit backstop and the commit floor still hold (ADR-004).
* The hook bridge duplicates about a hundred lines of the OpenCode plugin's
  subprocess handling. OpenCode calls every export of its plugin module as a
  plugin, so the two packages cannot share a module without changing the
  OpenCode entrypoint.
* OMP has no plan-exit event, so the plan-exit tier does not fire there.

## Pros and Cons of the Options

### Keep OMP as a compatibility path

* Good, because it needs no code and adds no maintained surface.
* Bad, because OMP users get no lifecycle context, no guard and no judge host,
  and must set `ADR_KIT_ROOT` by hand.

### Thin native OMP extension

* Good, because one small adapter closes both gaps over the shared engines.
* Bad, because it is one more surface to keep compatible with a moving API.

### Certify OMP as a fourth client

* Good, because OMP would carry the same installer, doctor and certification
  guarantees.
* Bad, because it widens ADR-010's ceiling before OMP has native evidence, and
  installer and doctor work would block a release on a niche client.

## Open Questions

None.

## Related Decisions

* ADR-004 defines the fail-open context tiers and the commit floor.
* ADR-010 limits the certified native registry to three clients.
* ADR-029 requires one shared retrieval engine.
* ADR-039 sets the precedent of a native client outside the certified gate.
* ADR-043 forbids a pinned model in a host command.
* ADR-044 defines the engine root resolver the skills use.
* ADR-049 records the judge host at the first session.

## References

* `hooks/adr-hook.py`
* `opencode/plugin.ts`
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
