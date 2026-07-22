---
id: TASK-51
title: 'Installer: --clients all can leave Copilot half-installed'
status: To Do
assignee: []
created_date: '2026-07-22 22:04'
labels:
  - bug
  - installer
dependencies: []
priority: medium
ordinal: 52500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
During the 0.39.0 local publish, install-agent-envs.py --clients all registered the Copilot marketplace at 0.39.0 but did not install the plugin: copilot plugin list reported "No plugins installed" and the completion line listed only claude and codex. A targeted re-run with --clients copilot completed it and reported validation PASS. Same failure class as the Claude re-point defect fixed in TASK-48: the combined run reports partial success without leaving the client usable. Investigate why the copilot branch aborted in the combined run and make the outcome either complete or loudly failed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Root cause of the partial Copilot install in a combined --clients all run identified
- [ ] #2 A combined run either completes the Copilot install or fails loudly with the reason
- [ ] #3 Regression coverage for the partial-install path
<!-- AC:END -->
