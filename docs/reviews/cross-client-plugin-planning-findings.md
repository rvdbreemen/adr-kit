# Adversarial review of the cross-client ADR Kit plan

Status: review complete; findings resolved by maintainer interview
Date: 2026-07-19
Reviewed:

- TASK-38 research;
- TASK-40 epic;
- TASK-40.1 through TASK-40.14;
- TASK-41; and
- `docs/plans/cross-client-plugin-implementation-plan.md`.

## Review conclusion

The architecture direction is sound: one deterministic Python engine,
portable canonical artifacts, thin client adapters, non-clobbering guidance,
idempotent installation, and evidence-based support claims.

The implementation plan is not yet efficient enough to execute. It assumes a
large target-client set before the maintainer has selected the platforms that
matter. It also puts too much foundation work ahead of the first useful
vertical slice and couples independent client releases into one large
certification dependency.

The most important correction is not technical. The maintainer must first
choose:

1. the clients and surfaces used regularly;
2. the clients that deserve full native support;
3. the desired generic portability floor;
4. the operating systems that require release-grade support;
5. update and enforcement defaults; and
6. the recurring maintenance budget.

Until those choices are made, TASK-40 and its subtasks should remain To Do.
This review does not make those choices.

## Blocking findings

### P-01 — The target list is a hidden product decision

Severity: blocker

The plan promotes Kimi, Kilo, Qwen, Gemini, Cursor local, VS Code Agent
Plugins, OMP, and Pi to “first implementation targets” before establishing
which clients the maintainer actually uses or expects users to use.

Consequence:

- substantial effort may go to impressive but unused integrations;
- each target adds permanent contract monitoring, fixtures, documentation,
  native smoke work, installer branches, and doctor branches;
- a broad target list reduces the quality available for the major platforms.

Required decision:

- identify the two or three primary clients;
- identify at most one exploratory native client; and
- classify all remaining clients as generic portability, contract research, or
  deferred.

### P-02 — The epic cannot ship incrementally as currently wired

Severity: blocker

TASK-40.13 depends on TASK-40.7 through TASK-40.12. The plan simultaneously
says releases should happen in independent waves. Those statements conflict:
the certification/release gate arrives only after every adapter family.

Consequence:

- Claude/Codex/Copilot foundation improvements cannot complete the epic or use
  the final gate until Kimi, Kilo/OpenCode, Cursor/VS Code/goose, Qwen/Gemini,
  and OMP/Pi all finish;
- a low-priority adapter can block a high-value release;
- the branch remains large and risky.

Required decision:

- make a minimal certification framework an early foundation task;
- certify and release each client independently; and
- make the epic a program container, not a single all-or-nothing release.

### P-03 — There is no explicit generic-support deliverable

Severity: blocker

The user preference is strong support for major platforms plus interesting
generic support. The plan mostly expresses generic support as a downgrade
state. It does not define one concrete portable bundle.

Missing deliverable:

- standard `SKILL.md` packages under `.agents/skills`;
- `AGENTS.md` managed block;
- `.adr-kit/ADR-guide.md`;
- local MCP launch descriptor or documented manual registration;
- prompt/workflow Markdown where a neutral convention is possible;
- a generic doctor report that says which parts a client discovered.

Consequence:

Many clients could receive useful ADR Kit behavior cheaply, but the plan
instead proposes expensive native adapters.

Required decision:

- define the minimum generic support promise;
- decide whether hooks are required for “generic support” or deliberately
  excluded; and
- decide whether generic support is installed automatically, explicitly, or
  only documented.

### P-04 — Required support surfaces and operating systems are unspecified

Severity: blocker

The plan frequently requires Windows, macOS, and Linux certification and, for
Kilo, both CLI and VS Code. It does not establish whether all are actual
release requirements.

Consequence:

- native smoke requirements may be impossible in ordinary CI because clients
  need logins, model access, GUI hosts, preview builds, or licenses;
- IDE and CLI behavior can double the work for one product name;
- three-platform support multiplies every migration and quoting test.

Required decision:

