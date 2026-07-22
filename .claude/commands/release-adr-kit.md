---
description: Release adr-kit to the Claude Code, Codex and Copilot marketplaces (drives docs/RELEASING.md)
argument-hint: "[version, e.g. 0.38.0]"
---

You are running the adr-kit release for version **$ARGUMENTS** (if empty, ask which
version to release, or read the intended version from `.claude-plugin/plugin.json`).

The authoritative runbook is `docs/RELEASING.md` and the decision behind it is
ADR-012. The three coding-agent marketplaces (Claude Code, Codex, GitHub Copilot)
all resolve adr-kit from the public repository, so a release must be version-
consistent across every publish surface before it ships. Follow these steps in
order. Stop and report if any step fails.

## 1. Create a task and a branch

- Ensure a backlog task exists for this release (create one if not); set it In Progress.
- Work on a branch, never commit the release directly to `main`.

## 2. Prepare the version, release notes and README

- Bump every version site with one command, then regenerate the client trees:

  ```bash
  python scripts/bump-version.py $ARGUMENTS
  python scripts/build-client-adapters.py
  ```

  `bump-version.py` is the only place a version is typed. It writes the CHANGELOG
  heading, the three plugin manifests, the two versioned marketplace manifests, the
  template version stamps and the README version pins, all from
  `packaging/version-sites.json`. Never hand-edit a version, and never hand-edit the
  generated adapters. If some file still carries an old version, declare it in the
  registry instead of patching it by hand, so the writer, the gate, the generator and
  the tests all learn about it at once.

- **Release notes (`CHANGELOG.md`).** Add a `## [$ARGUMENTS] - <today>` section at the top.
  Write it to release-note quality, not a raw commit log: group changes under
  `### Added` / `### Changed` / `### Fixed` / `### Removed`, name user-facing impact,
  and call out upgrade steps and breaking changes explicitly. This section is the
  single source for the release notes: `release-publish.yml` publishes it verbatim as
  the GitHub Release body, so it must read as the release announcement. Follow Keep a
  Changelog; no emoji.

- **README (`README.md`).** The version-pinned usage examples are already moved by
  `bump-version.py` (the release badge is automatic and historical "introduced in vN"
  markers stay put by design). What still needs judgement: if this release adds,
  changes or removes a user-facing capability, update the matching feature/usage
  section so the README describes what actually ships.

## 3. Verify locally (the same gates CI enforces)

Run each and confirm it passes:

```bash
python scripts/check-release-version.py --expect v$ARGUMENTS
python scripts/build-client-adapters.py --check
python bin/adr-lint --strict docs/adr
python bin/adr-index --check docs/adr
python -m pytest -q
```

Do not proceed while any gate fails.

## 4. Land and tag (publishes the public git-source marketplaces)

- Open a PR from the branch into `main` and wait for CI to go green.

  **Maintainer checkpoint: `main` is a protected branch.** Merging is the
  maintainer's action, not the agent's. Do not merge with `--admin` and do not
  otherwise bypass branch protection: report that the PR is green and hand off. If
  the PR picks up extra commits after the first CI run (for example applied
  code-scanning autofixes), review those commits and confirm CI is green for the
  final head before handing off.

- After the maintainer merges, pull `main`, confirm it carries the release version
  with `python scripts/check-release-version.py --expect v$ARGUMENTS`, then tag and
  push:

```bash
git tag v$ARGUMENTS
git push origin v$ARGUMENTS
```

Pushing the tag triggers `.github/workflows/release-publish.yml`, which re-runs the
gates and creates the GitHub Release from the CHANGELOG section. Confirm that
workflow went green before continuing.

**Checkpoint:** tagging + pushing is outward-facing. Confirm with the maintainer
before pushing the tag unless already authorized.

## 5. Publish to this machine's prepared-directory marketplace

End users on the git source are already served by step 4. Advance the local
prepared-directory source and re-register all three clients:

```bash
python scripts/install-agent-envs.py --clients all
```

Then remind the maintainer to restart each client (Claude Code / Codex / Copilot)
to load the new version. Verify with `claude plugin list`, `codex plugin list`,
`copilot plugin list` that each shows adr-kit at v$ARGUMENTS.

## 6. Report

Summarize: version, gate results, tag + Release URL, and the local install +
per-client version confirmation. Close the release task.
