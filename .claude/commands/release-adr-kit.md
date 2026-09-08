You are running the adr-kit release for version **$ARGUMENTS** (if empty, ask
which version to release).

Since ADR-042 this is one command. `scripts/release.py` drives every step of
`docs/RELEASING.md`, and `docs/RELEASING.md` remains the specification it
implements. Do not perform the steps by hand while the driver exists: a second
hand-run path is how the two drift apart, and every failure this decision was
written about came from a mechanical step performed by a person.

## 1. Open a backlog task

Search for an existing release task; create one if there is none, and set it In
Progress. Record the version and why it is a major, minor or patch bump. A
behaviour change a consumer can observe is a minor bump even when it is filed
as a bug fix.

## 2. Write the release notes first

Run the driver once:

```bash
python scripts/release.py X.Y.Z
```

It bumps every version site through the registry, regenerates the client
adapters, and then **stops**, because the CHANGELOG section it created is still
a placeholder. That stop is deliberate: `release-publish.yml` publishes that
section verbatim as the GitHub Release body, so it has to read as the
announcement rather than as a commit log.

Write it under `## [X.Y.Z]`: group under `### Added` / `### Changed` /
`### Fixed` / `### Removed`, name the user-facing impact, and call out upgrade
steps and breaking changes explicitly. Keep a Changelog, no emoji.

Update `README.md` where this release adds, changes or removes a user-facing
capability. The version pins move themselves; what needs judgement is whether
the README still describes what ships.

## 3. Run it again, and keep running it

```bash
python scripts/release.py X.Y.Z
```

It verifies the gates, opens the pull request into `main` with auto-merge, waits
for the merge, checks that the tag the workflow created resolves to
`origin/main`, opens the sync-back pull request into `dev`, and advances this
machine's prepared-directory marketplace.

Safe to re-run at any point. Each phase asks the repository whether its work is
already done, so an interrupted release is resumed, not restarted. Use
`--status` to see what is left without changing anything, and `--skip-tests`
when CI is the run you are relying on.

**Never tag by hand**, and never merge with `--admin`. The tag is created by
`release-publish.yml` from the merged commit; typing it is what cost v0.55.0.

## 4. Do the one thing the driver cannot

The driver ends by printing the npm approval steps. npm requires proof of
presence, so no tool can finish it. If more than one version is staged, approve
in **ascending** order: npm sets `latest` to the version published last, not
the highest.

Run the driver once more afterwards. It verifies `dist-tags.latest` names the
released version and reports the release as complete.

## 5. Report and close

Summarise: version and why that bump, the tag and the Release URL, the
verification that the tag equals `origin/main`, the sync-back pull request, the
per-client versions read back, and the npm dist-tag. Close the task with that
evidence.

If a phase refused, say which one and quote its message rather than
paraphrasing it. The messages are written to be actionable, and a summary of an
error is harder to act on than the error.