- choose release-grade operating systems;
- choose CLI versus IDE surfaces per product;
- decide which tests are hermetic CI, scheduled native smoke, or maintainer
  manual evidence.

### P-05 — Support quality has no recurring maintenance budget

Severity: blocker

The 2,000-star gate filters initial candidates but says nothing about how many
adapters one maintainer can keep current.

Every native adapter requires:

- official-contract monitoring;
- fixture refreshes;
- native client installation;
- update and migration testing;
- support documentation;
- issue triage; and
- release/demotion decisions.

Required decision:

- set a maximum first-class client count;
- choose a review cadence;
- define when a client is demoted or removed; and
- state how much release time may be spent on non-primary clients.

## Major findings

### P-06 — The plan builds too much framework before proving a vertical slice

Severity: major

TASK-40.1 through TASK-40.6 build an ADR, schema, generator, hook protocol,
instruction migrator, desired-state installer, rollback system, and doctor
before the first client is migrated in TASK-40.7.

Risk:

The abstractions may be shaped by documentation rather than executable client
behavior. Rework becomes likely when the first native adapter disagrees with
the generic schema.

Alternative to decide:

- build the smallest foundation needed for one current primary client and one
  structurally different client;
- generalize only after both pass;
- then extract the registry, generator, and common doctor contracts.

### P-07 — The plan assumes semantic parity where honest degradation may be better

Severity: major

Different clients cannot all inject context at the same lifecycle boundary.
Copilot PreToolUse is already a documented example. Requiring identical hooks
can lead to denial/retry tricks or excessive session context.

Decision needed:

- define essential user outcomes rather than identical event names;
- define acceptable degradations per outcome;
- decide which missing outcome blocks support.

Candidate outcome contract:

1. agent can discover ADR workflows;
2. task can request relevant ADRs;
3. edits receive governing context before or immediately after the write;
4. MCP remains available;
5. deterministic pre-commit remains the floor; and
6. installer/doctor state is trustworthy.

### P-08 — Performance numbers need a measurement policy before becoming release gates

Severity: major

The latency budgets are valuable, but TASK-40.3 and TASK-40.13 do not yet define
fixture size, warm/cold cache state, machine class, process startup inclusion,
sample count, or allowed CI variance.

Risk:

- noisy CI failures;
- benchmarks optimized for artificial fixtures;
- hidden slow first-use behavior.

Decision needed:

- distinguish cold process, warm process, and cached index measurements;
- choose the reference corpus size;
- decide which budget is hard CI versus advisory native telemetry.

### P-09 — Auto-update and universal rollback may be overpromised

Severity: major

Some clients have native plugin transactions; others use config files,
marketplaces, npm, or copied scripts. A universal automatic rollback promise
may not be implementable safely.

Decision needed:

- choose the default update policy;
- decide whether rollback means native rollback, prepared-payload pointer
  rollback, config restore, or a repair command per client;
- decide whether pre-1.0 ADR Kit should auto-apply minor updates.

### P-10 — Doctor scope should be split into fast and deep modes

Severity: major

TASK-40.6 includes configuration inspection, native probes, MCP calls, hook
fixtures, latency measurements, and stale-root traversal in one doctor.

Risk:

- normal doctor becomes slow and noisy;
- logged-out clients look broken;
- tests that launch native clients surprise users.

Potential split for user approval:

- `adr-doctor`: local, read-only, fast, no login, no model, no native turn;
- `adr-doctor --deep`: native plugin list, MCP smoke, hook fixture, latency;
- release certification: authenticated/interactive smoke where unavoidable.

### P-11 — The current-client task is too large

Severity: major

TASK-40.7 combines Claude, Codex, and Copilot. Each has different manifests,
hooks, trust, update, failure, and instruction behavior.

Risk:

- one client blocks fixes for another;
- review surface is large;
- rollback and release attribution are unclear.

Potential change:

- one shared migration task;
- one client task for each current primary client;
- leave an unused current adapter in maintenance-only mode until selected.

### P-12 — Several client-family tasks combine independent products

Severity: major

