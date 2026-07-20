---
id: TASK-40
title: 'EPIC: Certify Claude, Codex, and Copilot native support'
status: In Progress
assignee:
  - Codex
created_date: '2026-07-19 17:49'
updated_date: '2026-07-19 23:17'
labels:
  - epic
  - plugins
  - cross-client
  - installer
  - doctor
dependencies: []
references:
  - 'https://learn.chatgpt.com/docs/hooks'
  - 'https://developers.openai.com/learn/developers-codex-plugin'
  - 'https://code.claude.com/docs/en/plugins'
  - >-
    https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating
  - 'https://agents.md/'
  - 'https://skills.md/docs'
documentation:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/reviews/cross-client-plugin-planning-findings.md
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/adr/ADR-001-opt-in-llm-judge-for-commit-time-adr-enforcement.md
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
  - >-
    docs/adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md
modified_files:
  - .claude-plugin/
  - hooks/
  - codex/
  - copilot/
  - clients/
  - instructions/
  - skills/
  - prompts/
  - scripts/
  - bin/
  - schemas/
  - packaging/
  - tests/
  - docs/
  - README.md
  - INSTALL.md
  - .github/workflows/validate.yml
  - .github/workflows/release-candidate.yml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Deliver first-class native ADR Kit support for exactly Claude Code CLI, Codex CLI, and GitHub Copilot CLI. Windows native is the release baseline; macOS/Linux are best-effort. Keep one deterministic Python engine, preserve user-owned state, and provide shared skills, prompts, guidance, MCP, hooks, installation, doctor, and certification only where required by these three clients. Every ADR Kit release is blocked until all three pass their required certification. All additional client and generic support belongs to future TASK-43.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new Proposed ADR records the three-client ceiling, user-outcome parity policy, ownership model, settings hierarchy, update/repair boundaries, model-judgment defaults, latency method, and release gate without editing Accepted ADRs in place.
- [x] #2 Canonical skills, prompts/workflows, hook intents, MCP intent, and shared guidance serve Claude, Codex, and Copilot without independently edited semantic workflow copies; native manifests may remain schema-validated and hand-authored.
- [x] #3 Project setup detects and presents Claude, Codex, and Copilot, installs selected native support and pre-commit by default with explicit opt-outs, and preserves unrelated user state.
- [x] #4 Detection, install, update, rollback, disable, and uninstall converge idempotently, install verified stable updates automatically outside hook hot paths, and pause before breaking changes or migrations.
- [x] #5 Fast and deep doctor modes implement the approved safe-repair, --check, and --fix boundaries and diagnose the three clients in human and JSON output.
- [x] #6 Hooks meet the approved p50, p95, and hard-timeout budgets under a documented cold/warm benchmark method and fail open without model, network, install, index rebuild, or ADR mutation work.
- [ ] #7 Claude Code CLI, Codex CLI, and Copilot CLI preserve documented workflows and each has independent release-candidate-bound Windows native certification plus best-effort macOS/Linux status.
- [x] #8 Every ADR Kit release is blocked unless required Claude, Codex, and Copilot evidence passes; no future client participates in TASK-40 completion or release gating.
- [x] #9 Configured local-model judgment may default on in its documented workflow, while paid/cloud judgment remains explicit opt-in through global defaults with per-project overrides.
- [x] #10 Documentation, migration, rollback, settings, client-specific degradations, repair authority, and uninstall behavior match implemented evidence and describe only the three active clients.
- [x] #11 Public/build entrypoints remain orchestration-only and within the approved size/growth budget; the existing 991-line installer is decomposed and no client/event-specific script family is introduced.
- [x] #12 ADR Kit preserves the measured zero-runtime-dependency baseline unless a separate Proposed ADR approves a dependency with compatibility, security, license, update, and removal evidence; development tools never enter runtime installation.
- [x] #13 Stable releases use release-candidate evidence, consolidate policy/migration changes, and prohibit multiple same-day stable releases or policy reversals without a documented emergency exception.
- [x] #14 Every public archive/plugin is produced from an explicit allowlist and contains no backlog, internal agent workflow, test, cache, local-state, or developer-only content.
- [x] #15 Local judgment never guesses a provider model tag; unavailable or ambiguous models are reported as actionable degraded/skipped state rather than silently producing no judgment.
- [x] #16 Every TASK-40 deterministic generator meets the approved Windows-native clean/full and warm/no-op budgets, performs zero content rewrites for unchanged outputs, avoids unbounded repository scans, and blocks release on a material performance regression without weakening byte determinism or atomic writes.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Execute only the three-client graph in docs/plans/cross-client-plugin-implementation-plan.md. TASK-40.1 defines policy. TASK-40.4 delivers guide/settings, then TASK-40.2 canonical artifacts for Claude/Codex/Copilot. TASK-40.13 establishes the evidence schema and all-three blocking release gate. TASK-40.5 delivers detected-client setup/update/rollback, TASK-40.6 the doctor framework and repair boundaries, and TASK-40.3 hooks, latency, and deep-doctor hook probes. TASK-40.7 coordinates independent TASK-40.7.1/.2/.3 normalization and certification. TASK-40.8/.9 are archived. TASK-43 owns every wider or generic support plan and is not a dependency. Keep TASK-40 To Do until implementation begins.

