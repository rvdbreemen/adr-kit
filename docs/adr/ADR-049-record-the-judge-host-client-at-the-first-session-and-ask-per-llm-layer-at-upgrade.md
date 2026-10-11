---
id: "ADR-049"
title: "Record the judge host client at the first session and ask per LLM layer at upgrade"
status: "Accepted"
date: "2026-10-11"
binding: true
gate: "adr-llm-default-on-v1"
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-036"
  - "ADR-041"
topics:
  - "llm layers"
  - "default install"
  - "host client"
  - "onboarding"
aliases:
  - "llm.confirmed"
  - "ADR_KIT_HOST_CLIENT"
  - "machine-local override"
components:
  - "hooks/adr_hook_core.py"
  - "bin/adr_llm.py"
symbols:
  - "llm_onboarding"
  - "record_host_client_if_absent"
  - "apply_machine_overrides"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-049 Record the judge host client at the first session and ask per LLM layer at upgrade

## Status

Accepted, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-036
    changed_via: adr-kit lifecycle
  - date: 2026-10-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-041
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-036
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted after grilling on 2026-10-11
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

The LLM layers are the per-commit judge pass, the `adr-suggest` nudge and the
guardian's LLM tier. They default to on in the schema, but they only run where
a host client is recorded in the gitignored `docs/adr/.adr-kit.local.json`.
ADR-036 says that client is "recorded at install time". In practice only two
paths recorded it: `scripts/install-agent-envs.py` when a run installs exactly
one client (`clients/installer/judge_backend.py`, TASK-169), and `/adr-kit:init`
answered "on". The common route, a client's own plugin install
(`/plugin install`), runs neither, and neither does an installer run with
several clients. On those installs every LLM layer did nothing, silently.

Two more defects sat on the same path. OpenCode's plugin calls the shared hook
as `claude-code-cli` (`opencode/plugin.ts`) and loads the canonical skills that
name that id, so recording "the client" would have pointed an OpenCode user's
judge at `claude -p`. And on Windows `run_cli` handed the bare command name to
`Popen`, which cannot find an npm `.cmd` shim, so Codex, Copilot CLI or OpenCode
installed through npm failed with `FileNotFoundError` and degraded silently.

The maintainer set the requirement on 2026-10-06: on a clean install and on an
upgrade the LLM layers are on by default, they run on the coding assistant the
plugin is installed in, and the user confirms interactively whether to keep them
on or turn any of them off.

## Decision Drivers

* A default install must not leave a feature that is "on by default" doing
  nothing without a word.
* The model that judges is the one the user already uses in that client: no API
  key, no pinned model (ADR-036, ADR-043).
* The user decides, interactively, and can always say no.
* One developer's "off" must not switch the layers off for the whole team
  (ADR-025: a personal choice is a machine fact).
* The session hooks stay fast and fail open (ADR-015, ADR-030).

## Considered Options

* Record the host client at the first session, confirm through the session
  model, and keep every answer machine-local.
* Let the installer pick a client by fixed order when several are installed.
* Keep recording in `/adr-kit:init` only and document that it must be run.

## Decision Outcome

Chosen option: **record the host client at the first session, confirm through
the session model, and keep every answer machine-local**, because it is the only
option that reaches the plugin-install route, picks the client the user actually
works in, and leaves the choice with the user.

**Decision Maker:** User: Robert van den Breemen, on 2026-10-06. He chose this
option over installer ordering and init-only, chose machine-local scope for an
"off" answer over project-wide scope, and kept the guardian's LLM tier ask-first
(`guardian.llm_autorun` stays false, ADR-001).

What ships:

1. On `SessionStart`, and on the first prompt for a client without one, the
   shared hook records the session's client as `judge.host_client` when
   `docs/adr` exists, nothing is recorded, and the effective `judge.llm_enabled`
   is not false. It never replaces a recorded choice, never writes over an
   unreadable file, and fails open. `.git` is found by walking up, without a
   `git` subprocess, to stay inside the session-start budget. This is a
   session-scoped write, with ADR-021's index regeneration as precedent; the
   edit-tier hooks stay read-only.
2. On a real prompt the hook then asks the user, through the session model,
   whether to keep each layer on (recommended) or turn it off for this machine,
   with the exact `adr-settings --local` commands, until `llm.confirmed` is
   recorded, at most once a day. `ADR_KIT_NO_LLM=1` suppresses the question.
3. `/adr-kit:init` and `/adr-kit:upgrade` ask the same per-layer question on
   every run, show the current values, recommend "on", and never change an
   unanswered value.
4. An "off" answer is written to `.adr-kit.local.json`. Four booleans may be
   overridden there: `judge.llm_enabled`, `suggest.enabled`,
   `guardian.llm_enabled` (new) and `guardian.llm_autorun`. The judge,
   `adr-suggest`, `adr-substance` and the guardian read through that override.
5. OpenCode names its own host through `ADR_KIT_HOST_CLIENT=opencode-cli`, and
   `opencode run --pure` joins `HOST_COMMANDS`. OpenCode is a host, not a
   certified client (ADR-039).
6. `run_cli` resolves the command with `shutil.which`, so an npm `.cmd` shim
   runs.

This amends ADR-036 on one point, when the host client is recorded, and reuses
ADR-041's next-prompt handoff as the moment to ask. It does not change the host
backend itself.

### Confirmation

