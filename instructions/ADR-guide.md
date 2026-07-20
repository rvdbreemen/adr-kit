<!-- adr-kit-guide v0.35.0 -->
<!-- Generated ADR Kit guidance. Local additions belong in .adr-kit/ADR-guide.local.md. -->

# ADR Kit agent guide

Architecture decisions live in `docs/adr/`. Read the source ADR before treating
a generated summary as binding.

## Before implementation

1. Query the task with `adr-kit:context` or `bin/adr-context`.
2. Read the returned Accepted ADRs.
3. If the work introduces or changes a long-lived decision, use `adr-kit:adr`
   and keep the new record Proposed until a human accepts it.

## During implementation

- Treat hook-provided ADR context as advisory steering. Hooks fail open.
- Treat deterministic pre-commit enforcement as the blocking floor.
- Never rewrite an Accepted ADR. Create a Proposed successor and use the
  supersession lifecycle.
- Keep generated indexes and client artifacts deterministic; edit their
  canonical sources instead.

## Before completion

1. Run strict ADR lint and the relevant focused tests.
2. Regenerate `docs/adr/ADR-INDEX.md`, `docs/adr/ADR-INDEX.json`, and the
   generated README block after ADR changes.
3. Use `adr-kit:judge` or `bin/adr-judge` to check the staged diff.
4. Record the decision, evidence, and verification in the project task.

## Ownership

`.adr-kit/ADR-guide.md` is generated and may be replaced after backup.
Put project-specific guidance in `.adr-kit/ADR-guide.local.md` or outside ADR
Kit marker blocks in `AGENTS.md`, `CLAUDE.md`, and Copilot instructions.

If `.adr-kit/ADR-guide.local.md` exists, read it after this file. It is
user-owned and ADR Kit never overwrites or removes it.

## Judgment

Deterministic ADR checks remain available without a model. Paid or cloud model
judgment is opt-in. Local judgment is active only when a configured or
unambiguously discovered provider/model identity has been verified. Missing,
ambiguous, or unreachable models are degraded optional judgment, never a
successful judgment result.
