# Three-client ADR Kit implementation plan

Status: approved plan; implementation not started
Date: 2026-07-19
Research source: TASK-38 and
[`cross-client-plugin-hooks-report.md`](../research/cross-client-plugin-hooks-report.md)
Planning reviews: TASK-41, TASK-42, and
[`cross-client-plugin-planning-findings.md`](../reviews/cross-client-plugin-planning-findings.md)
Current implementation epic: TASK-40
Future expansion epic: TASK-43

## Current scope

TASK-40 delivers first-class native support for exactly:

1. Claude Code CLI;
2. Codex CLI; and
3. GitHub Copilot CLI.

These are the only client environments in the current implementation,
installer, doctor, hook, certification, documentation, and release scope.
Windows native is the release baseline. macOS and Linux are best-effort.

Every ADR Kit release is blocked until the required certification evidence for
all three clients passes. Each client has an independent certification task so
failures, fixes, and evidence remain attributable.

Shared Agent Skills, prompts, `AGENTS.md`, `CLAUDE.md`, Copilot instructions,
`.adr-kit/ADR-guide.md`, MCP configuration, hooks, and lifecycle tooling remain
in scope only where they directly serve these three clients.

## Future scope

All other client environments and generic portability work belong to TASK-43,
`FUTURE EPIC: Expand ADR Kit beyond Claude, Codex, and Copilot`.

TASK-43 is:

- low priority;
- independent from TASK-40;
- not a TASK-40 release or completion dependency;
- inactive until the maintainer explicitly selects it; and
- required to refresh contracts, versions, adoption, maintenance, surfaces,
  licensing, and priorities before implementation.

The research in TASK-38 remains evidence for that future epic, not current
implementation authority. TASK-40.8 through TASK-40.12 and TASK-40.14 are
archived historical inputs.

## Objectives

- Keep one deterministic Python ADR engine.
- Give Claude, Codex, and Copilot the same user outcomes through honest native
  capabilities.
- Preserve existing public workflow names or provide approved migration
  aliases.
- Make setup, upgrade, rollback, doctor, disable, and removal convergent and
  safe.
- Preserve user-owned instructions and configuration.
- Keep startup, prompt, edit, compact, and shutdown hooks within the approved
  latency budgets.
- Keep deterministic artifact generation fast on both clean/full and
  warm/unchanged paths.
- Derive support claims from executable, release-candidate-bound evidence.

## Non-goals

- Supporting a fourth client, IDE, cloud surface, wrapper, or generic client.
- Installing or testing artifacts for TASK-43 candidates.
- Designing current abstractions around speculative future client contracts.
- Requiring identical native event names or context-injection mechanics.
- Reimplementing ADR parsing, ranking, lint, lifecycle, or enforcement in a
  client adapter.
- Hosted services or required network dependencies.
- Automatic use of paid or cloud model judgment.
- Replacing user content outside ADR Kit-owned markers.

## Existing decisions and required Proposed ADR

Implementation remains constrained by:

- **ADR-001:** cost-bearing model judgment is opt-in.
- **ADR-002:** SessionStart is cheap, local, and fail-open.
- **ADR-004:** session, task, and edit context are bounded layers.
- **ADR-005:** all ADR formats expose the same semantic workflows.
- **ADR-006:** installation prepares and validates a platform-local payload
  before native activation.
- **ADR-007:** deterministic generated indexes are compact agent views.
- **ADR-008:** engines resolve from version-ranked roots; stale removed-cache
  targets are unhealthy.
- **ADR-009:** diagnostics are bounded and actionable.

TASK-40.1 creates a Proposed ADR recording:

- the three-client ceiling;
- equal user outcomes with documented native degradations;
- canonical, generated, and hand-authored ownership;
- capability and certification metadata;
- settings precedence;
- update, rollback, and doctor repair authority;
- the Windows-first release gate;
- local versus cloud judgment defaults; and
- the latency measurement contract.

It must not decide or implement TASK-43 behavior.

## First-class outcome contract

For each of Claude, Codex, and Copilot, a user can:

