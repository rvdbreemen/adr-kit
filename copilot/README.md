# ADR Kit Copilot CLI plugin

This is the self-contained plugin for the standalone GitHub Copilot CLI. It
uses Copilot's root `plugin.json` contract and does not change the Claude Code
or Codex manifests.

The deterministic payload is generated from the repository's canonical
directories by `python scripts/sync-agent-plugins.py`.
