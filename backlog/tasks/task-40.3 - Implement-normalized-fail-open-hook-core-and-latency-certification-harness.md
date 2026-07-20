---
id: TASK-40.3
title: Implement outcome-driven hooks and latency certification
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-19 17:50'
updated_date: '2026-07-19 21:47'
labels:
  - hooks
  - performance
  - fail-open
dependencies:
  - TASK-40.1
  - TASK-40.5
  - TASK-40.6
  - TASK-40.13
modified_files:
  - hooks/manifest.json
  - hooks/adr-hook.py
  - hooks/adr_hook_core.py
  - hooks/adapters/__init__.py
  - hooks/adapters/claude.py
  - hooks/adapters/codex.py
  - hooks/adapters/copilot.py
  - hooks/__init__.py
  - hooks/hook_benchmark.py
  - hooks/native/adr-hook.rs
  - hooks/native/windows-process-floor.rs
  - hooks/native/README.md
  - hooks/bin/windows-x64/adr-hook.exe
  - .claude-plugin/hooks/run-hook.cmd
  - .claude-plugin/plugin.json
  - clients/installer/payload.py
  - scripts/client_generation.py
  - bin/adr_doctor_probes.py
  - tests/fixtures/hooks/reference-corpus.json
  - tests/fixtures/hooks/windows-process-floor.json
  - tests/test_hook_protocol.py
  - tests/test_hook_performance.py
  - tests/test_client_adapter_generation.py
  - docs/hook-performance.md
  - packaging/client-generation-benchmark.json
  - codex/hooks/adr-hook.py
  - codex/hooks/adr_hook_core.py
  - codex/hooks/adapters/__init__.py
  - codex/hooks/adapters/claude.py
  - codex/hooks/adapters/codex.py
  - codex/hooks/adapters/copilot.py
  - codex/hooks/bin/windows-x64/adr-hook.exe
  - copilot/hooks/adr-hook.py
  - copilot/hooks/adr_hook_core.py
  - copilot/hooks/adapters/__init__.py
  - copilot/hooks/adapters/claude.py
  - copilot/hooks/adapters/codex.py
  - copilot/hooks/adapters/copilot.py
  - copilot/hooks/bin/windows-x64/adr-hook.exe
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement a client-neutral internal ADR Kit hook core used only by Claude Code CLI, Codex CLI, and Copilot CLI. Support lifecycle actions that serve the approved three-client outcome contract. SessionStart is cheap context/staleness orientation, prompt hooks rank relevant ADRs, edit hooks provide governing context or an honest backstop, SubagentStart propagates an existing bundle where native, and PreCompact preserves bounded ADR continuity only where native and useful. All optional hooks fail open and never invoke models or mutate ADRs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The normalized envelope contains only the client/version/event, session/agent identity, workspace, required tool data, and bounded parent context needed by ADR Kit.
- [x] #2 SessionStart uses local generated state and the cheap fail-open tier without index rebuild, model, network, installation, or ADR mutation.
- [x] #3 Prompt-tier ranking is deterministic, source-linked, bounded, and falls back to lexical references on timeout.
- [x] #4 Pre-edit behavior filters write tools, resolves paths safely, and returns governing Accepted ADR context only where the client can display it honestly; otherwise the documented task/post-edit/pre-commit backstop is used.
- [x] #5 Post-edit behavior is a bounded confirmation or dirty-state backstop; unrelated tools and duplicate events are successful no-ops.
- [x] #6 SubagentStart reuses the parent-selected ADR bundle where native and otherwise relies on project guidance; it performs no second expensive retrieval.
- [x] #7 PreCompact emits only bounded ADR continuity where native; Stop, SubagentStop, SessionEnd, permission, notification, interrupt, and unknown events are successful no-ops unless a documented ADR Kit outcome requires action.
- [x] #8 Malformed input, missing indexes/interpreters, internal exceptions, and timeouts map to each native client's fail-open response; pre-commit remains separate deterministic enforcement.
- [x] #9 The benchmark specification fixes reference corpus, machine class, sample count, cold/warm/cache state, process-startup inclusion, and permitted CI variance.
- [x] #10 Fixtures meet all approved p50/p95/hard-timeout targets and deep doctor reports the same measurement identifiers.
- [x] #11 Fixtures cover native naming/casing, tool aliases, spaces/Unicode paths, hostile or oversized JSON, duplicate events, disabled hooks, and unsupported events.
- [x] #12 Deep doctor invokes the completed hook fixtures and latency harness through TASK-40.6's versioned extension contract without making default doctor slow or login-dependent.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size L. Define the benchmark methodology and fail-open envelope first. Implement SessionStart plus pre/post edit for Claude, Codex, and Copilot as the earliest useful slice, then prompt ranking. Add SubagentStart and PreCompact only where an official event has a measurable ADR outcome. Do not add hook formats or adapters for TASK-43 clients.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting after TASK-40.6 completed with a versioned deep-probe extension contract. The approved implementation plan remains current: define the normalized fail-open protocol and benchmark method, implement only measurable ADR outcomes for the three clients, keep all optional hooks model/network/update/mutation-free, and wire latency evidence into deep doctor.

