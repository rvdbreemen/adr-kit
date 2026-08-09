---
id: TASK-158
title: Purge the retired judge backends from the init and judge skills
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 15:24'
updated_date: '2026-08-09 15:33'
labels:
  - bug
  - skill
  - adr-036
dependencies: []
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PR #83 (ADR-036) reduced the judge to the host backend plus the operator escape hatch, but skills/init/SKILL.md still offers a four-backend choice and issues --set-backend openrouter/ollama/openai-compatible commands with flags argparse now refuses (BACKEND_NAMES is host-only, --model/--base-url deleted): the guided init flow breaks mid-setup with exit 2. skills/judge/SKILL.md likewise documents --set-backend openrouter --model plus OPENROUTER_API_KEY guidance for code paths that no longer exist. Both mirror into the generated codex/ and copilot/ skills. Review finding NF1+NF2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 init skill offers host (with client choice) and off only, and every command it issues is accepted by the current adr-judge
- [x] #2 judge skill's settings step matches ADR-036: host plus ADR_KIT_LLM_CMD escape hatch, no retired backends or env vars
- [x] #3 Adapters regenerated, --check clean
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
init skill's backend step rewritten to ADR-036 reality: the notice explains host-only plus the ADR_KIT_LLM_CMD operator escape hatch, the question is now 'LLM pass? [1] on (host CLI) [2] off', every issued command is accepted by current adr-judge, and the wrap-up line reads backend <host|off>. judge skill's settings step likewise: one --set-backend host example, rules name what was retired and why the escape hatch is environment-only (ADR-025). The single remaining openrouter/ollama mention in each file is the sentence explaining their retirement. Adapters regenerated, --check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