- TASK-40.9 combines Kilo and OpenCode.
- TASK-40.10 combines Cursor, VS Code, and goose.
- TASK-40.11 combines Qwen and Gemini.
- TASK-40.12 combines OMP and Pi.

Shared code is a reason to share a library, not necessarily a reason to share
task completion.

Risk:

- the least mature product blocks the strongest product;
- client-specific evidence is obscured;
- promotion and rollback are coupled.

Potential change:

- one small family-bridge task;
- one certification task per selected client/surface;
- no task for unselected clients.

### P-13 — TASK-40.14 is an open-ended research sink

Severity: major

Nine contract-test clients in one task can consume large amounts of effort
without improving current users.

Potential change:

- move the list to a watchlist document;
- create a prototype task only when a client is nominated by usage, demand, or
  ecosystem change;
- cap each prototype with a time budget and one blocking question.

### P-14 — The plan lacks effort estimates and stop conditions

Severity: major

Tasks have many acceptance criteria but no relative size or explicit condition
for intentionally stopping.

Suggested planning scale:

- S: one focused change, one client/config surface;
- M: cross-platform deterministic component;
- L: native client adapter with installer and doctor;
- XL: multi-client foundation or certification system.

Every client task should include:

- expected size;
- prerequisites;
- earliest useful slice;
- stop condition;
- promotion condition; and
- recurring maintenance cost.

## Task-by-task findings

### TASK-40 — Epic

Assessment: directionally correct, overcommitted.

Findings:

- It names eight expansion targets without maintainer prioritization.
- Completion depends on broad client support rather than a smaller product
  outcome.
- It should be a program container with independently releasable milestones.
- Its support list must be revised after the interview.

### TASK-40.1 — Architecture ADR and capability registry

Assessment: necessary, but overloaded.

Findings:

- The ADR decision and schema implementation are mixed.
- The 2,000-star threshold may belong in support policy rather than an
  architectural decision.
- The ADR should define minimal outcomes and degradation policy before listing
  every lifecycle event.
- The schema should follow a two-client executable spike, or remain minimal
  enough to change cheaply.

### TASK-40.2 — Canonical artifact generator

Assessment: high value after scope is reduced.

Findings:

- Generating every artifact at once risks migration churn.
- First prove canonical skills and workflow metadata for two selected clients.
- Decide whether manifests should be generated or validated; hand-authored
  native manifests can be clearer when formats differ sharply.
- “No independently edited copies” is correct for semantic instructions, but
  too strict for client-native packaging files.

### TASK-40.3 — Hook core and performance

Assessment: valuable, currently broader than ADR Kit needs.

Findings:

- SubagentStart is useful but not obviously a first-release requirement.
- No-op support for every lifecycle event creates fixture work without user
  value.
- Prompt-tier injection should be validated against context duplication.
- Performance gates need cold/warm/reference-corpus definitions.
- The first slice should be SessionStart plus pre/post edit for primary
  clients.

### TASK-40.4 — ADR-guide and managed instructions

Assessment: high-value, mostly client-independent.

Findings:

- This can deliver value early and should not wait for broad plugin support.
- Full three-way merge behavior may be unnecessary; marker replacement plus
  local-modification detection and backup may suffice.
- Creating multiple client instruction files should depend on selected
  clients, not every detected executable.
- The guide ownership and local-edit policy needs a user choice.

### TASK-40.5 — Installer/update/rollback

Assessment: highest implementation risk.

Findings:

- It combines detection, planning, installation, migration, updates, rollback,
  and uninstall for every client.
- Split core desired-state planning from individual native mutators.
- Default auto-update is a user policy, not an implementation assumption.
- Native rollback semantics differ and must be described honestly.
- Start with current primary clients and prepared-payload repair.

### TASK-40.6 — Doctor

Assessment: essential, too broad for one default command.

Findings:

- Fast doctor and deep certification should be separate.
- Login/model-dependent probes should never run by default.
- Latency sampling belongs in deep/release mode.
- Stale launcher and MCP target resolution are immediate high-value work.

### TASK-40.7 — Claude, Codex, and Copilot

