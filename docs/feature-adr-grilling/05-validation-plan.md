# ADR Grilling validation plan

## Validation layers

### Unit validation

- Every readiness classification and finding code.
- Evidence classification and stable ordering.
- Clock injection and age calculation.
- Cross-platform path normalization.
- Open Questions semantics for all profiles.
- Explicit implementation-link rules and negative controls.
- Guardian ranking and tie-breaking.
- GitHub and shell escaping.

### Contract validation

- CLI human, JSON, and GitHub outputs.
- CLI exit behavior.
- JSON schema version and backwards-compatible extensions.
- CLI/MCP parity.
- The exact five-tool MCP inventory.
- Canonical workflow count and generated client artifacts.
- Lifecycle authority: read-only surfaces cannot mutate.

### Integration validation

- Subject to Proposed ADR.
- Proposed ADR through grill and acceptance packet to `adr accept`.
- Abort and resume.
- Reject and explicit defer.
- Reconstruction from code, PR, diff, chat log, and document.
- Existing Proposed ADR update instead of duplicate creation.
- Init with high- and low-confidence evidence.
- Review and judge routing.
- Guardian cache production and SessionStart consumption.
- Supersede, retire, and revalidate.
- Pre-commit advisory.
- Pull request advisory and linked-Proposed block.

### Regression validation

- Existing lint, quality, evidence, consistency, related, index, migrate,
  lifecycle, context, status, judge, guardian, hook, MCP, packaging, and client
  generation suites.
- Existing explicit `auto` configuration.
- Existing ADRs without Open Questions.
- Existing repositories without `CONTEXT.md`.
- Existing clients before regeneration.

## Determinism validation

Run equivalent fixtures with:

- reversed and randomly permuted ADR order;
- reversed findings and git path order;
- Windows and POSIX path separators;
- fixed evaluation dates;
- different process working directories;
- repeated warm execution;
- deleted caches and reconstructed caches.

Structured output must be byte-identical after normalization. Human output may
contain presentation differences only where explicitly documented.

## Robustness and security validation

- Corrupt ADR frontmatter.
- Dangling and cyclic links.
- Unknown lifecycle values.
- Missing git refs and detached HEAD.
- Renames, deletes, binary files, and large diffs.
- Concurrent guardian cache replacement.
- Interrupted lifecycle mutations.
- Prompt injection in source documents, PR bodies, titles, commit messages, and
  ADR prose.
- Newlines and GitHub command syntax in paths and findings.
- Shell metacharacters in suggested commands.
- Fork pull requests without secrets.
- Missing optional tools or network access.

Advisory surfaces fail open. Existing enforcement and explicit linked-Proposed
CI blocking fail according to their documented contracts.

## Performance certification

| Path | Fixture | Required result |
|---|---|---|
| Readiness core | 50 ADRs | warm p95 at most 100 ms |
| Single-ADR CLI | one ADR in 50-ADR repository | warm p95 at most 500 ms |
| All-Proposed CLI | 50 ADRs | warm p95 at most 1,000 ms; hard at most 2 seconds |
| Diff linkage | 500 paths and 50 ADRs | warm p95 at most 250 ms; hard at most 1 second |
| MCP adapter | same readiness fixture | at most 100 ms over core operation |
| Composite action | 500 paths and 50 ADRs | p95 overhead at most 5 seconds |
| SessionStart | repository fixture | p50 50 ms, p95 150 ms, hard 500 ms |
| Clean client generation | canonical artifacts | p95 2 seconds, max 5 seconds |
| Warm no-op generation | canonical artifacts | p95 500 ms, max 1 second, zero writes |

Each benchmark uses 30 warm certification samples. Reports include environment,
fixture size, median, p50, p95, maximum, and comparison to the current baseline.
CI variance may be at most 20%. No existing measured path may regress by more
than 20%.

## Cross-platform matrix

- Windows PowerShell.
- Linux Bash.
- macOS shell behavior where supported by the existing project.
- All Python versions declared by ADR Kit.
- Claude, Codex, and GitHub Copilot generated client artifacts.

## Epic release gate

The epic can be completed only when:

1. Every child task is Done with task-level evidence.
2. The full regression suite is green.
3. End-to-end lifecycle scenarios are green.
4. Deterministic outputs pass permutation validation.
5. All performance budgets pass.
6. Packaging and executable inventory pass.
7. Checked-in client artifacts match generated output.
8. Upgrade behavior from implicit `auto` to `assist` is documented and tested.
9. User documentation demonstrates a complete Proposed-to-Accepted interaction.
10. The parent task records the final commands, results, and release conclusion.
