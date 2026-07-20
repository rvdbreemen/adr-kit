# ADR Kit Copilot CLI plugin

This is the self-contained plugin for the standalone GitHub Copilot CLI. It
uses Copilot's root `plugin.json` contract and does not change the Claude Code
or Codex manifests.

Skills, lower-camel cross-platform hooks, schemas, templates, and shared
instructions are deterministic outputs of:

```bash
python scripts/build-client-adapters.py
python scripts/build-client-adapters.py --check
```

The legacy `sync-agent-plugins.py` name remains a compatibility alias.
Discover workflows through `/skills`. This package does not claim Claude
namespaced commands, Codex `$skill` syntax, or a separate prompt surface.
