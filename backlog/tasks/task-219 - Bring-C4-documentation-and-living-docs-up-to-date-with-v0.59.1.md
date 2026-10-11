---
id: TASK-219
title: Bring C4 documentation and living docs up to date with v0.59.1
status: Done
assignee: []
created_date: '2026-10-06 10:36'
updated_date: '2026-10-06 13:06'
labels:
  - docs
  - c4
dependencies: []
priority: medium
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
C4-Documentation/ was last revised at v0.52.0 (2026-08-18). Since then: the native adr-hook binary and its Rust sources were retired in 0.55.1 (ADR-029), yet C4 still mentions adr-hook 51 times across 8 files; the MCP server grew to seven read-only tools (0.53.0, ADR-040) while C4 says five in 8 places; automatic Proposed-ADR handoff to grilling (0.54.0, ADR-041); the release driver scripts/release.py with tag-from-merge (0.56-0.57, ADR-042) and the install-smoke workflow; adr-substance in the guardian LLM tier, judge LLM pass ceilings and --check-scope (0.58.0); adr-retire scanning git ls-files (0.59.0); the portable pre-commit probe (0.59.1). Living docs with stale hits: README.md, docs/hook-performance.md, docs/clients/opencode.md, docs/clients/codex.md. Historical records (docs/feature-adr-grilling/, sweep-v0.44.1-handover.md, plans/, research/, reviews/, superpowers/) are dated and stay as they are.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A current-state fact sheet is built from primary sources (bin/, MCP tools/list, hook manifests, workflows, ADRs, config keys) before any C4 edit
- [x] #2 C4 revised top-down (context, container, component overview, then the seven component files); adr-hook appears only as one explicit historical mention per place where its retirement matters
- [x] #3 C4 names the seven MCP tools, the release driver and tag-from-merge flow, ADR-040/041/042, and the 0.58-0.59.1 engine changes where they belong
- [x] #4 Living docs corrected without changing RELEASING.md procedure or registry-written version pins; adapters regenerated with --check changed=0
- [x] #5 Case-sensitive greps for adr-hook, Rust, five-tool and sort -V leave only explicit historical mentions
- [x] #6 Full suite green before the PR
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fact sheet built from primary sources (bin/, live MCP tools/list, hooks/manifest.json, 13 workflows, ADRs, config keys). C4 revised top-down by sequential single-file passes (context+container, overview, then the seven components), each verifying claims against code and validating its Mermaid diagram (all valid). Besides ADR-029 (native host) the passes found a second retired layer still documented: ADR-036 (0.48.0) removed embeddings and the HTTP judge backends. Dozens of counts and file:line anchors re-verified; retired c4-code-*.md links turned into labels (TASK-149). Living docs: client docs (seven MCP tools, 17 skills, Python-only host), README (skill counts, host-CLI FAQ, What's new rows 0.53.0/0.57.0/0.58.0), docs/README.md (C4 and OpenCode links, RELEASING as the spec release.py implements, background docs marked as dated). The LLM-judge default conflict (README says opt-in; code runs it by default after a single-client install, TASK-169) is described factually in C4 and left in README for the maintainer to decide. Code drift found along the way is in TASK-220 (guardian sort -V) and TASK-221. Adapters --check changed=0. Full suite 1965 passed / 12 skipped (two foreground halves, 2026-10-06).

Third commit (maintainer decision): README describes the LLM passes as they behave (on by default where a host client is recorded, host CLI only, ceilings, VIOLATION blocks / unparseable degrades, how to switch off) and adds 'Working locally (opt-in)': no model at all, or a local model via ADR_KIT_LLM_CMD. Local path verified live with qwen3.5:4b through Ollama: 4/7 ADRs judged with --think=false (7 s warm), 2/7 with thinking on (349 s); unusable verdicts degraded as designed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
C4-Documentation brought from v0.52.0 to v0.59.1 (all 10 files, every Mermaid diagram validated, counts and anchors re-verified, two retired layers removed: native hook host ADR-029 and embeddings/HTTP backends ADR-036). Living docs corrected (client docs, README, docs index); README now describes the default-on LLM judge truthfully and documents opt-in local work via ADR_KIT_LLM_CMD, tested with a local Ollama model. Merged via PR #184 (66076a8) with 14/14 CI checks green and the full suite 1965 passed / 12 skipped locally. Follow-ups: TASK-220 (guardian sort -V), TASK-221 (12 code/config drift items).
<!-- SECTION:FINAL_SUMMARY:END -->
