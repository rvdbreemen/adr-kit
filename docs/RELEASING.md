# Releasing adr-kit to the coding-agent marketplaces

adr-kit ships as a plugin to three coding agents: **Claude Code**, **Codex**, and
**GitHub Copilot CLI**. This document is the authoritative release runbook and
explains the distribution model that makes the steps necessary.

## Distribution model: the public repo IS the marketplace

There is no external app store. Each agent resolves its plugin marketplace
directly from the public `rvdbreemen/adr-kit` repository. Publishing a version
means: land version-consistent manifests on the public repo, tag it, and cut a
GitHub Release.

| Client | Marketplace manifest (in repo) | Marketplace id | Plugin manifest | Plugin source |
|---|---|---|---|---|
| Claude Code | `.claude-plugin/marketplace.json` | `rvdbreemen-adr-kit` | `.claude-plugin/plugin.json` | `./` (repo root) |
| Codex | `.agents/plugins/marketplace.json` | `rvdbreemen-adr-kit-codex` | `codex/.codex-plugin/plugin.json` | `./codex` |
| GitHub Copilot | `.github/plugin/marketplace.json` | `rvdbreemen-adr-kit-copilot` | `copilot/plugin.json` | `copilot` |

End users add the marketplace and install the plugin, for example on Claude Code:

```
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
```

Codex and Copilot use the equivalent `codex plugin ...` / `copilot plugin ...`
verbs against the same public repo.

### Two consumption paths

1. **Public git source (end users).** The client resolves the manifests from the
   public repo ref (default branch, or a tag). Once the tagged commit carries the
   new version, git-source users get it. Nothing else is required for them.
2. **Local prepared directory (maintainer machines, offline installs).**
   `scripts/install-agent-envs.py` builds a versioned prepared marketplace under
   the per-user data directory and re-registers each client CLI against it:
   - Windows: `%LOCALAPPDATA%\adr-kit\marketplaces\<version>`
   - macOS: `~/Library/Application Support/adr-kit/marketplaces/<version>`
   - Linux: `${XDG_DATA_HOME:-~/.local/share}/adr-kit/marketplaces/<version>`

   This path is version-pinned and does **not** roll forward on its own. A machine
   on this source stays on the old version until the installer is re-run. (This is
   exactly why 0.37.0 shipped to `main` yet a maintainer machine stayed on 0.36.0.)

## Version sites (single release version, six places)

A release is only coherent when the version is identical everywhere.
`scripts/check-release-version.py --expect vX.Y.Z` enforces this:

- `.claude-plugin/plugin.json` -> `version`
- `codex/.codex-plugin/plugin.json` -> `version`
- `copilot/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`
- `.github/plugin/marketplace.json` -> `plugins[0].version`
- `CHANGELOG.md` -> first `## [X.Y.Z]` heading
- plus the git tag `vX.Y.Z`

`.agents/plugins/marketplace.json` (Codex) has no version field by design: it
points at the local `./codex` source whose version lives in the Codex plugin
manifest, so it is not a version site.

## Release steps

### 1. Prepare the version, release notes and README on a branch

```bash
# bump the canonical version, then regenerate the three client adapters so all
# manifests move together (never hand-edit the generated adapters):
python scripts/build-client-adapters.py            # regenerate adapters/manifests
```

- **Release notes**: add the `## [X.Y.Z] - YYYY-MM-DD` section at the top of
  `CHANGELOG.md`, written to release-note quality (grouped `### Added`/`### Changed`/
  `### Fixed`, user-facing impact, upgrade + breaking-change notes; Keep a Changelog,
  no emoji). `release-publish.yml` publishes this section verbatim as the GitHub
  Release body, so it *is* the release notes.
- **README**: update the version-pinned usage examples so users copy the current
  version (`grep -nE "adr-judge@v[0-9]|rev: v[0-9]|adr-kit/.*@v[0-9]" README.md`); the
  release badge is automatic and historical "introduced in vN" markers stay. Update
  any feature/usage section that this release changes.

### 2. Verify locally (the same gates CI runs)

```bash
python scripts/check-release-version.py --expect vX.Y.Z
python scripts/build-client-adapters.py --check     # no adapter drift
python bin/adr-lint --strict docs/adr
python bin/adr-index --check docs/adr
python -m pytest -q
```

### 3. Land on the public repo and tag

```bash
# open a PR from your branch into main, merge it, then on the merge commit:
git tag vX.Y.Z
git push origin vX.Y.Z
```

Pushing the tag triggers **`.github/workflows/release-publish.yml`** (the release
flow), which re-runs every gate above and creates the GitHub Release from the
CHANGELOG section. If any version site disagrees, the workflow fails before the
Release is cut.

### 4. Optional: three-client native certification

`.github/workflows/release-candidate.yml` (manual `workflow_dispatch`) certifies a
candidate SHA against redacted native Windows evidence for all three clients. Run
it when the release needs the certified-support artifact; it validates and uploads
evidence but does not publish.

### 5. Publish to maintainer machines (prepared-directory source)

End users on the git source are already served by step 3. Machines on the local
prepared-directory source must advance explicitly:

```bash
python scripts/install-agent-envs.py --clients all
# then restart each client (Claude Code / Codex / Copilot) to load the new version
```

This rebuilds `.../adr-kit/marketplaces/<version>` and re-registers all three
client CLIs against it. It is idempotent and machine-local, so it cannot run in
CI; it is a per-machine step for each maintainer environment.

## Why there is no fully-automated "publish to marketplace" job

The public repo *is* the marketplace, so the tag + Release in step 3 is the
publication for git-source users. The only remaining action, step 5, mutates
per-user client installs on a specific machine and therefore stays a documented
local command rather than a CI job.

## Release flow summary

| Artifact | Purpose |
|---|---|
| `/release-adr-kit` (`.claude/commands/release-adr-kit.md`) | Repo-level command that drives this runbook locally end to end |
| `scripts/check-release-version.py` | Fails unless all six version sites equal the tag |
| `.github/workflows/release-publish.yml` | Tag-triggered gate + GitHub Release (the release flow) |
| `.github/workflows/release-candidate.yml` | Optional three-client native certification |
| `scripts/install-agent-envs.py` | Per-machine prepared-directory publish + client registration |
