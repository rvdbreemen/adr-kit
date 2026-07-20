---
id: "ADR-010"
title: "Certify Three Native CLI Clients Through One Outcome Contract"
status: "Accepted"
date: "2026-07-20"
binding: true
gate: "three-client-release"
documents_shipped: false
verified_in:
  - "schemas/client-capabilities.schema.json"
  - "tests/test_client_capabilities_schema.py"
supersedes: []
superseded_by: null
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-010 Certify Three Native CLI Clients Through One Outcome Contract

## Status

Accepted, 2026-07-20.

## Status History

```yaml
status_history:
  - date: 2026-07-19
    status: Proposed
    changed_by: Codex
    reason: TASK-40.1 records the approved three-client architecture and certification policy
    changed_via: adr-kit
  - date: 2026-07-20
    status: Accepted
    changed_by: Robert van den Breemen
    reason: Maintainer approved the three-client contract and authorized the v0.36.0 release candidate
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit already ships native payloads for Claude Code, Codex, and GitHub
Copilot command-line interfaces (CLIs), but those payloads grew as parallel
copies. The current repository has 27 direct `bin/` files, three direct
`scripts/` files, a 991-line `scripts/install-agent-envs.py`, and a 282-line
`bin/adr-doctor`. There is no runtime dependency manifest. Those measurements
show that a fourth client or another copied script family would increase
maintenance before the three existing clients have one explicit outcome and
release contract.

The client hook contracts are not identical. A lifecycle event can inject
context natively in one client while another needs proactive task context,
post-edit confirmation, or deterministic pre-commit enforcement. Treating
event-name parity as product parity would either overstate support or encourage
deny-and-retry behavior that ADR-004 rejected.

Installation and diagnosis also cross versioned local state. During TASK-40.1,
the installed Codex MCP registration attempted to launch
`0.34.0/bin/adr-context` after that cache had been removed, even though 0.35.0
was installed. ADR-006 and ADR-008 cover prepared payloads and version-ranked
engines, but the program still needs client-specific evidence that the
registration resolves to a live target.

The maintainer selected exactly Claude Code CLI, Codex CLI, and GitHub Copilot
CLI for current first-class support. Windows is the native release baseline;
macOS and Linux results are best-effort. All generic portability and additional
clients are deferred to TASK-43 and cannot enter the current installer,
documentation claims, or release gate.

## Decision Drivers

* Users need the same ADR workflow outcomes without false claims that different
  native event models are identical.
* One maintainer must be able to certify and maintain every first-class client.
* Installation, update, rollback, repair, and removal must preserve user-owned
  files and unrelated plugin configuration.
* Agent startup, prompt, edit, compact, and stop paths must remain local,
  bounded, model-free, and fail-open.
* Generated artifacts must stay byte-deterministic while clean and unchanged
  generation remain fast on Windows.
* ADR Kit must preserve its zero-runtime-dependency baseline unless a separate
  decision provides compatibility, security, license, update, and removal
  evidence.
* Release claims must be derived from evidence tied to the exact release
  candidate rather than from documentation or fixture success alone.

## Considered Options

* Define one outcome contract and capability registry for the three native CLI
  clients, with independent evidence and documented degradations.
* Let each native client own an independent semantic implementation and release
  claim.
* Build a generic standards layer first and treat native clients as optional
  wrappers.
* Extend first-class support to every researched client while building the
  shared framework.
* Keep the current copied payloads and informal support claims.

## Decision Outcome

Chosen option: **define one outcome contract and capability registry for the
three native CLI clients**, because it concentrates implementation and
certification effort on the clients the maintainer selected while preserving
honest native differences.

### Scope and outcome contract

The only first-class surfaces in TASK-40 are:

1. `claude-code-cli`;
2. `codex-cli`; and
3. `github-copilot-cli`.

Every client must provide these user outcomes:

1. discover stable ADR Kit skills and prompts;
2. retrieve relevant ADR context for a task;
3. receive governing context before an edit when native, or use a documented
   task, post-edit, and pre-commit backstop;
4. initialize and list the local Model Context Protocol (MCP) tools;
5. retain deterministic pre-commit enforcement as the blocking floor;
6. install, update, roll back, disable, remove, and reinstall ADR Kit without
   clobbering user state; and
7. produce trustworthy fast and deep doctor evidence.

The capability registry records event mappings and degradations per client.
Equal outcomes are required; identical event names are not. A missing required
outcome fails certification. An allowed degradation names its user-visible
effect, reason, and backstop.

### Artifact ownership

| Ownership | Artifacts |
|---|---|
| Canonical | workflow semantics, skill and prompt content, hook intents, MCP intent, settings definitions, guide content, capability and certification metadata |
| Generated | client skill/prompt wrappers, shared guidance, hook wrappers, inventories, support matrix, and release evidence views |
| Hand-authored and validated | client-native manifests and unavoidable platform command declarations |

Generated artifacts carry provenance and are never edited as semantic sources.
Native manifests may remain hand-authored when their schemas differ, but their
version, required references, and declared exceptions are validated. A
client-specific exception requires a registry rationale, a documented user
effect, and a fixture.

`schemas/client-capabilities.schema.json` is the minimal machine contract. It
permits only the three selected client identifiers and records surface and
operating-system scope, required outcomes, native event mappings, degradations,
lifecycle probes, settings keys, and certification references. The registry is
not a future-client catalog.

### Settings, lifecycle, and ownership boundaries

Settings resolve in this order:

1. explicit per-project override;
2. explicit global default; and
3. detected safe default.

Detection is read-only and shown before mutation. Detected clients are selected
by default and can be opted out; an absent client is never selected by a static
client list. Project setup installs deterministic pre-commit enforcement by
default unless the effective setting disables it.

Verified stable updates run outside agent hook hot paths and retain the previous
healthy payload. A breaking change or migration pauses for confirmation. A
failed activation restores the previous healthy payload and diagnostic
evidence. Uninstall removes only ADR Kit-owned registrations, generated files,
managed instruction blocks, payloads, and caches selected for removal.

User-owned configuration, unrelated keys, instruction bytes outside managed
markers, secrets, and `.adr-kit/ADR-guide.local.md` are never automatic repair
or uninstall targets.

Fast doctor uses local files and cached health only. Both fast and deep modes
may repair an enumerated safe deterministic ADR Kit-owned state; `--check`
performs the same diagnosis without mutation. `--fix` additionally authorizes
backed-up configuration rewrites, managed-block replacement, and native plugin
re-registration. Deep doctor may run bounded native, MCP, hook, latency, and
model identity probes.

### Model judgment

ADR-001 continues to prohibit surprise cost-bearing per-commit model work.
Paid or cloud judgment remains explicit opt-in. No hook hot path invokes a
model.

An already configured local provider may be enabled automatically only inside
the documented optional judgment workflow. ADR Kit never compiles a guessed
provider or model tag. Selection uses the project setting, then the global
setting, then unambiguous compatible local discovery. Zero or multiple
candidates remain visibly unconfigured or degraded. Fast doctor checks
configuration and recent cached reachability; deep doctor may issue one bounded
identity and minimal health probe. A missing, ambiguous, unreachable, or
rejected model never appears as successful judgment.

### Performance and engineering budgets

Hook budgets are:

| Path | p50 | p95 | Hard timeout |
|---|---:|---:|---:|
| Session start | 50 ms | 150 ms | 500 ms |
| Prompt ADR ranking | 75 ms | 250 ms | 500 ms |
| Subagent start | 30 ms | 100 ms | 250 ms |
| Pre-tool or post-tool signal | 25 ms | 50 ms | 100 ms |
| Pre-compact checkpoint | 30 ms | 100 ms | 500 ms |
| Stop or subagent-stop checkpoint | 50 ms | 200 ms | 750 ms |
| Session-end cleanup | 100 ms | 500 ms | 1 s |

The benchmark fixes the reference corpus, machine class, sample count,
process-startup inclusion, cold and warm state, and cache state before the
percentile targets become release gates. Hard timeouts apply immediately.
Timeouts fail open and perform the documented fallback or no-op.

Initial deterministic-generation targets for the fixed Windows three-client
fixture are:

| Generator path | p50 | p95 | Hard timeout |
|---|---:|---:|---:|
| Clean full generation | 1 s | 2 s | 5 s |
| Warm unchanged validation and generation | 150 ms | 500 ms | 1 s |

Generation uses declared bounded input roots and an explicit input/output
graph. An unchanged run performs zero content rewrites and preserves output
modification times where feasible. Evidence records sample count, process
startup, files and bytes read and written, peak memory, and percentiles. After
the baseline is approved, an unapproved p95 regression above 20 percent blocks
release. Profiling-led optimization must preserve byte identity, deterministic
ordering, atomic replacement, stale-output detection, and cache invalidation.
Caches remain disposable and cannot become correctness or package inputs.

Public and build entrypoints contain orchestration and argument handling and
target at most 300 physical lines. Support modules target at most 400 physical
lines. TASK-40 adds at most four directly invoked entrypoints and does not add
one executable per client or event. An exception requires a recorded rationale,
responsibility analysis, owner, focused tests, and review.

The zero-runtime-dependency baseline remains. A runtime dependency requires a
separate Proposed ADR covering compatibility, platform support, security,
license, update ownership, exact-pin rationale and review condition, plus a
tested removal or relaxation path. Development and coverage tools do not enter
runtime artifacts.

### Certification and release

Windows native evidence is required independently for all three clients.
macOS/Linux status records either an attempted result or a reason it was not
run and cannot promote an untested surface. Evidence is tied to the exact
release-candidate commit, ADR Kit payload hash, supported client version,
official contract date, environment fingerprint, outcomes, latency, lifecycle,
rollback, preservation, and retained redacted logs.

The candidate checkout cannot contain a bundle that names its own commit
without changing that commit. Redacted native observations and their assembled
bundle are therefore retained on a separate evidence commit. Release automation
pins and verifies both full commit hashes independently, executes validator code
from the candidate, and reads only the evidence bundle from the evidence
checkout.

The release gate fails when any required Windows record is missing, stale, tied
to another commit, or failing. Authenticated maintainer-run smoke is permitted
when hermetic automation cannot provide a client login, but it carries the same
evidence binding.

A release candidate consolidates defaults, hook policy, schemas, and migrations
for the intended stable version. At most one non-emergency stable release is
published per calendar day. An emergency override records the incident,
affected versions, rollback proof, changelog entry, and follow-up review. A
shipped default or hook-policy reversal requires a superseding Proposed ADR and
a new release candidate.

Public archives and plugins are built from an explicit allowlist. Release tests
reject backlog records, `.superpowers`, version-control and continuous
integration internals, tests, caches, local state, secrets, and developer-only
planning or review material.

### Confirmation

Confirm the decision with:

* strict lint and all four ADR quality gates for this Proposed record;
* schema-surface tests that permit exactly the three client identifiers and
  require outcomes, platforms, mappings, degradations, probes, settings, and
  certification references;
* byte-identical clean generation and a zero-write unchanged run;
* Windows cold/warm hook and generator benchmarks under the recorded method;
* installer, doctor, rollback, package-allowlist, and user-preservation
  fixtures;
* independent Windows native certification records for Claude, Codex, and
  Copilot tied to one release candidate; and
* a simulated release gate that fails for missing, stale, cross-commit, or
  failing evidence.

## Consequences

### Positive

* Maintainer effort stays bounded to three selected native clients.
* Users receive one set of workflows and honest, testable native degradations.
* Generated semantics, client manifests, and certification evidence have
  explicit owners instead of drifting as parallel copies.
* Fast paths remain deterministic, model-free, and guarded by executable
  latency budgets.
* Dependency, executable, artifact, and release growth become visible release
  evidence.

### Negative

* A defect in any one required Windows client blocks every stable release.
  Independent evidence and client-specific tasks isolate diagnosis but do not
  weaken that deliberate gate.
* Auto-update and automatic safe repair increase lifecycle complexity.
  Prepared payloads, per-client transactions, backups, bounded repair
  authority, and rollback evidence mitigate the risk.
* Hand-authored native manifests can still drift from canonical intent.
  Schema, provenance, required-reference, and exception validation mitigate
  that risk.
* Strict generator budgets can become noisy across machines. Windows uses a
  recorded reference class and method; macOS/Linux remain best-effort, and a
  reviewed exception is required instead of silently rebasing results.
* Deferring generic and additional-client support limits ecosystem reach.
  TASK-43 preserves the research and requires fresh maintainer approval before
  that cost is accepted.

## Pros and Cons of the Options

### One three-client outcome contract

* Good, because one semantic source serves every selected client.
* Good, because independent evidence makes degradations and failures
  attributable.
* Bad, because the all-three gate lets one client delay a stable release.

### Independent semantic implementations

* Good, because each client can follow its native contract directly.
* Bad, because skills, prompts, hooks, and guidance can diverge silently.
* Bad, because every behavior change requires three independent edits.

### Generic standards layer first

* Good, because standards-based artifacts can reach more environments.
* Bad, because generic discovery cannot prove the native lifecycle, hooks,
  repair, rollback, and trust behavior required for the three selected clients.
* Bad, because the maintainer explicitly deferred generic support to TASK-43.

### Support every researched client

* Good, because ADR Kit would advertise broader ecosystem reach.
* Bad, because every surface adds contract monitoring, fixtures, native smoke,
  migration, doctor, and release evidence.
* Bad, because it violates the approved three-client scope and maintenance
  ceiling.

### Keep copied payloads and informal claims

* Good, because no foundation work is required.
* Bad, because semantic drift, stale launchers, and unverified support claims
  remain undetected until users encounter them.

## Related Decisions

* **ADR-001** keeps cost-bearing model judgment opt-in; this decision permits
  only configured local judgment in its explicit workflow.
* **ADR-004** defines fail-open context tiers and one deterministic pre-commit
  floor; this decision maps those outcomes onto three native event contracts.
* **ADR-005** requires one semantic representation across body profiles; this
  decision applies the same ownership rule to client artifacts.
* **ADR-006** prepares and validates platform-local payloads before native
  activation; this decision adds desired state, rollback, and certification.
* **ADR-007** generates compact views from one semantic source; this decision
  extends deterministic generation to client capability artifacts.
* **ADR-008** version-ranks candidate engines; stale resolved targets remain a
  doctor and Codex certification failure.
* **ADR-009** bounds heuristic gates to actionable findings; performance and
  release exceptions likewise require explicit evidence.

## References

* `docs/plans/cross-client-plugin-implementation-plan.md`
* `docs/research/cross-client-plugin-hooks-report.md`
* `docs/reviews/cross-client-plugin-planning-findings.md`
* `schemas/client-capabilities.schema.json`
* `scripts/install-agent-envs.py:21` - the current three-client identifier
  tuple that the capability schema makes explicit and versioned.
* `bin/adr-doctor`
* TASK-40 and TASK-40.1 in Backlog.md
* Claude Code plugin documentation: <https://code.claude.com/docs/en/plugins>
* Codex hook documentation: <https://learn.chatgpt.com/docs/hooks>
* GitHub Copilot CLI plugin documentation:
  <https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating>

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "\"schema_version\"\\s*:\\s*\\{[\\s\\S]*\"const\"\\s*:\\s*1",
      "path_glob": "schemas/client-capabilities.schema.json",
      "message": "The three-client capability contract must retain an explicit schema version."
    },
    {
      "pattern": "\"claude-code-cli\"[\\s\\S]*\"codex-cli\"[\\s\\S]*\"github-copilot-cli\"",
      "path_glob": "schemas/client-capabilities.schema.json",
      "message": "The TASK-40 capability schema must retain exactly the three selected CLI identifiers."
    }
  ],
  "llm_judge": false
}
```
