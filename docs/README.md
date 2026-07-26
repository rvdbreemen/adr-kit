# ADR Kit documentation

Every guide in this repository, grouped by what you are trying to do. The
[root README](../README.md) is the product overview; this page is the map.

## If you are a coding agent

Read only what your current job requires. These four cover almost everything.

| Job | Read | Contract in one line |
| --- | --- | --- |
| Install ADR Kit into a machine or project | [INSTALL-AGENT.md](../INSTALL-AGENT.md) | The complete client-neutral runbook: detect, preview, install, initialize, verify. Do not read other docs first. |
| Find the decisions that govern a task | [selective-context.md](selective-context.md) | `python bin/adr-context --format json "<task>"` queries the generated index; open only the returned Markdown ADRs. |
| Choose or migrate an ADR format | [format-migration.md](format-migration.md) | `python bin/adr profiles --format json` is the only source of valid profile ids. Detection is read-only and never migrates. |
| Complete or reconstruct a decision | [adr-grilling.md](adr-grilling.md) | One evidence-backed human question at a time. Source material is evidence; it is never acceptance authority. |

Three invariants hold across all of them:

1. **Markdown ADRs are the authority.** `ADR-INDEX.json` and `ADR-INDEX.md` are
   generated lookups. Query them, never hand-edit them, and regenerate with
   `python bin/adr-index docs/adr`.
2. **Accepted governs, Proposed advises, historical is opt-in.** An injected
   `[adr-inject]` block naming an Accepted ADR is a binding constraint on that
   edit, not background reading.
3. **Nothing mutates without a human.** Every file-writing workflow is
   confirmation-gated. The guardian drafts; it does not apply. No default path
   needs an API key.

## If you are a human

### Getting started

- [Root README](../README.md): what ADR Kit is, the lifecycle, slash commands,
  configuration, CI integration, FAQ.
- [INSTALL.md](../INSTALL.md): per-tool manual install paths, portable Agent
  Skills, and MCP client setup.
- [MIGRATING-FROM-ADR-SKILL.md](../MIGRATING-FROM-ADR-SKILL.md): switching
  from the original adr-skill.
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md): when a hook, client, or MCP
  server misbehaves.

### Using it day to day

- [selective-context.md](selective-context.md): the index-first retrieval
  contract, covering query inputs, ranking signals, probes, strict mode, and
  the visible Markdown fallback.
- [adr-grilling.md](adr-grilling.md): authoring, reconstruction, resume,
  queue, acceptance, and CI examples for the guided decision interview.
- [format-migration.md](format-migration.md): detecting existing ADR formats
  and converting between MADR, Nygard, and canonical without losing metadata.
- [client-support.md](client-support.md): *generated* per-client, per-OS
  support matrix. It separates native certification from simulated contract
  coverage, and states which lifecycle events each client actually supports.
- [clients/claude.md](clients/claude.md), [clients/codex.md](clients/codex.md),
  [clients/copilot.md](clients/copilot.md): per-client package layout, setup,
  and recovery steps.

### Decisions and direction

- [adr/](adr/): this repository's own ADRs. We eat the dog food.
  - [adr/ADR-INDEX.md](adr/ADR-INDEX.md): compact one-row-per-ADR session map.
  - [adr/ADR-INDEX.json](adr/ADR-INDEX.json): schema-v2 agent metadata and
    relationship graph. Both are generated; do not edit either by hand.
- [../ROADMAP.md](../ROADMAP.md): direction, v1.0.0 criteria, deliberate
  non-goals.
- [../CHANGELOG.md](../CHANGELOG.md): full release history.

### Contributing and releasing

- [../CONTRIBUTING.md](../CONTRIBUTING.md): dev loop, adding a workflow, code
  style, and verification expectations.
- [RELEASING.md](RELEASING.md): the authoritative three-marketplace release
  runbook, including the version registry, the consistency gate, and the
  `main` → `dev` merge-back step.
- [hook-performance.md](hook-performance.md): the hook latency certification
  method and its budgets.
- [../SECURITY.md](../SECURITY.md): reporting policy and the security posture
  of the opt-in LLM passes.

## Background and evidence

Design dossiers, research, and audit records. Useful when you want to know
*why* something works the way it does; not required to use ADR Kit.

- [research/adr-format-evaluation.md](research/adr-format-evaluation.md): the
  weighted evaluation behind MADR as the default.
- [research/2026-06-12-adr-landscape.md](research/2026-06-12-adr-landscape.md):
  the ADR tooling landscape that shaped the roadmap.
- [research/cross-client-plugin-hooks-report.md](research/cross-client-plugin-hooks-report.md)
  and [plans/cross-client-plugin-implementation-plan.md](plans/cross-client-plugin-implementation-plan.md):
  the multi-client hook and packaging investigation.
- [feature-adr-grilling/](feature-adr-grilling/): the full grilling dossier
  (research, lifecycle analysis, solution design, implementation and validation
  plans, benchmark report, and final certification).
- [reviews/2026-07-18-source-audit/FINDINGS.md](reviews/2026-07-18-source-audit/FINDINGS.md):
  the multi-perspective source audit that drove fail-closed enforcement and
  transaction-safe lifecycle updates.
- [superpowers/specs/](superpowers/specs/): earlier design specs for the
  guardian and agent injection layers.

## Generated files: do not hand-edit

| File | Generated by |
| --- | --- |
| `docs/adr/ADR-INDEX.md`, `docs/adr/ADR-INDEX.json`, the sentinel block in `docs/adr/README.md` | `bin/adr-index docs/adr` |
| `docs/client-support.md` | client certification evidence |
| `codex/`, `copilot/`, `prompts/` payloads | `scripts/build-client-adapters.py` |
| Version strings across manifests, templates, and README pins | `scripts/bump-version.py X.Y.Z` |

Each has a `--check` or drift gate that fails CI when the generated view no
longer matches its source. Edit the source, then regenerate.
