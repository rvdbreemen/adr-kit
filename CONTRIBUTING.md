# Contributing to adr-kit

Thanks for considering a contribution. `adr-kit` is intentionally small and project-agnostic; the bar for upstream changes is "this is generic and improves the toolkit for any user", not "this is what we needed for project X".

## Dev loop

Local plugin testing without publishing:

```bash
# In any test project, point Claude Code at your local clone:
claude --plugin-dir /path/to/your/adr-kit

# Then try the slash commands:
#   /adr-kit:setup
#   /adr-kit:adr
#   /agents     (should list adr-generator)
```

`--plugin-dir` makes edits in your clone visible immediately on `/reload-plugins`. No publish, no install.

For Codex and the standalone Copilot CLI:

```bash
python scripts/sync-agent-plugins.py
python scripts/sync-agent-plugins.py --check
python scripts/install-agent-envs.py --dry-run
```

Use a temporary `CODEX_HOME` or `COPILOT_HOME` for isolated install smoke tests.
Never point either client at the Claude plugin cache.

The payload check normalizes CRLF and LF before comparison. Run it after every
engine, schema, template, instruction, or Codex skill change.

## How to add a skill

1. Create `skills/<name>/SKILL.md` with frontmatter:
   - `name`: lowercase, hyphenated.
   - `description`: 1 to 2 sentences front-loading the trigger phrases.
   - Optional: `disable-model-invocation: true` if the skill mutates user files; the user must explicitly invoke it.
   - Optional: `allowed-tools` (e.g. `[Read, Write, Edit]`) to pre-approve tools so the user is not prompted on every use.
   - Optional: `argument-hint` to show expected slash-command syntax.
2. Body: clear, scannable instructions to the model. Sections, bullets, code examples.
3. Update `README.md` with a one-line mention of the new skill so users discover it.

## How to add an agent

1. Create `agents/<name>.md` with frontmatter:
   - `name`: lowercase, hyphenated.
   - `description`: when Claude should delegate to this agent (used for auto-delegation).
   - `tools`: whitelist. Restrict to the minimum the agent needs.
   - Optional: `model`, `effort` for cost or quality tuning.
2. Body: the agent's system prompt. Clear scope, refusal conditions, output format.
3. Document in `README.md` when to delegate to this agent vs running the task in the main session.

## Version bump and release

`adr-kit` follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR**: breaking change in skill names, manifest schema, or default conventions.
- **MINOR**: new feature, backwards-compatible.
- **PATCH**: bug fix, doc-only change, no behavioural change.

The current release helper accepts stable `X.Y.Z` versions only. Although
Semantic Versioning permits pre-release and build metadata, `bin/bump-version`
does not yet accept those forms.

Release steps:

1. Finish the notes under `## [Unreleased]` in `CHANGELOG.md`.
2. Run `python bin/bump-version X.Y.Z`. It stamps all client manifests,
   marketplaces, copied-artifact versions, and rolls `Unreleased` into the
   dated release section.
3. Run `python scripts/sync-agent-plugins.py`, then inspect `git status` and
   `git diff`. Stage every stamped/generated file, including the guide,
   pre-commit wrapper, and both marketplace manifests.
4. Run the validation commands below and complete the manual client smoke test.
5. Commit the changes (`chore(release): vX.Y.Z (...)`).
6. Tag with the repository's published convention:
   `git tag -a vX.Y.Z -m "..."`.
7. `git push` and `git push --tags`.
8. Create a GitHub Release on the new tag with notes summarised from the CHANGELOG.

## Code style

- **No em dashes.** Use colons, periods, commas, parentheses, semicolons. Project-wide style.
- **English** for all repo content (skill bodies, README, CHANGELOG, commit messages).
- **Kebab-case** for file names: `adr-generator.md`, not `ADRGenerator.md` or `adr_generator.md`.
- **Concise over comprehensive.** A short, accurate sentence beats a verbose paragraph.
- **Cite when adapting upstream patterns.** If you bring in a pattern from another project, credit them in `SKILL.md` and `README.md`.

## Validation

CI is enforced by `.github/workflows/validate.yml` on every push and pull request:

