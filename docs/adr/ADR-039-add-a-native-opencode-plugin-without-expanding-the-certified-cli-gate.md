---
id: "ADR-039"
title: "Add a Native OpenCode Plugin Without Expanding the Certified CLI Gate"
status: "Accepted"
date: "2026-08-16"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "OpenCode"
  - "native plugin"
  - "client compatibility"
  - "lifecycle hooks"
  - "MCP"
aliases:
  - "OpenCode adapter"
  - "OpenCode plugin"
  - "fourth client"
components:
  - "opencode plugin"
  - "MCP server"
  - "client release gate"
symbols:
  - "opencode/plugin.ts"
  - "clients/capabilities.json"
  - "scripts/build-client-adapters.py"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-039 Add a Native OpenCode Plugin Without Expanding the Certified CLI Gate

## Status

Accepted, 2026-08-16.

## Status History

```yaml
status_history:
  - date: 2026-08-14
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-08-16
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: The user explicitly accepted the native OpenCode plugin decision while preserving the certified three-client release gate.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit has native distributions for Claude Code CLI, Codex CLI, and the
standalone GitHub Copilot CLI. ADR-010 deliberately limits the certified native
registry and release gate to those three clients. OpenCode now exposes a native
plugin API with configuration, chat/system transforms, tool hooks, compaction,
shell environment, commands, skills, and MCP configuration.

The existing generic OpenCode task only permits portable skills, `AGENTS.md`,
and manually configured MCP. That is no longer the requested product boundary:
OpenCode should receive a real native plugin while the three existing clients
must retain their manifests, generated payloads, hook contracts, installer,
doctor, and certification behavior byte-for-byte unless a shared engine fix is
required.

The Python engines already implement retrieval, hook policy, MCP, lifecycle, and
deterministic enforcement. A second TypeScript retrieval or enforcement engine
would create the same parity risk that ADR-029 removed from the native hook
binary. OpenCode therefore needs a thin native adapter around those engines, not
an independent governance implementation.

## Decision Drivers

* OpenCode users need native discovery and lifecycle integration, not only a
  portable fallback.
* Claude Code, Codex, and Copilot compatibility and their three-client release
  certification must remain unchanged.
* The Python engines remain the single source of truth for ADR context, hook
  policy, MCP tools, and the pre-commit/CI enforcement floor.
* Configuration must be additive and opt-out capable: user-owned OpenCode
  settings, MCP entries, skills, commands, and instructions must not be
  overwritten.
* Native hook work must be bounded, fail-open for advisory context, and free of
  surprise model or network calls. The existing pull-request guard may preserve
  its explicit enforcement semantics.

## Considered Options

* Keep OpenCode generic-only and defer native support.
* Add a separate native OpenCode package whose thin TypeScript adapter discovers
  the canonical skills, commands, MCP server, and project guidance, then calls
  the existing Python hook runtime for context and pull-request checks.
* Add OpenCode to `clients/capabilities.json`, generated adapter output, the
  three-client installer, and the release certification gate.

## Decision Outcome

Chosen option: **a separate native OpenCode package**, because it gives
OpenCode its documented native surface without widening ADR-010's certified
three-client contract or duplicating the governance engines.

The package is rooted at `opencode/plugin.ts` and is also loadable as the
repository's npm-style package. Its config hook adds only missing ADR Kit
skills, instructions, workflow commands, and a local `adr-kit` MCP server. Its
native hooks use the existing Python hook entrypoint and preserve the shared
fail-open context behavior. The OpenCode adapter may stop a pull-request tool
call when the existing guard returns its explicit deny decision; edit context,
session context, prompt context, and compaction context remain advisory.

The existing three-client registry, generated `codex/` and `copilot/` trees,
native installer, native doctor, support matrix, and three-client certification
gate do not gain an OpenCode identifier. OpenCode gets separate documentation
and focused compatibility tests. The existing pre-commit and GitHub Actions
templates remain client-independent and are the enforcement backstop for
OpenCode projects as well.

### Confirmation

Verify the package with a Bun smoke harness, valid OpenCode config-shape
fixtures, native hook dispatch fixtures, MCP startup, command/skill discovery,
and additive-config preservation tests. Run the existing three-client adapter
drift, native package, MCP, and full Python test suites unchanged.

## Decision Contract

### Must

* Keep `opencode/` separate from the three-client generated adapter trees.
* Reuse `bin/adr-mcp`, `hooks/adr-hook.py`, `bin/adr-context`, and the existing
  CI/pre-commit engines rather than implementing a second retrieval or judge.
* Preserve user-owned OpenCode config and make automatic MCP/skill/command
  registration opt-out capable.
* Keep advisory hook failures fail-open and bound subprocess input, output, and
  runtime.
* Document OpenCode support separately from the three-client certification
  matrix, including its evidence and unsupported lifecycle claims.

### Must Not

* Add `opencode` to `clients/capabilities.json`, `clients/workflows.json`, the
  three-client installer, or the three-client release certification gate.
* Hand-edit or regenerate `codex/` or `copilot/` as part of OpenCode support.
* Create a second ADR retrieval, MCP, or declarative enforcement engine in
  TypeScript.
* Overwrite existing OpenCode MCP entries, instructions, skills, commands, or
  permissions.

### Exceptions

* The OpenCode adapter may reuse the Claude-shaped normalized hook envelope
  internally because the Python hook core is client-neutral and its response is
  extracted before OpenCode sees it.
* The existing `gh pr create` guard may deny an OpenCode shell tool call when
  the shared guard returns `permissionDecision: deny`; this is enforcement, not
  advisory edit injection.

### Verification

* `tests/test_opencode_plugin.py`
* `tests/test_opencode_package.py`
* `python scripts/build-client-adapters.py --check`
* `python -m pytest -q`

## Consequences

### Positive

* OpenCode receives native skills, commands, MCP registration, context
  injection, compaction carry-forward, shell environment, and pull-request
  guarding through its documented plugin API.
* The existing Python engines remain authoritative, so a governance fix reaches
  every client surface instead of creating a fourth implementation.
* The three-client release and certification contract stays stable and easy to
  reason about.

### Negative

* A fourth native surface adds OpenCode API drift and Bun/TypeScript packaging
  risk. Focused smoke tests and separate documentation make that risk visible
  without making it a false release blocker for the three certified CLIs.
* OpenCode's advisory context hooks cannot provide the same response envelope
  as Claude Code, so the adapter uses the native system transform and retains
  deterministic pre-commit/CI enforcement as the floor.

## Pros and Cons of the Options

### Option A

* Good, because it preserves the already approved certification boundary.
* Bad, because OpenCode users lack a native plugin.

### Option B

* Good, because it provides native support with one thin adapter and one shared
  engine.
* Bad, because it adds a separately monitored package surface.

### Option C

* Good, because it presents one broader native registry.
* Bad, because it expands installer, doctor, certification, and release work
  before OpenCode has independent native evidence and violates ADR-010's
  maintenance ceiling.

## Open Questions

None.

## Related Decisions

* ADR-004 defines the fail-open context tiers and deterministic enforcement floor.
* ADR-010 limits the certified native CLI registry to three clients.
* ADR-012 defines versioned public-repository release surfaces.
* ADR-015 bounds deterministic user-facing paths.
* ADR-021 defines stale-index recovery boundaries for hooks.
* ADR-029 requires one shared retrieval engine.
* ADR-034 requires truthful per-event network declarations.

## References

* `clients/capabilities.json`
* `scripts/build-client-adapters.py`
* `bin/adr-mcp`
* `hooks/adr-hook.py`
* OpenCode plugin API: https://opencode.ai/docs/plugins/
* OpenCode MCP configuration: https://opencode.ai/docs/mcp-servers/
* OpenCode Agent Skills: https://opencode.ai/docs/skills/
* OpenCode rules and instructions: https://opencode.ai/docs/rules/
* MCP specification 2026-07-28: https://modelcontextprotocol.io/specification/2026-07-28

## Enforcement

Delete this optional section when the decision has no machine-checkable surface.

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
