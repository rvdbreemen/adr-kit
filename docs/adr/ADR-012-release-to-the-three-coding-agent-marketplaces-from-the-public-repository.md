---
id: "ADR-012"
title: "Release to the Three Coding-Agent Marketplaces From the Public Repository"
status: "Accepted"
date: "2026-07-22"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-042"
topics:
  - "release"
  - "marketplace"
  - "runbook"
  - "tag gate"
aliases:
  - "release process"
  - "three marketplaces"
  - "public repository source"
components:
  - "release workflows"
  - "scripts"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-012 Release to the Three Coding-Agent Marketplaces From the Public Repository

## Status

Accepted, 2026-07-22.

## Status History

```yaml
status_history:
  - date: 2026-07-22
    status: Proposed
    changed_by: Claude
    reason: Formalizes how a version is published to the Claude Code, Codex and Copilot marketplaces after a release lagged (0.37.0 shipped to main but a machine stayed on 0.36.0)
    changed_via: adr-kit
  - date: 2026-07-22
    status: Accepted
    changed_by: adr-kit
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
  - date: 2026-08-26
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-042
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

adr-kit ships as a plugin to three coding agents: Claude Code, Codex, and GitHub
Copilot CLI. None of them has a central app store; each resolves its plugin
marketplace directly from the public `rvdbreemen/adr-kit` repository through a
client-specific manifest:

- Claude Code: `.claude-plugin/marketplace.json` (marketplace id `rvdbreemen-adr-kit`, plugin source `./`).
- Codex: `.agents/plugins/marketplace.json` (id `rvdbreemen-adr-kit-codex`, plugin source `./codex`).
- GitHub Copilot: `.github/plugin/marketplace.json` (id `rvdbreemen-adr-kit-copilot`, plugin source `copilot`).

There are two consumption paths: end users resolve the manifests straight from
the public repo ref (git source), while maintainer machines and offline installs
use a version-pinned prepared directory built by `scripts/install-agent-envs.py`
under the per-user data directory (ADR-006).

Until now the release process was undocumented and unenforced. Version 0.37.0 was
tagged and merged to `main`, yet a maintainer machine kept resolving 0.36.0: the
prepared-directory marketplace is version-pinned and does not roll forward on its
own, and a Claude re-point defect left the client registration on the old
directory. Nothing tied the version across the six version-bearing sites, the
adapter drift check, the governance gates, the tag, and the per-machine install
into one repeatable act. A release could therefore be internally inconsistent and
still ship.

## Decision Drivers

- A published version must be coherent across all three client marketplaces.
- Version drift between manifests, CHANGELOG and tag must fail the release, not the user.
- Automation should cover exactly what CI can prove; machine-local steps must stay explicit, not pretended-automated.
- The process must be reproducible and documented for every maintainer environment.

## Considered Options

- Documented runbook plus a tag-triggered CI gate that verifies consistency and cuts the GitHub Release, with the per-machine install kept as an explicit step.
- Keep the status quo: an undocumented, manual, per-person release.
- Fully automate publication, including advancing every maintainer machine, from CI.

## Decision Outcome

Chosen: the documented-runbook-plus-tag-triggered-gate option.

### Publish surface

The public repository is the marketplace for all three clients. Publishing a
version means landing version-consistent manifests on the public repo and cutting
a tag plus GitHub Release. End users on the git source are served by the tagged
manifests; no further action reaches them.

### Version-consistency invariant

`scripts/check-release-version.py` fails unless a single release version is
identical across: `.claude-plugin/plugin.json`, `codex/.codex-plugin/plugin.json`,
`copilot/plugin.json`, `.claude-plugin/marketplace.json`,
`.github/plugin/marketplace.json`, the first `## [X.Y.Z]` CHANGELOG heading, and
the git tag. The Codex marketplace manifest (`.agents/plugins/marketplace.json`)
carries no version field by design (it points at the local `./codex` source whose
version lives in the Codex plugin manifest) and is therefore not a version site.

### Release flow

`.github/workflows/release-publish.yml` triggers on a `v*` tag, re-runs the
version-consistency check, `build-client-adapters.py --check`, `adr-lint --strict`,
`adr-index --check` and `pytest`, then creates the GitHub Release from the
CHANGELOG section. It then calls the reusable OpenCode npm workflow, which stages
the package through Trusted Publishing without making it public; a maintainer's
2FA approval remains required. The existing `release-candidate.yml` remains the
optional three-native-client certification (ADR-010), and the npm stage is not
part of that certification boundary.

### Automation boundary

The per-machine prepared-directory publish (`install-agent-envs.py --clients all`,
then restart each client) is a documented local step, not a CI job, because it
mutates per-user client installs on a specific machine. OpenCode npm staging is
safe to run in CI, but final npm publication remains human-gated by 2FA.
`docs/RELEASING.md` is the authoritative runbook.

### Confirmation

`check-release-version.py --expect v0.37.0` passes against the current tree; the
workflow parses, and the four gates run in CI on tag push.

## Consequences

### Positive

- A release cannot ship with a version mismatch across the three marketplaces; the gate would have caught the 0.37.0 lag.
- The publish is reproducible and documented for every maintainer environment.
- CI automates only what it can prove; the machine-local step is honest and visible.

### Negative

- The per-machine install remains manual, so a maintainer must run it and restart clients after each release.
- The daily prepared-directory source stays version-pinned; a skipped local install still lags until re-run (mitigated by documentation and the re-point fix in the installer).

## Pros and Cons of the Options

### Documented runbook plus tag-triggered gate

- Good: enforces consistency, publishes to git-source users automatically, keeps machine-local steps explicit.
- Bad: the per-machine install is not automated.

### Keep the status quo

- Good: nothing to build.
- Bad: caused the 0.37.0 inconsistency; not reproducible.

### Fully automate including maintainer machines

- Good: no manual step.
- Bad: impossible from CI, which cannot mutate a maintainer's per-user client installs.

## Related Decisions

- ADR-006 (Prepare platform-local marketplaces for native installs): defines the version-pinned prepared-directory source this release flow advances.
- ADR-010 (Certify three native CLI clients through one outcome contract): the optional certification gate that complements this publish flow.

## References

- `docs/RELEASING.md` (runbook).
- `scripts/check-release-version.py`, `.github/workflows/release-publish.yml`.
- TASK-47 (this release flow); TASK-48 (Claude marketplace re-point defect that caused the 0.36.0 lag).

## Enforcement

```json
{
  "llm_judge": false,
  "llm_judge_reason": "no code surface: this decision governs process or documentation, so there is no diff for a model to judge it against"
}
```