Assessment: must be prioritized by actual use.

Findings:

- Three independent clients in one task is poor release isolation.
- Codex stale-cache repair may deserve the first vertical slice.
- Copilot should not receive equal effort if it is not a primary platform.
- Claude compatibility must remain stable while shared artifacts change.

### TASK-40.8 — Kimi Code

Assessment: technically strong, product priority unconfirmed.

Findings:

- Excellent reference contract does not prove maintainer or user demand.
- Legacy Kimi migration is unnecessary unless an old installation is detected
  or supported users exist.
- Three-OS native certification is costly for a non-primary client.
- It should remain a candidate until the interview.

### TASK-40.9 — Kilo Code and OpenCode

Assessment: promising generic family, incorrectly coupled.

Findings:

- Kilo CLI, Kilo VS Code, and OpenCode are three release surfaces.
- Shared TypeScript bridge work can be one task; certification should be
  separate.
- Kilo’s adoption and active contract make it a rational exploratory choice,
  but actual maintainer use should decide.
- `KILO_PURE=1` is a good doctor check, not a reason to commit to the platform.

### TASK-40.10 — Cursor, VS Code, and goose

Assessment: too many maturity levels in one task.

Findings:

- Cursor local, Cursor cloud, Cursor CLI, VS Code preview, and goose are
  separate support decisions.
- VS Code may matter broadly but Agent Plugins are preview.
- goose should not block Cursor or VS Code.
- Split only after the maintainer identifies a selected surface.

### TASK-40.11 — Qwen and Gemini

Assessment: technically shareable, likely deferrable.

Findings:

- Gemini’s transition guidance raises maintenance risk.
- Qwen may be useful if the maintainer uses it or wants Gemini-family reach.
- Shared generation does not require both to ship.
- Do not start until one is selected.

### TASK-40.12 — OMP and Pi

Assessment: interesting, likely niche.

Findings:

- Both require TypeScript/package expertise and extension-owned capabilities.
- Their generic skills/AGENTS/MCP compatibility may provide most value without
  native first-class support.
- Native support should require a concrete user or strategic reason.

### TASK-40.13 — Certification and release

Assessment: essential, sequenced too late.

Findings:

- A minimal evidence model is needed before client tasks begin.
- The final task should aggregate evidence, not invent the criteria after
  adapters are implemented.
- It must not depend on every candidate family.
- Native authenticated tests need a defined operator and cadence.

### TASK-40.14 — Remaining prototypes

Assessment: defer.

Findings:

- The task is too broad to finish in one focused pass.
- It conflicts with spending effort on major platforms.
- Replace it with a watchlist; create one bounded spike only after nomination.

### TASK-41 — Durable plan

Assessment: useful planning artifact, prematurely prescriptive.

Findings:

- It accurately captures the created task graph.
- The “first implementation targets” and release waves must be revised after
  user choices.
- The generic-support floor is missing.
- The plan should be versioned after the interview, not treated as approved.

## Proposed simplification options

These are options for the maintainer to choose from, not recommendations that
have been applied.

### Option A — Focused core

- Fully support two primary clients.
- Keep one existing secondary client regression-compatible.
- Ship portable skills + AGENTS.md + MCP as generic support.
- Add no new native client in the first program.

Lowest ongoing maintenance; fastest path to reliable installer and doctor.

### Option B — Core plus one exploratory client

- Fully support two or three primary clients.
- Ship the generic support bundle.
- Add either Kimi or Kilo as one structurally different reference adapter.
- Defer every other native client.

Tests whether the architecture generalizes without committing to a matrix.

### Option C — Ecosystem expansion

- Normalize all current clients.
- Add Kimi, Kilo, Cursor/VS Code, Qwen/Gemini, and OMP/Pi.
- Maintain three-OS native certification.

Maximum reach, highest initial and recurring cost.

### Option D — Standards-first

- Prioritize Agent Skills, AGENTS.md, MCP, portable prompts, and one generic
  installer/doctor.
- Keep only current native hook adapters.
- Add native clients only when portable support proves insufficient.

