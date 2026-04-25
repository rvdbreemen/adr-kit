# adr-kit v0.8.0

Closes the post-mortem from the v0.7.1 and v0.7.2 install-side regressions with two layers of regression protection: schema validation in CI and a manual pre-release smoke test.

## Why this release exists

Both v0.7.1 (missing `marketplace.json`) and v0.7.2 (`repository` declared as object instead of string) were field-level mistakes in the plugin manifests that broke `/plugin install` for end users. The CI added in v0.5.0 caught JSON syntax errors and required-files presence but not field types or actual install behaviour. Both bugs would have been caught earlier with proper schema validation and a sanity check against the install path.

## What is new

### `schemas/plugin.json.schema.json`

Hand-curated JSON Schema (draft-07) for `.claude-plugin/plugin.json`. Validates:

- `name` is kebab-case lowercase and starts with a letter.
- `version` matches semver (`MAJOR.MINOR.PATCH` with optional pre-release suffix).
- `repository` is a plain URL string, not an npm-style `{ type, url }` object. (Regression test for the v0.7.2 bug.)
- `author` is an object with required `name`, optional `email` / `url`. Plain strings are rejected.
- `homepage` is a URI; `keywords` is an array of strings; `dependencies` is an array.

The schema's top-level `description` field documents which historical bugs each constraint prevents, so a future contributor cannot quietly weaken a constraint without understanding what it guards against.

### `schemas/marketplace.json.schema.json`

JSON Schema (draft-07) for `.claude-plugin/marketplace.json`. Required fields: `name`, `description`, `owner` (object with `name`), `plugins` (non-empty array). Each plugin entry requires `name`, `source`, `version`, `description`. The schema description references the v0.7.1 missing-manifest incident.

### CI integration (`.github/workflows/validate.yml`)

Two new steps run `ajv-cli` (draft-07, with `ajv-formats` for URI / email validation) against both manifests on every push and pull request. The workflow now fails the build on schema violations, not just on JSON syntax errors.

Required-files set extended:

- `.claude-plugin/marketplace.json` (was added in v0.7.1, now CI-enforced).
- `schemas/plugin.json.schema.json` and `schemas/marketplace.json.schema.json` (so a future contributor cannot accidentally remove the schemas without CI noticing).
- `skills/lint/SKILL.md` (added in v0.7.0 but never added to the required-files set; cleanup).

### Pre-release smoke test (`CONTRIBUTING.md`)

A 5-step manual checklist that release authors run in a fresh Claude Code session before tagging:

1. `claude --plugin-dir /path/to/your/adr-kit`
2. `/plugin` and confirm `adr-kit` appears in the Installed tab without validation errors.
3. `/help` and confirm `/adr-kit:adr`, `/adr-kit:setup`, `/adr-kit:lint` are listed.
4. Run `/adr-kit:setup` against a scratch project; verify the `ADR Kit Rules` section is appended and that re-running reports `Already set up.` (idempotency check).
5. Run `/adr-kit:lint` on a directory with at least one sample ADR; verify gate-by-gate output.

Schema validation catches manifest field-type bugs but cannot exercise the actual install path. The smoke test does. Both bugs from v0.7.1 and v0.7.2 would have been caught by step 2 of this checklist.

## Local sanity check

The schemas were validated locally before tagging using Python `jsonschema`. The current manifests pass. All six known-bad shapes (repository as object, author as string, missing version, non-semver version, missing plugins array, empty plugins array) are correctly rejected.

## Other changes

- `.claude-plugin/marketplace.json` plugin entry version corrected from 0.7.1 to 0.8.0. The v0.7.1 to v0.7.2 release silently left the marketplace manifest pointing at 0.7.1 while the plugin manifest advanced to 0.7.2. The new schema would also catch this kind of drift in future via the version-consistency CI step (currently only checks plugin.json against CHANGELOG; future improvement: also check marketplace.json plugin entry).

## Out of scope

- Automated install-smoke-test in CI: would require a Claude Code instance in the runner, which is not currently feasible.
- Schema for hooks / skills / agents frontmatter: those are markdown, not JSON; markdownlint already covers basic structure.
- Schema validation against an official Claude Code plugin manifest spec: when (if) Anthropic publishes one, this hand-curated pair will be replaced. Until then the pair is best-effort regression protection for bugs we have actually shipped.

## Install / upgrade

Existing installations:

```
/plugin marketplace remove rvdbreemen-adr-kit
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
```

Fresh installations: same four lines as above. See `INSTALL.md` for non-Claude-Code tools.

## Refs

- Backlog task: TASK-419 (post-mortem from v0.7.1 / v0.7.2 install regressions).
- Related: future v0.9.0 (TASK-420) will introduce scoped lint with grandfathering.
