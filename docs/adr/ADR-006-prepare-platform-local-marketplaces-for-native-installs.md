---
id: "ADR-006"
title: "Prepare Platform-Local Marketplaces for Native Installs"
status: "Accepted"
date: "2026-07-18"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-006 Prepare Platform-Local Marketplaces for Native Installs

## Status

Accepted, 2026-07-18.

## Status History

```yaml
status_history:
  - date: 2026-07-18
    status: Proposed
    changed_by: Codex
    reason: TASK-29 introduces a three-platform native installer contract
    changed_via: adr-kit
  - date: 2026-07-18
    status: Accepted
    changed_by: Robert van den Breemen
    reason: Human approval for the v0.34.0 release; the three-platform installer ships this surface
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit ships one marketplace repository with separate Claude Code, Codex, and
GitHub Copilot CLI (command-line interface) payloads. The Codex and Copilot
MCP (Model Context Protocol) manifests historically
invoked a command named `python`. Windows commonly provides `python.exe`, while
macOS and Linux installations may expose only `python3`. Static manifests
cannot select the interpreter that actually launched the installer.

The source audit records two related defects in
`docs/reviews/2026-07-18-source-audit/FINDINGS.md`: packaged Unix entry points
can lose executable modes, and list-only validation does not prove that the MCP
server starts. Mutating a developer's checkout to insert an absolute local
interpreter would fix one machine while dirtying shared source and making that
checkout unsuitable for another platform.

## Decision Drivers

* Automated installation must work on Windows, macOS, and Linux without a
  manual `.mcp.json` edit.
* The installer must remain stdlib-only and use native client plugin APIs.
* Re-running an install must be deterministic and must not mutate the source
  checkout.
* Broken client executables and partial client failures must not hide or undo
  successful installations for other clients.
* Validation must exercise the packaged runtime, not only registration text.

## Considered Options

* Keep static `python` commands and document a `python3` workaround.
* Mutate the source checkout's client manifests during installation.
* Add shell-specific launchers for every operating system.
* Prepare a persistent platform-local marketplace from validated source.

## Decision Outcome

Chosen option: **prepare a persistent platform-local marketplace from validated
source**, because it keeps the repository portable while allowing the installed
payload to contain the exact Python 3.10+ executable and Unix file modes for
the current machine.

The installer validates all required manifests and their release versions,
probes the child interpreter, copies the source to a versioned directory under
the operating system's per-user data root, patches only that copy's Codex and
Copilot MCP commands, and restores executable entry-point modes on Unix. It
then starts the prepared MCP server and completes `initialize` plus
`tools/list` before changing a client marketplace.

Each client remains installed through its native plugin API (application
programming interface). A marketplace
registered against another source is moved once to the stable prepared path.
Later runs recognize that same source and take update or no-op paths.
Detection and installation errors are isolated per client and summarized at
the end. Native marketplace operations are not treated as transactional across
different clients.

### Confirmation

Confirm the decision with:

* simulated path, interpreter, timeout, and failure-isolation tests;
* a real prepared MCP initialize/tools-list subprocess test;
* executable-mode assertions on Unix;
* the installer compatibility suite on `windows-latest`, `macos-latest`, and
  `ubuntu-latest`;
* an unchanged source checkout after dry-run and prepared-source creation.

## Consequences

### Positive

* Unix installations no longer depend on a command literally named `python`.
* Absolute interpreter paths and paths containing spaces remain structured
  subprocess arguments instead of shell fragments.
* The source checkout stays machine-neutral and clean.
* The same prepared payload is validated before Claude, Codex, or Copilot state
  changes.
* One failing client does not prevent other selected clients from installing.

### Negative

* The installer stores a versioned copy of the marketplace in per-user data.
  The copy consumes additional disk space and must persist while local
  marketplace registrations reference it.
* The first run after this change may re-register a marketplace and reinstall
  its plugin once.
* Native client marketplace mutations cannot be rolled back atomically as one
  three-client transaction. The installer reports failures and preserves
  successful clients for an explicit retry.
* Manual Git marketplace installation still depends on executable modes in the
  release archive; the automatic installer is the guaranteed portable path.

## Pros and Cons of the Options

### Keep Static Commands and Document a Workaround

* Good, because it requires no installer storage.
* Bad, because it leaves routine macOS and Linux installations partially
  configured and pushes deterministic work onto users and agents.

### Mutate the Source Checkout

* Good, because clients already reference the checkout.
* Bad, because absolute machine paths dirty version-controlled files and break
  portability for shared or reused checkouts.

### Add Operating-System-Specific Launchers

* Good, because each launcher can use native interpreter discovery.
* Bad, because a static MCP manifest must still choose the correct launcher,
  and Windows batch, POSIX (Portable Operating System Interface) shell,
  executable-mode, and quoting behavior create
  multiple runtime contracts.

### Prepare a Platform-Local Marketplace

* Good, because one stdlib installer can materialize exact runtime commands,
  retain native plugin APIs, and validate what clients will load.
* Good, because a stable per-user source makes repeated installation
  deterministic.
* Bad, because it introduces managed local storage and a one-time marketplace
  source migration.

## Related Decisions

* ADR-001 keeps cost-bearing model behavior opt-in; this installer remains
  deterministic and key-free.
* ADR-004 requires portable, fail-open context tooling and a deterministic
  enforcement floor.
* ADR-005 requires synchronized client payloads and verification across the
  supported Python runtime.

## References

* `scripts/install-agent-envs.py`
* `tests/test_agent_installer.py`
* `.github/workflows/validate.yml`
* `docs/reviews/2026-07-18-source-audit/FINDINGS.md`
* GitHub Copilot CLI plugin reference:
  <https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference>

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [],
  "llm_judge": false,
  "llm_judge_reason": "no code surface: this decision governs process or documentation, so there is no diff for a model to judge it against"
}
```
