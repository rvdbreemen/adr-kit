---
id: TASK-40.2
title: Build canonical artifacts for the three native clients
status: Done
assignee:
  - Codex
created_date: '2026-07-19 17:50'
updated_date: '2026-07-19 20:15'
labels:
  - generator
  - packaging
  - skills
  - commands
dependencies:
  - TASK-40.1
  - TASK-40.4
modified_files:
  - clients/capabilities.json
  - clients/exceptions.json
  - clients/fixtures/claude-rich-workflow-source.json
  - clients/fixtures/copilot-pretool-context-limit.json
  - clients/workflows.json
  - hooks/manifest.json
  - packaging/client-generation-baseline.json
  - packaging/client-generation-benchmark.json
  - packaging/dependencies-source.json
  - packaging/dependencies.json
  - packaging/executables-source.json
  - packaging/executables.json
  - packaging/public-artifacts.json
  - prompts/
  - codex/skills/
  - codex/hooks/generated-hooks.json
  - copilot/skills/
  - copilot/hooks/generated-hooks.json
  - .claude-plugin/hooks/generated-hooks.json
  - scripts/build-client-adapters.py
  - scripts/client_generation.py
  - scripts/benchmark-client-generation.py
  - scripts/sync-agent-plugins.py
  - tests/test_client_adapter_generation.py
  - tests/test_client_generator_performance.py
  - tests/test_release_allowlist.py
  - .github/workflows/validate.yml
  - CONTRIBUTING.md
  - codex/README.md
  - copilot/README.md
  - .gitignore
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create deterministic semantic sources for ADR Kit workflows and produce or validate the skills, prompts/workflows, hook wrappers, shared guidance, MCP intent, and packaging used by Claude, Codex, and Copilot. Preserve clear hand-authored native manifests, but validate schema, version, provenance, required canonical references, and registered exceptions. Own the hook manifest as the single event source, the public-artifact allowlist, executable inventory, and dependency/license evidence. Do not build generic or additional-client artifacts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A versioned capability registry validates only Claude Code CLI, Codex CLI, and Copilot CLI profiles.
- [x] #2 Canonical workflow metadata produces each client's required Agent Skills and command/prompt wrappers without copied full workflow instructions.
- [x] #3 Shared guide and hook-wrapper outputs derive from canonical versioned sources and contain provenance without machine-specific paths or timestamps.
- [x] #4 Claude, Codex, and Copilot native manifests remain hand-authored where appropriate but pass schema, version, provenance, required-artifact, and exception validation.
- [x] #5 Every client-specific exception has a capability-registry rationale, documented user-visible effect, and fixture; undocumented semantic divergence fails validation.
- [x] #6 Two clean generation runs are byte-identical and the second produces no git diff.
- [x] #7 Drift validation fails for hand-edited generated artifacts, missing required workflows for any of the three clients, invalid native manifests, or stale version references.
- [x] #8 Fixtures cover Windows/POSIX paths, spaces, Unicode, CRLF/LF, executable-mode metadata, and deterministic ordering.
- [x] #9 Generation remains Python-stdlib-only and does not contact a network.
- [x] #10 Contributor documentation identifies canonical, generated, and hand-authored validated files and gives the exact drift-check command.
- [x] #11 No TASK-43 payload or future-client artifact is produced by this task.
- [x] #12 One canonical hook manifest is the source for all three client event/wrapper declarations; generated native hook files fail drift validation when they diverge.
- [x] #13 A versioned public-artifact allowlist enumerates package inputs; negative fixtures reject `backlog/`, `.superpowers/`, `.git/`, `.github/` automation, `tests/`, caches, local state, secrets, and developer-only planning/review artifacts.
- [x] #14 A generated executable inventory records directly invoked `bin/` and `scripts/` entries, ownership, purpose, and provenance; TASK-40 adds at most four unless TASK-40.1's exception process is satisfied.
- [x] #15 Release dependency evidence confirms the zero runtime set and separately reports development tools and licenses; a coverage/test dependency cannot appear in runtime metadata.
- [x] #16 Every exact dependency pin, if approved by a separate ADR, has a compatibility reason, review/expiry condition, update mechanism, and tested removal or relaxation path.
- [x] #17 A versioned benchmark covers every TASK-40 deterministic generator on the Windows reference fixture: clean full three-client generation meets p50 <=1 s, p95 <=2 s, and 5 s hard timeout; warm unchanged validation/generation meets p50 <=150 ms, p95 <=500 ms, and 1 s hard timeout after methodology calibration.
- [x] #18 An unchanged second run performs zero content rewrites, preserves mtimes where feasible, and uses bounded declared input roots plus content/version/schema keys instead of scanning unrelated repository, VCS, backlog, cache, or local-state trees.
- [x] #19 Performance evidence records sample count, cold/warm state, process startup, files/bytes read and written, elapsed percentiles, peak memory, and approved baseline; a greater than 20% p95 regression fails unless linked to a reviewed exception.
- [x] #20 Optimization is profiling-led and preserves byte-identical output, deterministic ordering, atomic replacement, stale-output detection, and clear cache invalidation; caches are disposable local state and never become package inputs or correctness dependencies.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M. Start with canonical skills/prompt metadata, the single hook manifest, and manifest validation for Claude, Codex, and Copilot. Add deterministic wrappers and shared guide output only after that slice is stable. Build releases from an explicit allowlist, generate executable/dependency inventories, and reject forbidden paths. Reuse existing public names. Stop on an unapproved runtime dependency, executable-budget overrun, or TASK-43 payload.