Broad practical reach with intentionally weaker automatic lifecycle behavior.

## Interview decisions

The plan cannot be finalized responsibly without the maintainer’s answers to:

1. Which coding clients are used weekly?
2. Which client surfaces matter: CLI, VS Code/IDE, cloud, or more than one?
3. Which operating systems require release-grade support?
4. How many first-class clients can ADR Kit maintain well?
5. Is generic support allowed to omit native hooks?
6. Is one exploratory adapter desirable, and if so should it be Kimi, Kilo,
   or another client?
7. Should updates be automatic, notify-first, or pinned by default?
8. Should `adr-doctor` default to fast local checks with a separate deep mode?
9. Should the pre-commit enforcement hook be opt-in, recommended, or automatic?
10. How often should native client certifications be refreshed?

These questions were answered in the interactive maintainer interview. The
approved decisions and their effect on the plan are recorded below.

## Interview resolution

The maintainer approved the following scope:

1. Claude Code CLI, Codex CLI, and GitHub Copilot CLI are the only first-class
   clients, in that priority order.
2. All three are independently certified, and every ADR Kit release is blocked
   unless all three required certification sets pass.
3. Windows native is the release baseline; macOS and Linux are best-effort.
4. OpenCode is periodically tested as the generic reference client.
5. Kilo Code CLI and Kimi Code are untested, best-effort generic
   compatibility. Kilo's VS Code surface is deferred.
6. Generic support consists of Agent Skills, `AGENTS.md`, generated
   `.adr-kit/ADR-guide.md`, local MCP intent, portable prompts/workflows, and
   only hook formats that work unchanged from a supported native client.
7. Generic support installs by default with opt-out. Client detection is shown
   before changes, and selection screens contain at most four clients.
8. The implementation order is guide/settings, installer/doctor, then hooks
   and latency.
9. Native manifests may remain hand-authored and schema-validated; shared
   semantics and portable artifacts are generated. Exceptions belong in the
   capability registry.
10. First-class parity means equal user outcomes with documented native
    differences, not identical lifecycle events.
11. Verified stable updates install automatically with rollback. Breaking
    changes and migrations pause for confirmation.
12. `adr-doctor` is fast by default and `--deep` adds native, MCP, hook, and
    latency probes. Both repair safe deterministic ADR Kit-owned state;
    `--fix` additionally authorizes backups, config rewrites, and plugin
    re-registration.
13. Project setup installs the pre-commit gate by default; `adr-kit:settings`
    can disable it. Settings have global defaults and per-project overrides.
14. Configured local-model judgment defaults on; paid/cloud judgment remains
    opt-in.
15. `.adr-kit/ADR-guide.md` is generated and replaced after backup. Users keep
    custom guidance outside managed instruction markers or in
    `.adr-kit/ADR-guide.local.md`.

### Finding disposition

| Finding | Resolution |
|---|---|
| P-01 target list | Three native clients only; no expansion wave |
| P-02 late all-or-nothing gate | Early certification framework; separate client evidence |
| P-03 missing generic deliverable | Dedicated Level-4 generic bundle |
| P-04 OS and surfaces | Windows native CLI; macOS/Linux best-effort |
| P-05 maintenance budget | Three-client first-class ceiling |
| P-06 framework before slice | Guide/settings and current clients shape the abstractions |
| P-07 exact parity | User-outcome contract with documented degradations |
| P-08 measurement ambiguity | TASK-40.3 must define cold/warm/reference methodology |
| P-09 update promise | Verified stable auto-update; rollback; confirmation for breaking work |
| P-10 doctor scope | Fast and deep modes with explicit repair authority |
| P-11 combined client task | Shared normalization plus three certification subtasks |
| P-12 bundled new products | Native product-family tasks canceled |
| P-13 research sink | Prototype task archived; TASK-38 remains the watchlist |
| P-14 effort and stop rules | Task scopes include earliest slice and explicit boundaries |

The revised durable plan and TASK-40 graph implement these decisions. This
review remains as the adversarial record; its earlier alternatives are not
current commitments.

