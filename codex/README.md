# ADR Kit Codex plugin

This directory is the self-contained Codex distribution. It deliberately has
its own manifest and skills; Claude Code continues to use the repository-root
`.claude-plugin/` manifest and `skills/`.

Skills, native hooks, `bin/`, schemas, templates, and shared
instructions derive from the versioned canonical registries and roots through:

```bash
python scripts/build-client-adapters.py
python scripts/build-client-adapters.py --check
```

The legacy `sync-agent-plugins.py` name remains an alias. CI verifies byte
drift, manifest versions, the three-client scope, and generator performance.

Use `/skills` or an explicit `$adr-kit:<workflow>` mention. Local custom prompts
are deprecated and are not advertised as a plugin-distributed command surface.
