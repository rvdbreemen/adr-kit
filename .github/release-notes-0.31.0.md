# v0.31.0 - Layered ADR Context Injection

This release makes ADR context active before and during agent edits.

## Highlights

- Added ADR-004 and the layered context injection model: session index, pre-edit injection, post-edit nudge, and commit-time enforcement.
- Added `bin/adr-index --adr-dir docs/adr -o docs/adr/ADR-INDEX.md`, a deterministic compact ADR map that can be imported from `CLAUDE.md`.
- Added the `PreToolUse` edit-tier hook through `.claude-plugin/plugin.json`, backed by `bin/adr-watch --pre-edit`.
- Added enforcement floor coverage buckets to `bin/adr-status`.
- Added CI freshness checking for `docs/adr/ADR-INDEX.md`.
- Extended `bin/adr-lint` to flag one-directional supersession drift.

## Upgrade Notes

- Existing plugin installs should update through the normal Claude Code plugin flow.
- Projects using copied artifacts may see stale guide or hook stamps after the plugin updates; run `/adr-kit:upgrade` to refresh them.
- Regenerate the compact context index with:

```bash
bin/adr-index --adr-dir docs/adr -o docs/adr/ADR-INDEX.md
```
