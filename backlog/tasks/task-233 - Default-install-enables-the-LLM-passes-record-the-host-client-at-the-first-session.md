---
id: TASK-233
title: >-
  Default install enables the LLM passes: record the host client at the first
  session
status: In Progress
assignee: []
created_date: '2026-10-11 19:42'
labels:
  - feature
  - llm
  - install
dependencies: []
priority: high
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Maintainer requirement (2026-10-06): a default install must enable all LLM features. Today judge.llm_enabled and suggest.enabled default to true, but the passes only run when judge.host_client is recorded, which happens only when install-agent-envs.py installs exactly one client or /adr-kit:init is answered 'on'. The common marketplace route (/plugin install) and multi-client installer runs record nothing, so the LLM passes silently do nothing. Chosen design (maintainer, over 'installer picks by order' and 'init only'): the SessionStart hook records the client the session runs in, once, into the gitignored docs/adr/.adr-kit.local.json, when docs/adr exists, no host client is recorded and the tracked config does not set judge.llm_enabled: false. It never overwrites an existing choice and fails open. The guardian's LLM tier keeps asking first (llm_autorun stays false, ADR-001). Needs a new ADR because ADR-036 says the client is recorded at install time. Also fix the guardian skill text that still names claude-sonnet-4-6.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Goal: on a clean install and on an upgrade the LLM layers are ON by default, run on the coding assistant the plugin is installed in, and the user confirms interactively (keep on, the default, or turn off). Guardian LLM tier stays ask-first (llm_autorun false, ADR-001).
<!-- SECTION:PLAN:END -->