## Post-interview task audit

A second adversarial pass reviewed every retained task after the interview
rewrite. It found and corrected the following execution defects.

### R-01 — Doctor and hook work had a hidden dependency cycle

TASK-40.6 required completed hook latency probes while TASK-40.3 depended on
TASK-40.6. The doctor task now owns the deep-probe schema and native/MCP
framework; TASK-40.3 owns hook/latency implementation and plugs it into that
stable contract.

### R-02 — Certification children could not finish their parent

TASK-40.7.1 through TASK-40.7.3 originally depended on TASK-40.7, while
TASK-40.7 could only finish after its children. TASK-40.7 is now a coordination
container. Each child depends directly on the shared foundation tasks and owns
its client-specific normalization plus certification.

### R-03 — Early certification depended on evidence that did not exist yet

TASK-40.13 now delivers the schema, validator, simulated pass/fail fixtures,
freshness rules, candidate-commit binding, and a gate that intentionally fails
while evidence is absent. The three client tasks later provide live evidence;
the early task does not pretend certification already passed.

### R-04 — Automatic updates lacked a safe execution boundary

The installer task now requires a per-client trigger, approved release
manifest/hash, last-check evidence, pin/offline controls, and either a safe
native update manager or deferred ADR Kit maintenance. Update checks and
activation may not run synchronously in any agent hook hot path.

### R-05 — Automatic doctor repair lacked an audit mode

The approved automatic repair behavior remains, but `--check` now provides the
same diagnosis without mutation for CI and read-only audits. Safe repairs,
`--fix` rewrites, and user-owned state are separate testable authority classes.

### R-06 — Best-effort and periodic were not measurable

macOS/Linux certification may explicitly record “not run” with a reason and
cannot promote those surfaces. OpenCode generic discovery now runs at least
quarterly and whenever generic discovery paths or packaging change.

### R-07 — Release evidence could be stale or irreproducible

Required Windows evidence is bound to the release-candidate commit and
supported client version. Interactive or login-dependent smoke may be
maintainer-run only with a recorded environment fingerprint and retained
redacted evidence.

### R-08 — Repurposed tasks retained misleading metadata

TASK-40.8 and TASK-40.9 no longer carry native Kimi/Kilo adapter labels or
modified-file claims. Their metadata now names generic artifacts and OpenCode
discovery only.

### R-09 — Deferred work remained executable in the board

TASK-40.10, TASK-40.11, TASK-40.12, and TASK-40.14 were archived with explicit
cancellation reasons. TASK-38 remains the research record, not an automatic
implementation queue.

### Audit conclusion

No unresolved planning blocker remains. The remaining risk is implementation
complexity, concentrated in transactional updates/rollback, bounded doctor
repair, and live three-client certification. Those risks now have explicit
owners, stop conditions, evidence requirements, and release consequences.

## Final scope correction

After reviewing the corrected graph, the maintainer narrowed current
implementation scope one step further:

- TASK-40 contains only Claude Code CLI, Codex CLI, and GitHub Copilot CLI.
- Generic portability is not a current TASK-40 product.
- OpenCode, Kilo, Kimi, IDE surfaces, and every other researched client are
  not current deliverables, tests, installer targets, doctor claims, release
  evidence, or documentation promises.
- Shared skills, prompts, instructions, guide content, MCP intent, and hooks
  remain in TASK-40 only when they directly serve the three selected clients.

The wider roadmap was not discarded. It moved to low-priority TASK-43,
`FUTURE EPIC: Expand ADR Kit beyond Claude, Codex, and Copilot`.

TASK-43 preserves TASK-38's candidate landscape and the possible generic
standards layer, but it has an explicit activation gate. When the maintainer
selects it in the future, it must first refresh official contracts, versions,
adoption, maintenance, OS/surface availability, licensing, and the available
maintenance budget. It then creates one bounded implementation and
certification task per approved client surface.

TASK-43 has no dependency relationship with TASK-40 and cannot delay or alter
the three-client release gate. TASK-40.8 and TASK-40.9 were archived and
transferred to TASK-43, joining the already archived TASK-40.10, TASK-40.11,
TASK-40.12, and TASK-40.14 as historical planning inputs.

