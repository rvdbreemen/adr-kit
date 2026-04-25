# adr-kit v0.9.0

Adds scoped lint with grandfathering. `/adr-kit:lint` now accepts a project-level config file plus per-ADR HTML-comment markers that let you apply the four verification gates surgically: strict on new ADRs, advisory on legacy ones, ignored on archived ones.

## Why this release exists

The four gates (Completeness, Evidence, Clarity, Consistency) are correct in principle but rigid in practice. Adopting adr-kit on an established project where 80+ ADRs already exist surfaces a noise problem: the legacy template is fine, but the heading shape diverges from canonical, so dozens of files report Completeness FAIL on a structural rule that nobody is being asked to fix. A lint output where most entries are noise is a lint output the user starts ignoring.

v0.9.0 keeps the gates intact and gives projects two ways to opt in.

## What is new

### Project-level config: `docs/adr/.adr-kit.json`

A JSON file at `docs/adr/.adr-kit.json` (optional). When present, `/adr-kit:lint` reads it before linting. Recognised fields:

- `strict_from` (string): first ADR id (inclusive) on which the gates are enforced strictly. ADRs with a lower number are linted in advisory mode for the gates that opt in.
- `ignore` (array): ADR ids or filenames to skip entirely. Useful for archived or superseded entries.
- `severity` (object): per-gate severity. Keys are `completeness`, `evidence`, `clarity`, `consistency`. Values: `always_strict`, `always_advisory`, `advisory_before_strict_from`. Consistency stays `always_strict` by default because filename / heading mismatches and duplicate numbers are real bugs at any age.
- `template.required_sections` (array): override the canonical seven required sections with the project's actual template.

A fully annotated copy lives at `examples/.adr-kit.sample.json`.

### Per-ADR markers

For one-off grandfathering without a project-wide config, drop one of these HTML comments anywhere in an individual ADR file:

```html
<!-- adr-kit-lint: skip -->
<!-- adr-kit-lint: skip completeness, evidence -->
<!-- adr-kit-lint: advisory -->
```

A worked example lives at `examples/ADR-sample-003-grandfathered-legacy.md`: a legacy-template ADR with the `advisory` marker that lints clean despite Completeness shape mismatches.

### Three-tier output

`/adr-kit:lint` reports PASS, ADVISORY (a finding that does not block but is reported), and FAIL. The aggregate's "next step" line always points at a FAIL, never an ADVISORY: ADVISORY is informational; FAIL is what the user is asked to act on.

Single-file output gains the reason for any ADVISORY:

```
ADR-042-foo.md
  Completeness: PASS
  Evidence:     ADVISORY
    line 24: "improves performance" with no measurement (ADVISORY: ADR predates strict_from=ADR-042)
  Clarity:      PASS
  Consistency:  PASS

Summary: 3 of 4 gates pass strictly. 1 advisory. No FAIL.
```

Directory-tree output groups files into `PASS strictly / ADVISORY only / FAIL / SKIPPED` counts, with a config banner when a `.adr-kit.json` is in effect.

### Severity decision tree

The skill body now includes a Graphviz decision tree documenting the precedence rules: ignore beats markers, markers beat config, and within config the precedence is `always_strict` > `always_advisory` > `advisory_before_strict_from`. PASS stays PASS regardless of policy.

## Smoke test against a real-world ADR set

Validated against an 87-ADR project with a legacy template:

| Config | PASS strictly | ADVISORY only | FAIL |
|---|---|---|---|
| Default (canonical seven, no `.adr-kit.json`) | 0 | 0 | 87 |
| `strict_from: "ADR-082"`, default severity | 2 | 80 | 5 |

The FAIL count drops from 87 (everything noise) to 5 (recent ADRs that genuinely lack canonical headings). The ADVISORY tier absorbs the legacy template mismatch without complaining about it. The 5 actionable FAILs are recent ADRs that the user can fix or further codify via `template.required_sections`.

## Backwards compatibility

When no `.adr-kit.json` and no per-ADR markers are present, behaviour is identical to v0.8.0: everything strict, FAIL on any gate failure. Existing users see no change unless they opt in.

## Out of scope (future work)

- v0.10.0: `/adr-kit:migrate` -- interactive helper that walks legacy ADRs and rewrites them into the canonical template, preserving content but reshaping headings.
- v0.11.0: per-team severity profiles (`severity_profile: "open-source"` vs `"internal"` etc.) as named bundles instead of per-gate configuration.

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

- Backlog task: TASK-420 (scoped lint with grandfathering).
- Related: TASK-419 (v0.8.0 schema validation pairs with this release; they were developed back to back).
