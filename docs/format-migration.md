# ADR format discovery and migration

ADR Kit detects existing ADR formats automatically during project-aware
installation, initialization, upgrade, and lint. Detection is always
read-only. It informs the user; it never authorizes or applies a migration.

## Selectable target profiles

List the installed pre-made target catalog before choosing or migrating:

```bash
python bin/adr profiles
python bin/adr profiles --format json
```

MADR is preferred. Nygard and canonical are supported alternatives. These
three ids are registered in the shared semantic profile catalog and each must
resolve to its shipped `templates/adr-template.<profile>.md` file. Adding an
arbitrarily named template does not make a new format selectable. If a catalog
template is missing, repair or reinstall ADR Kit before creating or converting
records.

## Run discovery directly

```bash
python bin/adr-migrate --plan docs/adr
python bin/adr-migrate --plan --format json docs/adr
```

The planner scans canonical `ADR-NNN-...md` files and recognizable older
numeric filenames. Generated `README.md` and `ADR-INDEX.md` files are excluded.
The command exits successfully when notices exist because a notice is not a
failed migration.

## Detection and upgrade paths

| Detected shape | Detection basis | Upgrade path |
| --- | --- | --- |
| MADR | Distinct MADR headings or `format: madr` | Already supported; deterministic metadata/filename preview when needed |
| Nygard / adr-tools | Status, Context, Decision, Consequences | Already supported; deterministic metadata/filename preview when needed |
| adr-kit canonical | Canonical headings or `format: canonical` | Already supported; deterministic metadata preview when needed |
| Y-Statement | Full context/facing/decision/neglected/achieve/accepting sentence structure | Guided migration |
| Tyree/Akerman | Issue and Decision plus at least three distinctive structured fields | Guided migration |
| arc42 | Explicit Architecture Decisions section marker | Guided migration |
| Hybrid | Conflicting supported heading families | Guided source-profile selection |
| Unknown | ADR filename without a reliable supported or legacy signature | Guided semantic mapping |

The external-family detectors are intentionally conservative. Failing to
recognize an unusual variant is safer than assigning the wrong format and
rewriting a decision incorrectly.

## Deterministic path

For a supported profile that needs canonical metadata or filename
normalization, the report provides commands like:

```bash
python bin/adr-migrate --dry-run --to-profile nygard "docs/adr/0010-use-queues.md"
python bin/adr-migrate --to-profile nygard "docs/adr/0010-use-queues.md"
```

Review the dry-run first. Apply only after approval, then use the reported
`ADR-NNN-kebab-case-title.md` filename and run strict lint. Passing the detected
profile back through `--to-profile` retains that profile while adding its
required adr-kit extension sections and normalizing the legacy H1. Existing
MADR, Nygard, and canonical body profiles do not need conversion merely because
a different default is configured.

To deliberately standardize a supported record on another profile:

```bash
python bin/adr-migrate --dry-run --to-profile madr docs/adr/ADR-010-use-queues.md
python bin/adr-migrate --to-profile madr docs/adr/ADR-010-use-queues.md
python bin/adr-migrate --check --to-profile madr docs/adr/ADR-010-use-queues.md
```

Profile conversion preserves invariant frontmatter, Status History,
relationships, references, decision prose, and Enforcement.

## Guided path

When the report labels a file `guided`, invoke the migration skill shown in the
notice:

```text
/adr-kit:migrate "docs/adr/ADR-010-existing-decision.md"
```

Codex and other Agent Skills clients use their installed ADR Kit migrate skill.
The agent must read the source, show the proposed semantic mapping, preserve
existing content, use TODO markers instead of fabrication, and obtain approval
before writing. Unknown or hybrid records may use `--from-profile` only after
the real source profile has been established.

## Automatic invocation points

- `scripts/install-agent-envs.py --project-root <project>` runs the planner
  after client validation and fails open if discovery itself cannot run.
- The `init` and `upgrade` skills run the planner before changing project
  artifacts.
- `bin/adr-lint` includes a `migration_notices` array in JSON and an always
  visible read-only section in human output, including recognizable files that
  do not yet satisfy the canonical filename contract.

These paths may recommend a command. They must never run the recommended write
command automatically.