Treat generator performance as a product contract: TASK-40.1 fixes the measurement and regression policy, TASK-40.2 implements bounded incremental generation and benchmarks, and TASK-40.13 gates release-candidate evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-07-19 planning established independent Windows-first certification for Claude Code CLI, Codex CLI, and Copilot CLI; fixed doctor/hook ownership, certification-parent dependencies, release-evidence bootstrapping, update hot-path behavior, doctor audit mode, and evidence freshness. A final maintainer scope correction removed generic and additional-client work from TASK-40. TASK-43 now preserves all wider support as a separate low-priority future epic with explicit activation and revalidation.

Implementation started with TASK-40.1 after explicit goal authorization. Work follows the recorded dependency graph; current focus is the Proposed architecture ADR and minimal capability schema.

Implementation and working-tree certification are complete for the three-client scope. Final regression after atomic-write hardening: 740 passed, 6 skipped; adapter drift clean; Claude manifest validation passed; prepared payload SHA-256 e96edb9a307df297d335713322c212b85b7d35c4e5f0814652f63f714632cc51. Remaining AC #7 is intentionally not checked: native records are independent Windows passes but are marked working_tree_clean=false/release_eligible=false. A maintainer-approved release-candidate commit is required before rerunning all three native certifications, promoting docs/client-support.md, accepting ADR-010, and completing TASK-40.7/TASK-40.

Implementation audit 2026-07-20: all shared foundations and all three native client subtasks are complete. Atomic deterministic generation passes at clean p50 880.576 ms / p95 1039.0 ms and warm p50 61.078 ms / p95 88.265 ms with zero rewrites; full suite is 740 passed, 6 skipped. Criterion #7 remains intentionally unchecked because release-candidate-bound native certification requires a clean commit and regenerated three-client evidence; current native evidence is correctly marked working_tree_clean=false and release_eligible=false.

Correction to the earlier implementation note: after the final same-directory atomic-write generator change, the authoritative prepared payload SHA-256 is 7c81f71393fcdf89641d633568e6df340270ea57e72f4f6d7c5d570c0a212635 (superseding e96edb9a...). Three local Rust PDB build artifacts are ignored and excluded from public payloads/releases; only the runtime executable is eligible.

Temporary-index release preflight (real index/branch untouched): candidate tree f9db9d6edf3ad8fbba4a77db40fad98452e6ccd9 contains 255 changed paths; git diff --check passed; root/Codex/Copilot hook launchers and existing pre-commit launchers are 100755; packaging contract passed 3 tests with 1 platform skip. EOF cleanup changed the authoritative prepared payload SHA-256 to 1bae71baf4b4b460064408235dd083e33fc5f2c2e6371095da82330b6b3dd7b9.

Adversarial release audit 2026-07-20 found and fixed three previously hidden blockers: native observation files could not be assembled into the release schema, release evidence was self-referential to the candidate checkout, and the generated native support matrix was incorrectly expected to exist inside that same candidate. `scripts/client_evidence.py` now assembles exactly three clean, commit-bound observations; the release workflow checks out a separately pinned evidence commit, validates it with candidate code, and emits the certified matrix/gate result as retained workflow artifacts. Focused release tests cover dirty, cross-commit, mixed-payload, mixed-policy, drift, path-escape, and separate-evidence-ref cases.

ADR-010 size-budget audit also found `scripts/client_generation.py` above its 400-line support-module target. It is now a 232-line orchestrator backed by 129/312/239-line model, artifact, and state modules; a regression test enforces <=300 lines for TASK-40 entrypoints and <=400 for support modules. Windows benchmark after decomposition: clean p50 713.408 ms / p95 735.485 ms; warm p50 34.965 ms / p95 60.974 ms; zero warm writes. Prepared payload SHA-256 is 6a7fc1bddcf64bd25b6b9e90d7a1d93aae180b2a0d9ae2fad6d658c0ef8e673a; prepared MCP initialize/tools-list and Claude SessionStart fail-open smoke passed.

Final regression after adversarial fixes: 746 passed, 6 skipped; generated adapter drift clean; `git diff --check`, strict ADR lint (10/10), and ADR index drift check pass. Deep doctor verified Codex/Copilot registration, all three MCP/hook packages, live MCP, and all measured hook budgets; it intentionally remains non-green because ADR-010 is still Proposed and Claude registration is trust-pending in the current user environment. AC #7 remains open until a maintainer-authorized candidate commit is created and all three native records are rerun clean against that exact commit.
<!-- SECTION:NOTES:END -->