1. discover the same ADR workflows and names;
2. load relevant ADR context for a task;
3. receive governing context before an edit where the native contract permits
   it, or an honest documented backstop where it does not;
4. use the local ADR Kit MCP server;
5. rely on deterministic pre-commit enforcement as the floor;
6. install, update, roll back, disable, and remove ADR Kit safely; and
7. obtain trustworthy doctor evidence.

The capability registry records native event mappings and degradations. It may
not claim identical lifecycle behavior when client contracts differ.

## Ownership model

Canonical sources own:

- workflow semantics;
- skill and prompt content;
- hook intents and bounded outputs;
- MCP intent;
- shared guide content;
- settings definitions; and
- capability and certification metadata.

The generator creates or assembles shared semantic artifacts and client
wrappers for the three clients. Native manifests may remain hand-authored when
that is clearer, but they are schema-validated and tied to the canonical ADR
Kit version. Client exceptions require a registry rationale, documented
degradation, and tests.

`.adr-kit/ADR-guide.md` is generated ADR Kit-owned content and is replaced
after backup. Users keep custom guidance:

- outside ADR Kit markers in `AGENTS.md`, `CLAUDE.md`, and
  `.github/copilot-instructions.md`; or
- in `.adr-kit/ADR-guide.local.md`, referenced by the generated guide.

ADR Kit does not create singular `AGENT.md` as a standard.

## Settings and automation policy

`adr-kit:settings` provides global defaults with per-project overrides for:

- pre-commit installation;
- update channel, trigger, frequency, pinning, and offline mode;
- Claude, Codex, and Copilot opt-outs;
- local-model and paid/cloud judgment;
- doctor automatic repair and `--check` behavior; and
- client-specific disabled state.

Project setup:

1. detects the three clients and previous ADR Kit versions without writing;
2. presents detected state and planned actions;
3. defaults to installing detected selected clients;
4. offers per-client opt-outs;
5. installs pre-commit by default unless disabled in settings; and
6. converges to the same state on repeated runs.

Verified stable updates install automatically and retain a working rollback
target. A safe native update manager is used where available; otherwise ADR
Kit uses deferred maintenance outside every agent hook hot path. Update state
records the approved source, authenticated release manifest, payload digest,
trigger, and last check.

Breaking changes and migrations pause for confirmation. Failed activation
restores the previous healthy state.

Configured local-model judgment is enabled automatically only in its
documented judgment workflow. Paid or cloud judgment remains explicit opt-in.
No provider or model tag is compiled as a fallback. Selection uses a project
setting, then a global setting, then unambiguous compatible local discovery.
Zero or multiple candidates leave judgment visibly unconfigured or degraded
until the user chooses. No model judgment runs in hook hot paths.

## Doctor contract

`adr-doctor` is fast by default. `adr-doctor --deep` adds bounded native,
MCP, hook, and latency checks.

Both modes may automatically repair enumerated safe, deterministic ADR
Kit-owned state. `--check` performs the same diagnosis without repair.
`--fix` additionally authorizes backups, config rewrites, managed-block
replacement, and native plugin re-registration.

No mode mutates unrelated keys, content outside markers,
`.adr-kit/ADR-guide.local.md`, arbitrary user files, secrets, or non-ADR Kit
plugin state.

The doctor task establishes the versioned deep-probe contract. TASK-40.3 plugs
hook and latency probes into it after the hook core exists.

Human and JSON output distinguish healthy, repaired, degraded, disabled,
trust/review pending, stale, unsupported-version, and failed states. The
current-manifest-to-removed-cache launcher class is a required Codex fixture.
Fast doctor checks configured model identity and recent cached reachability
without invoking a model. Deep doctor may run a bounded provider/model identity
and minimal health probe. Missing, ambiguous, unreachable, or rejected models
remain distinct actionable degraded states; optional judgment cannot disappear
behind an overall healthy result.

## Hook and latency contract

Hooks are local, deterministic, and fail open. They do not rebuild indexes,
install or update software, invoke models, contact a network, or mutate ADR
lifecycle state.