- `jq empty` on `plugin.json` and `marketplace.json` (syntax check).
- Schema validation (ajv-cli, draft-07): both manifests are validated against `schemas/plugin.json.schema.json` and `schemas/marketplace.json.schema.json` respectively. The schemas reject the field-type bugs that surfaced post-install in v0.7.1 and v0.7.2 (missing marketplace manifest; `repository` declared as object instead of string).
- The generated-payload and integration-test gate checks both `codex/` and
  `copilot/`. Codex currently has no `plugin validate` subcommand; verify with
  `codex plugin list --json`, `codex mcp list`, and a real `adr_context` call.
- Presence check on the required-files set.
- `plugin.json` version must match the top entry of `CHANGELOG.md`.
- `markdownlint` on skills, agents, instructions, and examples.

Run the local equivalent before opening a PR:

```bash
python scripts/sync-agent-plugins.py --check
python bin/adr-doctor
python bin/adr-index docs/adr/ --check
python bin/adr-index --adr-dir docs/adr -o docs/adr/ADR-INDEX.md --check
python -m pytest
```

PRs that break CI will not be merged.

### OTGW migration corpus

`tests/testsets/otgw-firmware/` is a byte-preserved, GPL-3.0-only validation
corpus from the adjacent `OTGW-firmware` repository. It is test data only and
is isolated from ADR Kit's MIT-licensed runtime payload. Run its focused tests
after changing format detection, migration, lint, indexing, context, or
relationship behavior:

```bash
python -m pytest tests/test_otgw_corpus.py -q
```

Refresh it only from a reviewed, clean numbered-ADR source set:

```bash
python scripts/refresh-otgw-corpus.py --source ../OTGW-firmware
```

Review the source revisions, file count, format counts, migration outcomes, and
hash changes in `tests/testsets/otgw-firmware/manifest.json` before accepting a
refresh. The script refuses to snapshot modified or untracked numbered ADRs.

## Pre-release smoke test

Schema validation catches manifest field-type bugs but does not exercise the actual install path. Before tagging a new release, run this manual checklist in a fresh Claude Code session against your local clone. The whole sequence takes about 3 minutes.

1. **Start Claude Code with the local clone as plugin source:**

   ```bash
   claude --plugin-dir /path/to/your/adr-kit
   ```

2. **List installed plugins.** Type `/plugin` in the Claude Code prompt. Confirm `adr-kit` appears in the Installed tab. Confirm there are no red error messages or `Validation errors:` lines next to the plugin entry. (This catches manifest schema mismatches that ajv missed and that would otherwise only surface for end users.)

3. **List slash commands.** Type `/help`. Confirm the following commands are registered:
   - `/adr-kit:adr`
   - `/adr-kit:setup`
   - `/adr-kit:lint`

   Missing commands typically mean a skill file is in the wrong directory or has malformed frontmatter.

4. **Run setup against a scratch project.** In a temporary directory (or any project that does not already have an `ADR Kit Rules` section in its `CLAUDE.md`), run:

   ```
   /adr-kit:setup
   ```

   Confirm the response is one of: `Setup complete. Appended ...`, `Setup complete. Created CLAUDE.md ...`, or `Already set up. ... at line N. No changes made.` Inspect `CLAUDE.md` to verify the section was appended literally and not duplicated. Re-run `/adr-kit:setup` and confirm it reports `Already set up.` (idempotency check).

5. **Run lint against a sample ADR.** Create a directory with at least one `ADR-001-foo.md` file, then run:

   ```
   /adr-kit:lint
   ```

   Confirm the output reports per-gate PASS / FAIL for each ADR found. The exact result is not what matters; what matters is that the skill executed and produced gate-by-gate output.

6. **If any of steps 2-5 fails, do not tag the release.** Investigate the failure first. Schema-only fixes (CI green, install red) are exactly the regressions this checklist exists to catch.

When the checklist passes, proceed with the release steps in the next section.

## Reporting issues

Use the issue templates if they fit. If not, a plain issue is fine. Include:

- Your AI coding tool and version (Claude Code, GitHub Copilot CLI, or OpenAI Codex).
- The reproduction steps.
- What you expected to happen.
- Any relevant config (sanitised, no secrets).

## License

By contributing, you agree that your contributions are licensed under the MIT license, the same license as the project.
