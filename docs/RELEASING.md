# Releasing adr-kit to the coding-agent marketplaces

adr-kit ships as a plugin to three certified coding-agent CLIs: **Claude Code**,
**Codex**, and **GitHub Copilot CLI**, plus a native **OpenCode** package. This
document is the authoritative release runbook and explains the distribution
model that makes the steps necessary.

## Distribution model: the public repo is the certified marketplace source

There is no external app store for the three certified CLI integrations. Each of
those clients resolves its plugin marketplace directly from the public
`rvdbreemen/adr-kit` repository. OpenCode loads the native package from a
repository checkout or, when separately published, from npm. Publishing a
repository version means: land version-consistent manifests on the public repo,
tag it, and cut a GitHub Release. The canonical release workflow then calls the
reusable OpenCode workflow to stage the npm package for maintainer approval.

| Client | Marketplace manifest (in repo) | Marketplace id | Plugin manifest | Plugin source |
|---|---|---|---|---|
| Claude Code | `.claude-plugin/marketplace.json` | `rvdbreemen-adr-kit` | `.claude-plugin/plugin.json` | `./` (repo root) |
| Codex | `.agents/plugins/marketplace.json` | `rvdbreemen-adr-kit-codex` | `codex/.codex-plugin/plugin.json` | `./codex` |
| GitHub Copilot | `.github/plugin/marketplace.json` | `rvdbreemen-adr-kit-copilot` | `copilot/plugin.json` | `copilot` |
| OpenCode | `opencode.json` / `package.json` | repository package source; npm when separately published | `package.json` | repository root |

End users add the marketplace and install the plugin, for example on Claude Code:

```
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
```

Codex and Copilot use the equivalent `codex plugin ...` / `copilot plugin ...`
verbs against the same public repo.

### Two consumption paths

1. **Public git source (end users).** The three certified clients resolve their
   manifests from the public repo ref (default branch, or a tag). Once the tagged
   commit carries the new version, git-source users get it. OpenCode users can
   point at the tagged repository checkout; npm remains a separate publication
   path.
2. **Local prepared directory (maintainer machines, offline installs).**
   `scripts/install-agent-envs.py` builds a versioned prepared marketplace under
   the per-user data directory and re-registers each client CLI against it:
   - Windows: `%LOCALAPPDATA%\adr-kit\marketplaces\<version>`
   - macOS: `~/Library/Application Support/adr-kit/marketplaces/<version>`
   - Linux: `${XDG_DATA_HOME:-~/.local/share}/adr-kit/marketplaces/<version>`

   This path is version-pinned and does **not** roll forward on its own. A machine
   on this source stays on the old version until the installer is re-run. (This is
   exactly why 0.37.0 shipped to `main` yet a maintainer machine stayed on 0.36.0.)

## Version sites (one version, one registry)

A release is only coherent when the version is identical everywhere.
`packaging/version-sites.json` is the single registry that declares every
version-bearing file and how to read and write it. Four tools read that one file:

| Tool | Uses the registry to |
|---|---|
| `scripts/bump-version.py` | write the version to every site |
| `scripts/check-release-version.py` | fail the release on any mismatch |
| `scripts/build-client-adapters.py` | refuse to generate against stale manifests |
| `tests/test_version_sites.py` | keep the registry and the repo honest |

Currently declared: the CHANGELOG release heading (canonical), the three
certified client plugin manifests, the OpenCode npm package, the two versioned
marketplace manifests, the pre-commit / guardian-entry / guide template stamps,
the two README version pins, and the action pin in the readiness workflow
template. The git tag is compared against them at
release time.

`.agents/plugins/marketplace.json` (Codex) carries no version by design: it points
at the local `./codex` source whose version lives in the Codex plugin manifest, so
the registry asserts it stays absent. README history markers such as "introduced
in v0.31.0" are deliberately not sites: they record when a feature landed and must
never move.

Every check reports *all* mismatches in one pass, so a bump surfaces its complete
work list immediately instead of one error per tool run.

## Release steps

### 0. Confirm `dev` carries every published release

```bash
git fetch origin
python scripts/check-branch-sync.py
```

Run this *before* cutting the release branch. A release branch is cut from
`dev`, so any release still sitting only on `main` is missing from it, and the
release PR back into `main` then arrives as a pile of version-stamp conflicts —
one per publish surface, each of them the previous release's number against the
new one. Resolving them by hand is exactly the moment a published version gets
reverted by accident.

