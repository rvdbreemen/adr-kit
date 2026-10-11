---
id: TASK-224
title: >-
  Certify each native client on every platform it runs on, and refresh the
  0.36.0 evidence
status: In Progress
assignee: []
created_date: '2026-10-11 16:07'
labels: []
dependencies:
  - TASK-223
references:
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
  - scripts/client_certification.py
  - scripts/client_evidence.py
  - tests/certification
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The certification evidence in tests/certification is from ADR Kit 0.36.0: it is dated 2026-07-19 and covers Claude Code 2.1.215, Codex 0.144.6 and Copilot 1.0.71 on Windows only. It was captured on a dirty tree and is not release eligible. ADR-010 makes Windows the only certifiable platform. The validator (scripts/client_certification.py:69) and the assembler (scripts/client_evidence.py:20-24, :194) enforce that, and tests/test_native_client_packages.py:51-53 and docs/clients/*.md pin the client versions. Certification has been optional since 0.36.0 (docs/RELEASING.md step 5), although ADR-010 says a failing Windows record blocks every stable release. On 2026-10-11 the maintainer decided three things. A new ADR lets every platform count. What can be measured without a model is recorded now, and the model-dependent outcomes stay not-run until a session with credentials. The newest stable npm versions are certified, and tests read the versions from the evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ADR-048 amends ADR-010 and is accepted by the maintainer
- [ ] #2 The validator, assembler and support matrix accept native evidence per platform (Windows, macOS, Linux), and a record certifies only the platform it ran on
- [ ] #3 No test or document hard-codes a client version that the evidence records; each reads it from the evidence
- [ ] #4 Linux native observations for Claude Code, Codex and Copilot at the newest stable versions record every model-free outcome and mark model-dependent outcomes not-run with a reason
- [ ] #5 A runbook states what a session with credentials must run to complete the records
- [ ] #6 The full suite passes
<!-- AC:END -->