The gate `adr-llm-default-on-v1` is `tests/test_llm_onboarding_hook.py`. It
checks that the client is recorded per client and never overwritten, that
nothing is recorded when the pass is off, for an unknown client or without
`docs/adr`, that OpenCode records `opencode-cli`, and that the question repeats
until it is confirmed and stops after. `tests/test_machine_llm_overrides.py`
holds every reader to the machine-local override. Live: `adr-judge --llm-cmd
"opencode run --pure"` judged all seven in-scope ADRs on this repository once
`run_cli` resolved the `.cmd` shim.

## Decision Contract

### Must

* Record the host client only when none is recorded and the effective
  `judge.llm_enabled` is not false.
* Ask the user before treating the default as settled, and record the answer in
  `llm.confirmed`.
* Write an "off" answer to `.adr-kit.local.json`, never to `.adr-kit.json`.
* Name the host a client actually runs on, through `ADR_KIT_HOST_CLIENT` where a
  client borrows another client's hook shape.

### Must Not

* Replace a recorded host client, or a value the user did not answer.
* Pass a model flag or record a credential (ADR-036, ADR-043).
* Write from an edit-tier hook (PreToolUse, PostToolUse).

### Exceptions

* None.

### Verification

* `tests/test_llm_onboarding_hook.py` (gate `adr-llm-default-on-v1`).
* `tests/test_machine_llm_overrides.py` and `tests/test_adr_llm_bounded.py`.
* The two `require_pattern` rules below.

## Consequences

### Positive

* A plugin install, a multi-client install and an upgrade all end with the LLM
  layers running on the user's own assistant. They run from the first
  session on; the user's answer keeps them on or turns them off.
* OpenCode users get their own model as the judge, not `claude -p`.
* npm-installed CLIs on Windows work as hosts instead of degrading silently.
* A teammate's "off" stays on that teammate's machine.

### Negative

* The first prompt in a project carries one extra question until it is
  answered. Mitigation: at most once a day, ended by `llm.confirmed`, silenced
  by `ADR_KIT_NO_LLM=1`.
* A session hook now writes a gitignored file. Mitigation: session-scoped events
  only (ADR-021 precedent), the file is registered in `.git/info/exclude`, and
  every failure is silent.
* With several clients, the first one used in a project becomes its judge.
  Mitigation: init and upgrade show it and record a different one on request.
* The team cannot see a machine's "off" in review. That is intended, because it
  is a personal choice (ADR-025); `adr-settings` shows its provenance.

## Pros and Cons of the Options

### Record at the first session, confirm, machine-local

* Good, because it reaches every install route, including `/plugin install`.
* Good, because the recorded client is the one the user works in.
* Bad, because a hook writes a file.

### Installer picks by order

* Good, because no hook writes anything.
* Bad, because the plugin-install route never runs the installer.
* Bad, because a fixed order decides, without the user, which vendor sees the
  diffs.

### Init only

* Good, because it is the smallest change.
* Bad, because an install without `/adr-kit:init` stays silently off, which is
  the defect this record exists to remove.

## Open Questions

- [x] Do the LLM layers run between the first session, which records the
  host client, and the user's answer to the question, or do they wait for
  `llm.confirmed`?
  — **Answered 2026-10-11 by User: Robert van den Breemen:** They run from the first session on. The host is the client the user already works in, so no new party sees the diff, and gating on llm.confirmed would bring back the silently-off install this record removes for anyone who ignores the question. llm.confirmed ends the question; it does not gate the layers.

## Related Decisions

* ADR-036 (Retire the vector layer and run the judge on the host model only):
  amended on when the host client is recorded.
* ADR-041 (Automatically hand off unfinished Proposed ADRs to interactive
  grilling): its next-prompt handoff is the moment the question is asked.
* ADR-025 (Separate what tracked configuration may select from what only a
  machine may introduce): why an "off" answer is machine-local.
* ADR-021 (Let the session-scoped hooks regenerate a stale ADR index): the
  precedent for a session hook that writes.
* ADR-039 (Add a native OpenCode plugin without expanding the certified CLI
  gate): OpenCode is a host here, not a certified client.
* ADR-043 (Forbid a pinned model or a default LLM command in every
  model-calling entry point): `opencode run --pure` carries no model flag.

## References

* TASK-233 (plan, decisions and evidence); TASK-169 (installer recording).
* `hooks/adr_hook_core.py` (`llm_onboarding`), `bin/adr_llm.py`
  (`record_host_client_if_absent`, `HOST_COMMANDS`, `run_cli`),
  `bin/adr_config.py` (`apply_machine_overrides`), `opencode/plugin.ts`.
* OpenCode 1.18.28: `opencode run` reads the prompt on stdin (verified
  2026-10-06).

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "record_host_client_if_absent\\(",
      "path_glob": "hooks/adr_hook_core.py",
      "message": "The session hook must record the host client on a default install (ADR-049)."
    },
    {
      "pattern": "ADR_KIT_HOST_CLIENT: \"opencode-cli\"",
      "path_glob": "opencode/plugin.ts",
      "message": "The OpenCode plugin must name its own host, so its judge is not claude -p (ADR-049)."
    }
  ],
  "llm_judge": false,
  "llm_judge_reason": "Both obligations are exact textual requirements the declarative pass checks completely; the behaviour behind them is covered by the gate tests."
}
```