Exit 0 means `dev` is current: continue to step 1. Exit 1 names the release tags
that reached `main` but never reached `dev`; do the step 4 merge-back for those
first, land it, and only then cut the release branch. Exit 2 is an
infrastructure error (bad ref, not a git repo), not a verdict.

This is the same check step 4 runs after the release. Running it at both ends is
deliberate: step 4 proves *this* release got home, step 0 proves the *previous*
one did. Skipping step 0 is silent at the time — the drift only surfaces as
conflicts once the release PR is already open. It has gone wrong at v0.53.0
(three releases behind, 18 conflicting files) and, worse, before v0.40.0
(32 commits behind, missing the release toolchain itself).

### 1. Prepare the version, release notes and README on a branch

```bash
python scripts/bump-version.py X.Y.Z                # writes EVERY version site
python scripts/build-client-adapters.py             # regenerate codex/ and copilot/
```

`scripts/bump-version.py` is the canonical writer and the only place a version is
typed. `bin/bump-version` forwards to it and implements nothing; there is no
second bump tool to choose between. Until v0.47.0 there was, and the two did not
do the same thing — the one this runbook names could not write the CHANGELOG
compare-link block, so that block went stale on every release (TASK-139).

It writes the CHANGELOG release heading, the CHANGELOG compare-link block
(`[Unreleased]` retargeted and a `[X.Y.Z]` link added), the three certified
client plugin manifests, the OpenCode package version, the two versioned
marketplace manifests, the template version stamps and the README version pins,
all from the declarative registry in
`packaging/version-sites.json`. Before writing anything it checks that the client
manifests agree on the plugin name and that every marketplace pointer resolves to
that plugin's entry.

Never hand-edit a version: if a file is missing from the bump, declare it in the
registry instead, and every tool (writer, gate, generator, tests) learns about it
at once.

- **Release notes**: add the `## [X.Y.Z] - YYYY-MM-DD` section at the top of
  `CHANGELOG.md`, written to release-note quality (grouped `### Added`/`### Changed`/
  `### Fixed`, user-facing impact, upgrade + breaking-change notes; Keep a Changelog,
  no emoji). `release-publish.yml` publishes this section verbatim as the GitHub
  Release body, so it *is* the release notes.
- **README**: update the version-pinned usage examples so users copy the current
  version (`grep -nE "adr-judge@v[0-9]|rev: v[0-9]|adr-kit/.*@v[0-9]" README.md`); the
  release badge is automatic and historical "introduced in vN" markers stay. Update
  any feature/usage section that this release changes.
