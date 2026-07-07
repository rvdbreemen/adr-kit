# v0.32.0 - Local ADR Governance

This release consolidates the local governance workstreams after v0.31.0 and moves every update-sensitive artifact to version `0.32.0`: plugin manifest, marketplace manifest, guide stamp, wrapper stamps, changelog, tags, and GitHub Release notes.

## Highlights

- Added canonical ADR frontmatter with a stdlib parser, renderer, migration helper, and JSON Schema.
- Added `bin/adr-lint --strict` for schema validation, verified evidence resolution, reciprocal supersession checks, binding gate lookup, and CI-ready failure handling.
- Added `bin/adr` lifecycle commands: `propose`, `accept`, `supersede`, `reject`, and `document`.
- Added after-the-fact ADR acceptance: shipped behaviour can be documented with `verified_in` evidence and auto-accepted only after strict lint and quality checks pass.
- Added `bin/adr-doctor`, a local health check for agents and CI that combines strict lint, generated index freshness, staleness checks, evidence drift checks, missing-gate detection, and material-drift audit summaries.
- Consolidated `bin/adr-index` into two compatible modes: ADR-004 context index generation for `docs/adr/ADR-INDEX.md`, and local README index generation/checking for `docs/adr/README.md`.
- Updated agent-facing instructions so agents use generated indexes, strict lint, doctor checks, and Backlog.md instead of editing governance files by hand.

## Upgrade Notes

- Claude Code plugin updates compare `.claude-plugin/marketplace.json` `plugins[].version`; this release bumps that field to `0.32.0` together with `.claude-plugin/plugin.json`.
- Copied project artifacts are stamped as `0.32.0`. Existing projects may get a guardian stale-artifact nudge after the plugin update; run `/adr-kit:upgrade` to refresh the git wrapper, project settings entry, and `.claude/adr-kit-guide.md`.
- Regenerate both generated ADR indexes when adopting the new lifecycle tools:

```bash
bin/adr-index --adr-dir docs/adr -o docs/adr/ADR-INDEX.md
bin/adr-index docs/adr/
```

## Validation

- Full Python suite: `504 passed, 7 skipped`.
- Strict ADR lint: 4 ADRs pass, 0 failures.
- `bin/adr-doctor --fix-index docs/adr/ --format json`: clean.
- Generated context index and README index are fresh.
