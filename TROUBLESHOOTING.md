# ADR Kit troubleshooting

## Start with the fast doctor

```bash
python bin/adr-doctor --repo-root /path/to/project
```

Fast mode uses local files and bounded executable-version probes. It does not
log in, invoke an agent/model, rebuild broad indexes, run certification, or
contact cloud services. It checks ADR/index state, generated adapter drift,
effective settings, managed guidance, native CLI identity, MCP launcher
targets, and cached local-model health.

Default mode repairs only enumerated deterministic ADR Kit-owned drift, such
as a stale generated ADR index or generated client artifacts. Use `--check`
for the same diagnosis without writes:

```bash
python bin/adr-doctor --check --format json
```

## Deep probes

```bash
python bin/adr-doctor --deep --format json
```

Deep mode adds bounded native plugin-list probes, an MCP
initialize/tools-list/adr-status call, and local provider/model identity and
health checks. It never performs an agent turn. Hook fixtures and latency
measurements use the versioned `hook-latency-extension` object populated by
the hook certification harness.

## Repair levels

- Default: deterministic ADR Kit-owned regeneration only.
- `--check`: read-only; returns non-zero for required failures.
- `--fix`: additionally permits backed-up managed-guide/instruction rewrites
  and native re-registration where the doctor identifies an owned stale
  registration.

Backups are stored under `.adr-kit/backups/`. The doctor reports the exact
owned path or command and recovery location. It never rewrites unrelated
configuration keys, content outside ADR Kit markers,
`.adr-kit/ADR-guide.local.md`, project ADRs, secrets, or other plugins.

## Common states

- `stale`: an owned manifest or launcher points at a removed payload.
- `trust-pending`: the native client requires plugin review/trust approval.
- `disabled`: effective settings intentionally disabled the client or local
  judgment.
- `degraded`: an optional capability is unavailable, including a missing
  provider, nonexistent model tag, ambiguous model discovery, unreachable
  backend, or rejected health probe.
- `failed`: a required first-class outcome is missing or invalid.

For a stale native registration, review the desired-state plan before repair:

```bash
python scripts/install-agent-envs.py --plan
python scripts/install-agent-envs.py --clients codex
```