| Path | p50 target | p95 target | Hard timeout | On timeout |
|---|---:|---:|---:|---|
| SessionStart | 50 ms | 150 ms | 500 ms | cached minimum or nothing |
| UserPromptSubmit ADR ranking | 75 ms | 250 ms | 500 ms | lexical references only |
| SubagentStart | 30 ms | 100 ms | 250 ms | parent bundle or project guide |
| PreToolUse / PostToolUse | 25 ms | 50 ms | 100 ms | no-op; pre-commit remains |
| PreCompact checkpoint | 30 ms | 100 ms | 500 ms | no-op |
| Stop / SubagentStop checkpoint | 50 ms | 200 ms | 750 ms | no-op |
| SessionEnd cleanup | 100 ms | 500 ms | 1 s | no-op |

TASK-40.3 defines the reference corpus, machine class, sample count,
cold-process and warm-process runs, cache state, process-startup inclusion, and
permitted CI variance before the percentile targets become release gates.
Hard timeouts are always executable safety limits.

## Engineering and release guardrails

The pre-implementation baseline measured on 2026-07-19 is:

| Surface | Baseline |
|---|---:|
| `scripts/install-agent-envs.py` | 991 physical lines |
| `bin/adr-doctor` | 282 physical lines |
| Direct files under `bin/` | 27 |
| Direct files under `scripts/` | 3 |
| Runtime dependency manifest | none found |

TASK-40 uses these enforceable complexity controls:

- public and build entrypoints contain orchestration and argument handling
  only and target no more than 300 physical lines;
- single-responsibility support modules target no more than 400 physical
  lines;
- TASK-40 adds at most four directly invoked entrypoints;
- client and event differences are registry/data-driven, not implemented as a
  new script per client or hook event; and
- an exception requires a recorded rationale, responsibility analysis, owner,
  focused tests, and approval through the TASK-40.1 policy.

The 991-line installer must be decomposed; extending the monolith does not
satisfy this plan. The 282-line doctor must remain a thin entrypoint as client,
model, repair, and deep-probe behavior moves to tested support modules.

ADR Kit preserves the measured zero-runtime-dependency baseline. A runtime
dependency requires its own Proposed ADR covering compatibility, security,
license, update ownership, exact-pin rationale and review/expiry condition,
and a tested removal or relaxation path. Development and coverage tools remain
separate from runtime artifacts. Release evidence inventories both sets and
their licenses.

Installer defaults are calculated from detected executables, native manager
state, and effective settings. No static `claude,codex`, all-client, or similar
default may select an absent client unless the user explicitly requests it.

Stable publication follows a release candidate that consolidates intended
defaults, hook policy, schemas, and migrations. At most one non-emergency
stable release may be published per calendar day. An emergency override
records the incident, affected versions, rollback proof, changelog entry, and
follow-up review. Reversing a shipped default or hook policy requires a
superseding Proposed ADR and a new release candidate; it is not hidden in a
same-day patch.

Public archives and plugins are built from an explicit allowlist. Negative
tests reject `backlog/`, `.superpowers/`, VCS and CI internals, tests, caches,
local state, secrets, and developer-only planning or review material.

### Deterministic generation performance

Performance is part of the generator contract, not a cleanup activity after
correctness work. Every TASK-40 deterministic generator uses declared bounded
input roots and an explicit input/output graph. It may use content, tool
version, and schema fingerprints to skip unchanged nodes, but disposable local
caches are never required for correctness or included in a package.

Initial Windows-native targets for the fixed three-client reference fixture
are:

| Generator path | p50 target | p95 target | Hard timeout |
|---|---:|---:|---:|
| Clean full generation | 1 s | 2 s | 5 s |
| Warm unchanged validation/generation | 150 ms | 500 ms | 1 s |

The benchmark records the reference machine class, fixture and artifact set,
process-startup inclusion, cold/warm state, sample count, files and bytes read
and written, peak memory, and p50/p95/max. macOS/Linux results are best-effort
status.

An unchanged run performs zero content rewrites and preserves output mtimes
where feasible. Generators do not scan unrelated VCS, backlog, cache,
developer, or local-state trees. Profiling precedes optimization, and
performance changes may not weaken byte-identical output, deterministic
ordering, stale-output detection, atomic replacement, or cache invalidation.