- **README "What's new"**: not every release gets a row - the table covers
  releases that change what ADR Kit does - so there is no gate demanding one, and
  adding a row is your judgement. What *is* enforced (TASK-163,
  `tests/test_documentation_contracts.py`) is that no row keeps pointing at a
  decision that stopped governing: if this release supersedes or retires an ADR
  that an older row links, say so in that row ("retired in X.Y.Z" or "superseded
  by ADR-NNN") or drop the link. The prose review above is still yours; only the
  stale-link property is mechanical.

### 2. Verify locally (the same gates CI runs)

```bash
python scripts/check-release-version.py --expect vX.Y.Z
python scripts/build-client-adapters.py --check     # no adapter drift
python bin/adr-lint --strict docs/adr
python bin/adr-index --check docs/adr
python -m pytest -q
npx markdownlint-cli2@0.14.0 "skills/**/*.md" "codex/skills/**/*.md" \
  "copilot/skills/**/*.md" "agents/**/*.md" "instructions/**/*.md" \
  "examples/**/*.md" "templates/**/*.md"
```

The markdownlint line pins the version and repeats the globs from
`.github/workflows/validate.yml` deliberately: they must stay in step, and a
different version resolves different rules. It was missing here until v0.44.0,
where "all gates green locally" was true and the release PR still failed on a
double blank line in a skill file — the rest of these gates are Python and none
of them read Markdown. Feature branches do not run `validate`, so a Markdown
defect can sit unseen from the commit that introduced it until the release PR
opens, which is the worst moment to find it.

**Your machine has libraries the runners do not.** CI installs `pytest` and
nothing else, because ADR-016 makes zero runtime dependencies load-bearing. A
test that imports a third-party module therefore passes locally and fails on
all six runners at once. This also bit v0.44.0: a `import yaml` in
`tests/test_adr_lifecycle.py` was green on a developer machine with PyYAML
installed and red everywhere else. Run the suite once with the extras hidden
before opening the release PR:

```bash
python - <<'PY'
import sys
from importlib.abc import MetaPathFinder

BLOCKED = {"yaml", "requests", "httpx", "numpy", "pydantic"}


class Block(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            raise ImportError(f"No module named '{fullname}'")
        return None


sys.meta_path.insert(0, Block())
import pytest
sys.exit(pytest.main(["-q"]))
PY
```

Skips are fine — `pytest.importorskip` is the supported way to reach for an
optional library. Failures are not. If a check matters enough to guard a
regression, assert the structural form unconditionally and use the library only
for the stronger parse on machines that have it.

**If `ADR Enforcement (declarative)` fails on the release PR with `exceeds
--max-diff-bytes=...`, that is the cap, not a violation.** The gate judges
`origin/main...HEAD`, which for a release PR is the whole development branch,
and this repository counts most changes about three times because it ships
mirrored `codex/` and `copilot/` distributions. The fix is to raise the
`max-diff-bytes` input on `.github/actions/adr-judge` (default 32 MiB), **not**
`judge.max_diff_bytes` in `docs/adr/.adr-kit.json` — that number is the
pre-commit budget for a single commit and must stay small (ADR-015's latency
budget). Never set either to 0 to get past it: the cap is what makes an
unscanned diff fail closed instead of reporting an unearned success. This bit
once at v0.43.0, where the diff was 2,281,314 bytes against a 2 MiB cap and
scanned clean in 4.5 s once the budget fit.

### 3. Land on the public repo and tag

`main` is a protected branch, so **merging is the maintainer's action**. An agent
running this runbook reports that the PR is green and hands off; it must not merge
with `--admin` or otherwise bypass branch protection. If the PR gains extra commits
after the first CI run (applied code-scanning autofixes, for example), review them
and confirm CI is green for the final head before merging.

```bash
# after the maintainer merged the PR, on main:
git pull origin main
python scripts/check-release-version.py --expect vX.Y.Z   # main really carries it
git tag vX.Y.Z
git push origin vX.Y.Z
```

Pushing the tag triggers **`.github/workflows/release-publish.yml`** (the release
flow), which re-runs every gate above and creates the GitHub Release from the
CHANGELOG section. If any version site disagrees, the workflow fails before the
Release is cut. After the Release is created, the same workflow invokes the
reusable `.github/workflows/publish-opencode-npm.yml` workflow. It stages the
OpenCode package through OIDC; it does not make the package public without the
maintainer's npm 2FA approval. The same sequence runs when `release-publish.yml`
is manually dispatched with an existing tag.

### 3a. Stage the OpenCode package for npm

The first package publication is a deliberate manual bootstrap. npm Trusted
Publishers and staged publishing require the package to exist first. That
bootstrap was completed for `@rvdbreemen/adr-kit-opencode@0.52.0` with local
2FA. It has no OIDC provenance; future versions use the staged workflow.

Before the first automated staging run, configure the package's Trusted Publisher
on npmjs.com with these exact values:

| npm setting | Value |
|---|---|
| Provider | GitHub Actions |
| Organization or user | `rvdbreemen` |
| Repository | `adr-kit` |
| Workflow filename | `release-publish.yml` |
| Environment name | empty; npm performs the final approval |
| Allowed action | `npm stage publish` |

The reusable staging workflow pins npm `11.19.0`, which satisfies the
staged-publishing requirement of npm `11.15.0` or newer. Configure the
relationship locally after signing in and enabling 2FA:

```bash
npm trust github @rvdbreemen/adr-kit-opencode --repo rvdbreemen/adr-kit --file release-publish.yml --allow-stage-publish
```

No separate staging dispatch is needed. Push a new release tag, or run
**Actions -> ADR Kit release publish -> Run workflow** with an existing
unpublished release tag such as `v0.53.0`. After the GitHub Release is created,
the release workflow checks the exact tag, version sites, generated adapters,
ADR index, focused OpenCode tests, and the package tarball. It refuses a version
already present on npm, then stages the package through OIDC without an npm
token. The reusable `publish-opencode-npm.yml` file is the implementation helper;
`release-publish.yml` is the Trusted Publisher workflow identity.

The final manual step is on npm: open **Staged Packages**, inspect the staged
tarball, and approve it with 2FA. The approval publishes the package and allows
npm to publish the provenance requested during the OIDC staging operation. If the
staged package is rejected, it never becomes publicly available.

### 4. Merge the release back into `dev`

**Do not skip this, and do not leave it for later.** Releases land on `main`, but
day-to-day work continues on `dev`, and nothing else moves the release commits
back. Skipping it does not cause an error at the time; it silently arms the next
release to revert this one.

This has already gone wrong three times. By v0.40.0 the `dev` branch was 32
commits behind `main`, still declared version 0.37.0, and was missing
`bump-version.py`, `check-release-version.py`, `packaging/version-sites.json`,
this runbook and `release-publish.yml`, plus ADR-012, ADR-013 and ADR-014. Every
one of those is machinery a release is supposed to run, so `dev` had quietly
become unable to cut a correct release at all. At v0.53.0 the drift was smaller
(three releases) but surfaced the same way: a release branch cut from a stale
`dev` met `main` with 18 conflicting files, every one of them a version stamp.
Step 0 exists to catch that before the branch is cut.

```bash
git fetch origin
git checkout -b sync/release-to-dev origin/dev
git merge origin/main
```

Resolve any conflicts, then run the step 2 gates on the merge result before
opening a PR into `dev`. Treat the release branch as authoritative for anything a
release touches (version sites, generated `codex/` and `copilot/` adapters,
manifests). In `CHANGELOG.md`, keep the `[Unreleased]` entries from `dev` on top
and the published release sections from `main` below them.

`.github/workflows/branch-sync-check.yml` runs daily and fails when `dev` is
behind `main`, naming the released versions that never made it back. To check at
any time:

```bash
python scripts/check-branch-sync.py
```

### 5. Optional: three-client native certification

`.github/workflows/release-candidate.yml` (manual `workflow_dispatch`) certifies a
candidate SHA against redacted native Windows evidence for all three clients. Run
it when the release needs the certified-support artifact; it validates and uploads
evidence but does not publish.

The OpenCode package has a separate focused smoke contract. It is not included
in this three-client certification gate; run
`python -m pytest -q tests/test_opencode_package.py tests/test_opencode_plugin.py`
on a machine with Bun when OpenCode package or API behavior changes.

### 6. Publish to maintainer machines (prepared-directory source)

End users on the git source are already served by step 3. Machines on the local
prepared-directory source must advance explicitly:

```bash
python scripts/install-agent-envs.py --clients all
# then restart each client (Claude Code / Codex / Copilot) to load the new version
```

This rebuilds `.../adr-kit/marketplaces/<version>` and re-registers all three
client CLIs against it. It is idempotent and machine-local, so it cannot run in
CI; it is a per-machine step for each maintainer environment.

**Always verify per client afterwards**, because a combined run can leave one client
half-done (the 0.39.0 publish registered the Copilot marketplace but did not install
the plugin, and the completion line silently listed only the other two):

```bash
claude plugin list ; codex plugin list ; copilot plugin list   # each must show the new version
```

If one lags, re-run the installer for that client alone
(`python scripts/install-agent-envs.py --clients copilot`). Tracked as TASK-51.

## Why npm is staged rather than directly public

The public repo *is* the marketplace, so the tag + Release in step 3 is the
publication for git-source users. The release workflow automatically stages the
npm package, but a maintainer must review the staged tarball and approve it with
2FA before npm makes it public. The other remaining action, step 6, mutates
per-user client installs on a specific machine and therefore stays a documented
local command rather than a CI job.

## Release flow summary

| Artifact | Purpose |
|---|---|
| `/release-adr-kit` (`.claude/commands/release-adr-kit.md`) | Repo-level command that drives this runbook locally end to end |
| `scripts/check-release-version.py` | Fails unless all declared version sites, including the OpenCode package, equal the tag |
| `.github/workflows/release-publish.yml` | Tag-triggered/manual release gate + GitHub Release + OpenCode npm staging handoff |
| `.github/workflows/publish-opencode-npm.yml` | Reusable OpenCode release preflight, OIDC staging, and npm approval handoff |
| `.github/workflows/release-candidate.yml` | Optional three-client native certification |
| `scripts/check-branch-sync.py` | Fails when `dev` is missing release commits from `main`; run in step 0 (before cutting the branch) and step 4 (after merging back) |
| `.github/workflows/branch-sync-check.yml` | Daily guard that the merge-back in step 4 actually happened |
| `scripts/install-agent-envs.py` | Per-machine prepared-directory publish + client registration |