## Fable v0.17.1 feedback disposition

Fable's review describes KennisBank v0.17.1, not defects proven in the current
ADR Kit implementation. KennisBank product behavior and memory workflows are
therefore not imported into TASK-40. The review does expose transferable
failure modes that should be prevented before ADR Kit's three-client work
starts.

### Measured ADR Kit baseline

The repository was measured before setting limits:

- `scripts/install-agent-envs.py`: 991 physical lines;
- `bin/adr-doctor`: 282 physical lines;
- 27 directly present files under `bin/`;
- 3 directly present files under `scripts/`; and
- no `requirements*.txt`, `pyproject.toml`, `setup.cfg`, `package.json`, or
  other runtime dependency manifest found.

These facts make two risks concrete. The installer is already a monolith that
must be decomposed, while the doctor is close enough to the entrypoint budget
that new client/model/repair behavior must move to support modules. The absence
of a runtime manifest establishes a zero-runtime-dependency baseline rather
than permission to add dependencies casually.

### Guardrails added

1. **Detected defaults, not a static client set.** Setup derives defaults from
   detected Claude, Codex, and Copilot installations plus effective settings.
   An absent client is never selected by a compiled `claude,codex` or
   all-client default.
2. **Complexity and executable budgets.** Public/build entrypoints target at
   most 300 physical lines, support modules target at most 400, and TASK-40
   adds at most four directly invoked entrypoints. Client/event behavior must
   remain data-driven. Exceptions need a recorded rationale, owner,
   responsibility analysis, focused tests, and approval.
3. **Dependency discipline.** The zero-runtime baseline remains unless a
   separate Proposed ADR justifies compatibility, security, license, update,
   exact-pin, expiry/review, and removal policy. Development and coverage tools
   cannot leak into runtime metadata or packages.
4. **Release consolidation.** A release candidate consolidates defaults, hook
   policy, schemas, and migrations. The normal limit is one stable release per
   calendar day. Emergencies require incident, version, rollback, changelog,
   and follow-up evidence. A shipped policy reversal requires a superseding
   Proposed ADR and new release candidate.
5. **Allowlisted public artifacts.** Packages are assembled from an explicit
   allowlist. Negative tests reject backlog data, `.superpowers`, VCS/CI
   internals, tests, caches, local state, secrets, and developer planning or
   review material.
6. **Explicit local-model health.** ADR Kit compiles no guessed provider/model
   fallback. Selection must be configured or unambiguous. Fast doctor uses
   configuration and cached reachability; deep doctor performs a bounded live
   probe. Missing, ambiguous, unreachable, or rejected models remain
   actionable degraded states, never silent successful judgment.
7. **Release-gated deterministic generation speed.** All TASK-40 generators
   use declared bounded inputs and an incremental input/output graph. The
   Windows reference targets are p50/p95 1/2 seconds for a clean full
   three-client build and 150/500 milliseconds for a warm unchanged run, with
   hard timeouts of 5 and 1 seconds. Unchanged outputs receive zero content
   rewrites. Evidence includes I/O, peak memory, and percentiles; an unapproved
   p95 regression above 20 percent blocks release. Profiling-led optimization
   may not weaken byte determinism, atomic writes, stale detection, or cache
   invalidation.

### Task ownership

The protections are now owned by the TASK-40 epic and by:

- TASK-40.1 for the architecture, dependency, complexity, release, and model
  policy;
- TASK-40.2 for canonical hooks, executable/dependency inventories, and the
  release allowlist, plus bounded incremental generation and its performance
  harness;
- TASK-40.4 for settings and model selection;
- TASK-40.5 for detected defaults and installer decomposition;
- TASK-40.6 for thin doctor structure and model-health reporting; and
- TASK-40.13 for executable, dependency, package, release-cadence, and
  all-three-client certification gates, including generator-performance
  evidence.

This resolves the transferable concerns at planning level. It does not claim
that implementation or release certification has begun.
