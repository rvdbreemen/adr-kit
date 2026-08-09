---
id: TASK-32.6
title: Close residual audit portability CI and metadata gaps
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 20:54'
labels:
  - portability
  - ci
  - documentation
  - packaging
  - audit
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
modified_files:
  - .gitattributes
  - .claude-plugin/hooks/run-hook.cmd
  - .github/workflows/validate.yml
  - scripts/install-agent-envs.py
  - tests/test_packaging_contract.py
  - tests/test_agent_installer.py
  - tests/test_documentation_contracts.py
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - ROADMAP.md
  - CHANGELOG.md
  - .claude-plugin/plugin.json
  - skills/supersede/SKILL.md
  - codex/skills/supersede/SKILL.md
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
  - codex/
  - copilot/
parent_task_id: TASK-32
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resolve or explicitly close residual source-audit F-06, F-14, F-19, and F-20; verify F-07, F-11, F-12, F-13, F-17, and F-18 remain fixed; synchronize documentation and generated artifacts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every directly executed release entry point records or restores executable Unix mode and packaging tests cover manual and automatic paths.
- [x] #2 Installer failures remain isolated and validation exercises real packaged runtime contracts.
- [x] #3 CI covers the supported Python/OS matrix, public examples, and all generated index/document surfaces.
- [x] #4 Public metadata, changelog links, README, install guidance, roadmap, security claims, report statuses, and generated payloads are synchronized.
- [x] #5 Regression checks confirm previously resolved findings remain fixed.
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed F-06, F-14, F-19, and F-20 and reverified the previously fixed portability/documentation findings. Every direct root and packaged entry point is mode 100755, Git archives preserve manual-install modes, the automatic installer restores them, and Windows/macOS/Linux CI exercises packaging. Prepared-source validation now runs real MCP initialize/tools-list plus the Claude SessionStart wrapper; client failures stay isolated and recover through idempotent reruns. The Windows smoke uncovered and fixed a Unicode character that broke cmd parsing. CI now checks public JSON examples and all three generated index surfaces. README, agent/human install guides, roadmap, changelog links and release helper, public metadata, supersession guidance, audit report, and generated Codex/Copilot payloads are synchronized. Verification includes full suite 635 passed/4 skipped, OTGW corpus 5 passed, strict lint 7 clean, payload and all index checks current, judge zero violations/advisories, and git diff check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
