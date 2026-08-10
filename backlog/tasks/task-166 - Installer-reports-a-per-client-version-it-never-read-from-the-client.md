---
id: TASK-166
title: Installer reports a per-client version it never read from the client
status: To Do
assignee: []
created_date: '2026-08-09 19:25'
labels:
  - bug
  - installer
  - detection
dependencies: []
references:
  - clients/installer/detection.py
  - clients/installer/planning.py
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
priority: high
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`python scripts/install-agent-envs.py --clients claude` prints `copilot: SKIP; installed:0.48.0 -> installed:0.48.0` on a machine where copilot has no adr-kit plugin at all (`~/.copilot/config.json` reads `"installedPlugins": []`, with stale 0.47.0 files left on disk per TASK-164). The plan is stating something it never checked.

Two defects in `clients/installer/detection.py`, both reproduced on this machine.

**1. `installed_version` is not per client.** `detailed_detection` (detection.py:99-147) derives `installed_version` from a single marker shared by all three clients: `marker = current[1]`, where `current = roots[-1]` from `_marker_roots(install_root)`. Every client in the loop gets the same value. Nothing in that path consults the client's own registry, so a client that failed to install, was never installed, or sits at an older version is still reported as installed at the marketplace's version — and is then planned as SKIP.

**2. `_marker_roots` sorts lexicographically, so a `.old` backup outranks the live directory.** detection.py:86-96 does `sorted(install_root.glob("*/.adr-kit-prepared-source.json"))` and the caller takes `roots[-1]`. Measured on this machine (17 marker directories present):

```
0.44.1 / 0.44.1.old / 0.46.0 / 0.47.0 / 0.48.0 / 0.48.0.old
GEKOZEN root (roots[-1]): ...\marketplaces\0.48.0.old
GEKOZEN version        : 0.48.0
```

The active `0.48.0` directory is not selected; its `.old` backup is, because `"0.48.0.old" > "0.48.0"` as a string. Consequences: `duplicate_roots` lists the *active* directory as the duplicate, and `source`/`source_sha256` are read from the backup. Today the two markers happen to carry the same version, so the reported number is accidentally right. After a rollback, where `<version>.old` holds the previous payload, it would be wrong.

The same ordering is wrong for versions generally: `"0.9.0" > "0.48.0"` lexicographically, so a future 0.9.x would outrank 0.48.x. This is the glob-ordering class the release-gate notes already warned about.

Related but distinct: TASK-164 covers the rollback that dismantled copilot's working install. This task covers the detection that then reports the wreckage as healthy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 installed_version is read from the client's own registration, not from a marketplace marker shared across clients
- [ ] #2 A client with no adr-kit plugin is never planned as SKIP on the grounds that it is already at the target version
- [ ] #3 Marker roots are ranked by parsed semantic version, not by string sort, and .old backup directories never outrank their live counterpart
- [ ] #4 duplicate_roots lists the backups, not the active directory
- [ ] #5 Regression coverage builds a marketplaces directory containing 0.9.0, 0.48.0 and 0.48.0.old and asserts the live 0.48.0 root wins
<!-- AC:END -->
