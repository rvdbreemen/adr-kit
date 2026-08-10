---
id: TASK-166
title: Installer reports a per-client version it never read from the client
status: Done
assignee: []
created_date: '2026-08-09 19:25'
updated_date: '2026-08-10 20:11'
labels:
  - bug
  - installer
  - detection
dependencies: []
references:
  - clients/installer/detection.py
  - clients/installer/planning.py
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
modified_files:
  - clients/installer/detection.py
  - clients/installer/registrations.py
  - scripts/install-agent-envs.py
  - tests/test_agent_installer.py
  - tests/test_release_allowlist.py
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
- [x] #1 installed_version is read from the client's own registration, not from a marketplace marker shared across clients
- [ ] #2 A client with no adr-kit plugin is never planned as SKIP on the grounds that it is already at the target version
- [x] #3 Marker roots are ranked by parsed semantic version, not by string sort, and .old backup directories never outrank their live counterpart
- [x] #4 duplicate_roots lists the backups, not the active directory
- [x] #5 Regression coverage builds a marketplaces directory containing 0.9.0, 0.48.0 and 0.48.0.old and asserts the live 0.48.0 root wins
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both defects were real and are fixed, but the task was wrong on three points worth recording.

**Defect 1 - one marker spoke for three clients.** `detailed_detection` hoisted `roots[-1]` out of the loop, so every client received the same `installed_version`, read from a marketplace payload directory rather than from any client. `detailed_detection` now takes an `installed_versions` mapping and derives nothing; a client that reports nothing reads as `detected`, not as installed at the payload's version.

**Defect 2 - a backup outranked the live directory.** Measured before: `roots[-1]` was `...\marketplaces\0.49.0.old`. Ranking is now by parsed version with an explicit demotion for `.old` and `.tmp`, so on the same machine the live `0.49.0` wins and the order reads `0.47.0, 0.48.0.old, 0.48.0, 0.49.0.old, 0.49.0`. `.tmp` is included because payload.py writes that marker before it copies the payload, so an interrupted run leaves a marker with no version at all - the task named only `.old`.

**Where the reader lives, and why not where the task assumed.** The task presents "read each client's own config" as one uniform option. It is not: codex's `config.toml` records that the plugin is enabled and carries no version, and `tomllib` is 3.11+ against a declared floor of 3.10; copilot's `config.json` is JSONC, opening with `//` banner lines that `json.loads` rejects. And detection.py is mirrored into codex/ and copilot/, where it must stay stdlib-only and keep its promise not to invoke plugin managers.

So the readers live in a new `clients/installer/registrations.py`, which is not mirrored, and the answer is handed to detection as data. The first plan put them in native.py, which would have taken that file to 462 lines against ADR-010's 400-line cap - the same trap payload.py hit in v0.49.0. registrations.py is 128 lines and is named in the budget test.

**Caught only by running it against the real clients:** codex answers `{"installed": [{"pluginId": ..., "version": ...}]}`, not the `{"plugins": [{"id": ...}]}` shape the plan assumed. Written against the assumption, codex read as "not installed" - a silent wrong answer of exactly the kind this task exists to remove. The reader now accepts both spellings and the test carries codex's real shape.

Verified end to end. Before: all three clients reported `installed:0.48.0` from a shared marker. Now: `claude: installed:0.49.0`, `codex: installed:0.49.0`, `copilot: installed:0.49.0`, each read from that client's own registration, and an empty `installed_versions` renders `detected` rather than a version.

**Record correction, acceptance criterion 2.** It states that a client is "planned as SKIP on the grounds that it is already at the target version". No code path does that: `planning.py` computes selection from the requested set and the enabled flag, and never consults `installed_version`. In the reported repro, `--clients claude` made copilot's reason "explicit selection", which was correct - only the rendered `current_state` was fabricated. Left unchecked because the behaviour it describes does not exist; the real consequence is recorded instead.

**A consequence the task missed:** `planning.py` also feeds `installed_version` into the breaking-migration gate, which raises `requires_confirmation` on a major-version change. A fabricated version could therefore have demanded `--yes` for a migration that was not happening, or masked one that was. That is behavioural, not cosmetic.
<!-- SECTION:FINAL_SUMMARY:END -->