After the initial baseline is approved, an unapproved p95 regression greater
than 20%, any hard-timeout breach, an unexpected unchanged-output write, or an
unbounded input scan blocks the release candidate. Changing the fixture,
method, or budget requires reviewed evidence under TASK-40.1 rather than
silently rebasing the benchmark.

## Current task graph

```text
TASK-40.1  three-client architecture ADR + minimal capability schema
   |
   +--> TASK-40.4  guide + managed instructions + settings
   |       |
   |       +--> TASK-40.2  canonical three-client artifacts
   |
   +--> TASK-40.13 certification schema + all-three gate algorithm

40.2 + 40.13
   |
   +--> TASK-40.5  three-client detection/install/update/rollback
            |
            +--> TASK-40.6  doctor framework + repair boundaries
                     |
                     +--> TASK-40.3  hooks + latency + deep-doctor probes

After 40.2/40.3/40.4/40.5/40.6/40.13:

TASK-40.7  native coordination container
   |
   +--> TASK-40.7.1  Claude normalization + certification
   +--> TASK-40.7.2  Codex normalization + certification
   +--> TASK-40.7.3  Copilot normalization + certification
            |
            +--> all-three release gate passes
```

There is no dependency from TASK-40 to TASK-43.

## Execution phases

### Phase 1 — Policy, guide, and settings

**TASK-40.1** records the Proposed ADR and minimal three-client capability
schema. Stop if an Accepted decision must change; use the normal supersession
lifecycle instead of editing history.

**TASK-40.4** delivers generated and local guidance, marker-owned client
instruction blocks, effective settings, and default pre-commit setup. Its
first slice is read-only settings resolution and a dry-run file plan.

### Phase 2 — Canonical artifacts and lifecycle

**TASK-40.2** normalizes semantic sources and generates or validates only
Claude, Codex, and Copilot artifacts. It also owns the bounded incremental
generation DAG and clean/full plus warm/no-op performance harness.

**TASK-40.13** establishes the certification schema, candidate-commit binding,
evidence freshness, simulated pass/fail fixtures, and release-gate algorithm
before live client evidence exists. Missing live evidence correctly blocks a
release candidate, not ordinary pull requests. Its schema includes generator
performance and unchanged-write evidence from the start.

**TASK-40.5** implements read-only three-client detection, desired-state
installation, verified stable updates, confirmation for breaking migrations,
rollback, disable, and uninstall. Its first slice is accurate detection and
human/JSON dry-run output.

**TASK-40.6** delivers fast/deep doctor, `--check`, automatic safe repair, and
transactional `--fix`. Its first slice resolves actual launcher targets and
diagnoses stale cache/version skew on Windows.

### Phase 3 — Hooks and native certification

**TASK-40.3** implements only hook behavior serving the three-client outcome
contract, plus the complete benchmark methodology and deep-doctor integration.
SubagentStart and PreCompact are used only where native and useful.

**TASK-40.7** coordinates public-name compatibility, shared outcome
documentation, aggregate regression evidence, and final release readiness. It
is not a dependency of its own children.

**TASK-40.7.1**, **TASK-40.7.2**, and **TASK-40.7.3** independently normalize
and certify Claude Code CLI, Codex CLI, and Copilot CLI. Windows evidence is
required. macOS/Linux status is best-effort and may record “not run” with a
reason.

## Certification and release policy

Required evidence is tied to:

- the release-candidate commit;
- ADR Kit version and payload hash;
- supported client version;
- official contract date/version;
- Windows environment fingerprint;
- required user outcomes;
- cold/warm latency results;
- native lifecycle results;
- rollback and preservation proof; and
- retained redacted fixture/native logs.

Where login or interactive state prevents hermetic CI, a maintainer-run smoke
is allowed only with the same evidence binding. Ordinary pull requests validate
schemas, simulated gate behavior, and available fixtures without requiring
authenticated clients.

A release is blocked when any of the three required evidence records is
missing, stale, tied to another candidate commit, or failing.