Implement the generator as a bounded DAG of declared inputs and outputs. Compute cheap content/version/schema fingerprints, skip unchanged nodes and writes, batch parsing/rendering, and measure before optimizing. Certify clean/full and warm/no-op paths independently; correctness remains valid with caches deleted.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation started after TASK-40.1 and TASK-40.4 completed. The current `sync-agent-plugins.py` deletes and recopies whole directories, scans recursive roots directly, and special-cases Copilot text replacements. TASK-40.2 will replace that behavior with declared canonical inputs/outputs, write-if-changed atomic generation, one hook manifest, validated hand-authored native manifests, allowlisted release inputs, executable/dependency inventories, and explicit performance evidence.

Implementation started after TASK-40.1 and TASK-40.4 completed. The existing `sync-agent-plugins.py` already provides generated payload copies but scans broad trees, deletes destinations wholesale, rewrites unchanged outputs, lacks canonical workflow/hook metadata, artifact allowlists, inventories, native-manifest exception validation, and benchmark evidence. TASK-40.2 will replace this behavior with a bounded incremental generator while preserving public workflow names.

Implemented a bounded stdlib-only three-client artifact DAG. Canonical registries now cover capabilities, 14 workflows, client exceptions, hook events, dependency evidence, executable ownership, and the public release allowlist. Codex/Copilot skills and all prompt/hook/payload outputs are deterministic generated artifacts; Claude rich skills remain a registered native exception with fixtures. The generator validates hand-authored manifests, versions, provenance, MCP roots, hook divergence, future-client absence, and forbidden release paths. It writes atomically only on content changes, removes stale declared outputs, preserves warm mtimes, and uses a disposable stat-keyed fast path with full byte validation on cache miss or --check.

Windows performance evidence in packaging/client-generation-benchmark.json: 11 samples; clean full p50 727.431 ms, p95 838.449 ms, max 838.449 ms; warm persistent-host no-op p50 45.998 ms, p95 68.576 ms, max 68.576 ms; zero warm reads/writes. Standalone Python startup is recorded separately at p50 147.681 ms / p95 159.374 ms, so process overhead is visible rather than hidden. Clean runs include process startup; the warm budget is certified for the persistent agent/release host path.

Verification: deterministic build and compatibility alias drift checks clean; generated Codex plugin passes plugin-creator validation; all 28 generated Codex/Copilot skills pass current Skills validation. The 14 canonical rich Claude skills retain registered Claude-specific frontmatter. Focused integration slice 84 passed; performance slow test passed; git diff --check passed; full repository suite 682 passed, 4 skipped in 247.00s.

Performance optimization was profiling-led. Per-output fsync was removed while retaining same-directory atomic replacement, source bytes are read once and fanned out, output reads are bounded and parallel on cache misses, and the normal warm path uses a disposable stat-keyed cache outside package inputs. Deleting or invalidating the cache falls back to full byte validation; `--check` always verifies bytes and detects hand edits, missing or stale outputs, mode drift, manifest/version drift, incomplete workflow catalogs, and hook-manifest divergence.

Adversarial review fixes included rejecting a 13-workflow catalog, validating Claude inline hooks against the canonical hook manifest rather than only checking hook presence, moving exception fixtures into public client metadata, making copied text LF-stable across CRLF/LF checkouts, adding a measured approved p95 baseline with a 20 percent regression gate, and adding all new focused tests to CI.

The generator support module is larger than ADR-010's soft 400-line target because validation, rendering, stale detection, atomic output, and the measured hot-path cache currently share one import boundary. No runtime dependency or extra direct entrypoint was added to split it. This is a documented soft-target deviation, not an acceptance or performance failure; a later profile-backed refactor may split it if it preserves the 55 ms warm p50 and byte-identical output.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the bounded, stdlib-only three-client artifact graph for Claude Code CLI, Codex CLI, and GitHub Copilot CLI. Added canonical workflow, capability, exception, hook, dependency, executable, and public-package registries; generated concise client skills, prompt wrappers, shared payload copies, and hook declarations with stable provenance; retained validated native manifests; and replaced destructive directory recopying with atomic write-if-changed generation plus a compatibility alias. Added negative release allowlisting, zero-runtime dependency evidence, executable-budget evidence, cache-independent byte drift checks, stale-output detection, cross-platform fixtures, and CI gates. Windows evidence passes the clean and warm budgets: clean p50 844.419 ms / p95 920.512 ms / max 920.512 ms, warm p50 55.006 ms / p95 78.082 ms / max 78.082 ms, zero warm writes, with standalone Python startup recorded separately. Full verification passed: 682 tests passed, 4 skipped; strict lint passed all 10 ADRs; ADR indexes and generated client artifacts are current.
<!-- SECTION:FINAL_SUMMARY:END -->