Implemented the normalized bounded read-only hook core, Claude/Codex/Copilot response adapters, six measurable lifecycle outcomes plus no-op terminal handling, deterministic lexical ranking/source links, safe write-path resolution, parent bundle reuse, compact continuity, hostile/oversized fail-open handling, a dependency-free Rust Windows hot-path host, and the versioned end-to-end benchmark wired into deep doctor. Protocol/performance/installer/doctor focused slice: 65 passed. Native host reduces the Python SessionStart path from about 200 ms to roughly 20-35 ms. Current honest deep-doctor evidence passes SessionStart, prompt, subagent, compact, stop, and every hard timeout, but the Windows process-creation floor keeps PreToolUse/PostToolUse p50 around 20 ms versus the approved 10 ms target; PostToolUse p95 can also exceed 25 ms under load. The harness includes startup and reports these misses without coercion. TASK-40.3 remains In Progress and release promotion remains blocked by AC #10 until the approved targets are met or explicitly revised. See docs/hook-performance.md.

Added cross-process duplicate-event suppression in OS temp (never project/ADR state), native/Python regression coverage, an embedded-Python fallback patched during payload preparation, and hash-equal Windows native hosts for canonical/Codex/Copilot payloads. Fixed generator source tracking so hook runtime changes invalidate the warm cache; the 11-sample generator benchmark remains within budget (clean p95 917.021 ms, warm p95 79.162 ms, zero warm writes). ACs 1-9 and 11-12 are now evidenced. AC 10 remains the only unverified criterion because the approved 10 ms edit p50 is below the measured Windows process-launch floor.

Second Windows-floor investigation: compiled a 3,072-byte Rust no_std/no-CRT process with no stdin parsing or ADR work and measured 300 end-to-end launches. Results: min 13.171 ms, p50 18.116 ms, p95 25.857 ms, p99 33.878 ms, max 144.603 ms. This proves the unchanged 10/25/100 edit-hook budget cannot be met by any command hook on this machine; the semantic native host is already close to the irreducible floor. Evidence is preserved in tests/fixtures/hooks/windows-process-floor.json. No budget or hook policy has been changed without user approval.

User decision on 2026-07-19: retain full Windows PreToolUse/PostToolUse automation and revise the certified edit-hook budget to p50 25 ms, p95 50 ms, hard timeout 100 ms. This replaces the physically unattainable 10/25/100 ms Windows target; macOS/Linux remain best-effort and must report measured results honestly.

Revised-budget certification completed on the Windows native runner. The 30-sample warm-filesystem run included process startup and passed every event and hard timeout. PreToolUse measured p50 22.358 ms, p95 28.275 ms, max 30.260 ms; PostToolUse measured p50 22.932 ms, p95 28.080 ms, max 29.787 ms; both had zero timeouts against 25/50/100 ms. Deep doctor reported `adr-kit-hook-latency-v1` and a healthy hook extension. Full regression: 735 passed, 4 skipped; generator check: changed=0/written=0; `git diff --check` clean apart from existing line-ending notices.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and certified ADR Kit's normalized, fail-open hook runtime for Claude Code CLI, Codex CLI, and GitHub Copilot CLI. The runtime provides bounded deterministic SessionStart, prompt recall, write-tool governance/backstop, parent context reuse, and pre-compaction continuity while terminal and unsupported events remain safe no-ops. Added the dependency-free native Windows host, portable Python fallback, client adapters, duplicate suppression, hostile-input/path-safety coverage, reproducible latency harness, deep-doctor extension, and performance documentation. Following the explicit policy decision, Windows PreToolUse/PostToolUse retain full automation under a 25 ms p50 / 50 ms p95 / 100 ms hard-timeout budget. Native 30-sample certification passed all targets with edit-hook p50/p95 below 23/29 ms and zero timeouts. Verification: 735 passed, 4 skipped; generated adapters deterministic and clean.
<!-- SECTION:FINAL_SUMMARY:END -->