Certification also records the entrypoint/module size inventory and executable
delta from the baseline, runtime and development dependency inventories,
exact-pin rationale, license/security/update ownership, and public-archive
allowlist results. An unapproved budget overrun, runtime dependency, or
forbidden packaged path blocks release.

## Migration and rollback

For each of the three clients:

1. detect current and legacy state;
2. show human and JSON plans;
3. back up owned and explicitly selected config targets;
4. prepare and validate the immutable payload;
5. activate one client transaction;
6. run bounded health checks;
7. retain the previous healthy target;
8. restore it automatically on failed stable update; and
9. remove only ADR Kit-owned state during uninstall.

Breaking migrations stop for confirmation. Safe no-op upgrades remain
non-interactive.

## Risk controls

| Risk | Control | Owner |
|---|---|---|
| Three native contracts drift | independent certification and dated evidence | 40.7.1-.3, 40.13 |
| Shared semantics fork | canonical sources and validated exceptions | 40.2 |
| User instructions are clobbered | markers, backups, local guide, byte tests | 40.4 |
| Auto-update breaks a client | authenticated source, digest, health check, rollback | 40.5 |
| Doctor mutates too much | safe-repair list, `--check`, transactional `--fix` | 40.6 |
| Hooks slow startup or edits | hard timeouts and cold/warm benchmarks | 40.3 |
| Live smoke is irreproducible | candidate/version/environment evidence binding | 40.13 |
| Future scope leaks into current work | separate TASK-43 with no dependency | 40, 43 |
| Installer or doctor becomes a monolith | measured line budgets, thin entrypoints, exception gate | 40.1, 40.5, 40.6, 40.13 |
| Script count grows per client/event | executable inventory and data-driven adapters | 40.2, 40.13 |
| Runtime dependencies drift or bloat | zero baseline, dependency ADR, split inventories | 40.1, 40.2, 40.13 |
| Stable releases churn or reverse policy | consolidated RC, daily limit, emergency evidence, superseding ADR | 40.1, 40.13 |
| Internal files leak into packages | explicit allowlist and negative archive tests | 40.2, 40.13 |
| Local judgment silently does nothing | explicit model selection and actionable degraded states | 40.4, 40.6 |
| Deterministic generation becomes slow | bounded DAG, no-op writes, profiling, Windows budgets, regression gate | 40.1, 40.2, 40.13 |

## TASK-40 completion

TASK-40 is Done only when:

- the policy ADR and capability/certification schemas pass their required
  lifecycle and validation;
- settings, guide, installer, rollback, doctor, and hooks meet their task
  criteria;
- TASK-40.7.1, TASK-40.7.2, and TASK-40.7.3 are Done with current Windows
  evidence;
- macOS/Linux best-effort status and limitations are recorded;
- the pre-commit, model judgment, update, and repair defaults match this plan;
- installation and upgrade are idempotent and preserve user-owned state;
- entrypoint, module, and executable-growth budgets pass or link an approved
  exception;
- runtime/development dependency and license evidence preserves the approved
  zero-runtime baseline;
- the stable release obeys the release-candidate consolidation and cadence
  policy;
- public packages pass allowlist and forbidden-path checks;
- clean/full and warm/unchanged generator benchmarks pass, unchanged output is
  not rewritten, and no unapproved performance regression remains;
- local judgment validates an explicit or unambiguous provider/model and
  reports unavailable judgment as degraded instead of silently succeeding;
- strict ADR lint, indexes, fixtures, regression tests, and the release gate
  pass; and
- no TASK-43 client is advertised, installed, tested, or required by TASK-40.

## TASK-43 future expansion

TASK-43 preserves:

- a possible generic standards layer;
- OpenCode, Kilo Code, and Kimi Code;
- Cursor and VS Code agent surfaces;
- goose, Qwen Code, Gemini CLI, OMP, and Pi; and
- every remaining TASK-38 watchlist candidate.

When explicitly activated, TASK-43 begins by refreshing all external facts and
the maintainer's maintenance budget. It then selects a small wave and creates
one bounded implementation/certification task per client surface. Research
inclusion never becomes an automatic support promise.
