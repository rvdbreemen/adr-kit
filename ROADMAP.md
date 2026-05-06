# adr-kit roadmap

This document captures the project's direction. It is not a contract, but a signal of where the maintainer wants the toolkit to go and which directions are deliberately *not* on the table. The goal is to make filtering decisions easy: contributions and issues that align with this roadmap are likely to land; those that do not are likely to be politely deferred.

## Status

`adr-kit` is in pre-1.0. The structure, file layout, and skill conventions are stable and in use, but may evolve before v1.0.0. Each release since v0.2.0 has been additive; we have not introduced a breaking change since the v0.2.0 plugin restructure.

If a breaking change becomes necessary before v1.0.0 (for example, renaming a default convention because of consistent user feedback), it will land as a minor bump (v0.x to v0.x+1), be called out in CHANGELOG, and include a migration note in the release.

## Toward v1.0.0

`v1.0.0` is the "this layout will not change again without a long deprecation window" signal. Criteria the maintainer wants to satisfy before tagging v1.0.0:

- 90 days of field time without a needed breaking change.
- At least 5 unrelated installations beyond the maintainer's own (signal: someone other than the author finds the toolkit useful).
- The four verification gates have been used to block at least one PR in real-world review (signal: the toolkit is being used as intended, not just installed).
- A migration guide for the v0.x to v1.0 transition is published in CHANGELOG, with the upgrade path tested on a non-trivial existing ADR set.

## Planned features (signals, not commitments)

These are likely additions in upcoming versions. Priority is shaped by user requests; a feature without a real-world ask may slip indefinitely.

- **Tier-2 chore**: branch protection on `main`, dependabot for the GitHub Actions workflow, release-drafter for auto-generated release notes, codespell in CI. Repo-automation polish that benefits maintainers more than users. Likely v0.8.0.
- **ADR query skill** (`/adr-kit:related ADR-XXX`): walks the `## Related Decisions` section across the ADR set and returns the dependency graph for a chosen ADR. Useful when an ADR is being superseded and you need to see who else points at it. Will land only if a real user asks for it; not auto-prioritised.
- **CI integration for `bin/adr-judge`**: a GitHub Actions snippet (mirroring the v0.10 `bin/adr-lint` snippet in README) that runs the judge against the diff produced by a PR. Local pre-commit only in v0.12; CI variant is v0.13+ if there is demand.
- **`pre-commit` framework support**: ship a `.pre-commit-hooks.yaml` so projects already using the `pre-commit` framework can register `adr-judge` without writing a native git hook. Native `.githooks/` is the only supported delivery in v0.12.

## Recently landed

- ✅ **Three-mode workflow** (v0.12.0, 2026-05-06): `/adr-kit:init` for one-shot project bootstrap (audit + ADR generation + pre-commit hook), pre-commit verification via `bin/adr-judge` against declarative `Enforcement` blocks, and on-demand `/adr-kit:judge` for in-session review. LLM judging stays in-session (no `claude -p` shell-out, no API key in the hook environment). Hook is default-on after init/upgrade. Backwards compatible: v0.11 users opt into the new layout via `/adr-kit:upgrade`.
- ✅ **Audit existing codebase** (v0.12.0, 2026-05-06): `bin/adr-audit` scans top-level config files and documentation for decision-shaped artefacts and emits a candidate list. The `/adr-kit:init` skill drives Claude through batched user-approval to convert candidates into Accepted ADRs.
- ✅ **ADR migration helper** (`/adr-kit:migrate`, v0.11.0, 2026-04-25): rewrites legacy-shaped ADRs into the canonical seven-section template. Read-then-confirm; never silent.

## Out of scope (deliberate non-goals)

These are choices the maintainer has already made. PRs proposing them will be politely declined unless the proposal includes a substantive new argument that has not been considered.

- **Multi-language support for skill bodies.** The skill prompts are English-only. A project's ADR template can be in any language the project chooses, but the skill instructions stay English to keep the agent-instruction surface small and easy to maintain. The patterns (anti-rationalization, four gates) are language-neutral; the wrapper around them is not.
- **ADR visualisation (graph rendering, diagrams).** Out of scope. If you need a graph, generate it from the `## Related Decisions` sections with a script in your project. The skill is markdown-shaped, not visualisation-shaped.
- **Bundling other plugins.** `adr-kit` is a single-purpose plugin: ADR creation, review, and lint. Cross-cutting governance (RFCs, design docs, lightweight specs) belongs in a separate kit if someone wants to write it. The maintainer is happy to link to such a kit, not to absorb it.
- **Anthropic-specific features.** The toolkit aims to work in Claude Code, Claude Cowork, Cursor, GitHub Copilot, and OpenAI Codex CLI. Features that only work in one tool are not accepted upstream unless they degrade gracefully on the others. The portable cp-based install path in INSTALL.md is the floor.
- **Heavy framework wrapping.** No build step, no compiled assets, no JavaScript runtime. The toolkit is markdown plus a JSON manifest. If a feature would require any of those, it is probably better as a separate project.

## How decisions get made

Decisions about `adr-kit` itself follow the same conventions and pass the same four verification gates that the toolkit asks of its users. The maintainer eats the dog food: significant changes to the plugin layout, default conventions, or user-visible behaviour are documented and reasoned about in PR descriptions before merging.

For substantial decisions, the PR description is structured as a mini-ADR (Status, Context, Decision, Alternatives Considered, Consequences). This is a guideline, not a rule. Tiny PRs (fix a typo, bump a date) do not need it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Project-specific examples should stay in your own copy of `SKILL.md`, not upstream. Generic improvements that benefit any user are welcome.

If you are unsure whether your idea fits the roadmap, open an issue using the feature-request template before writing a PR. The template asks for alternatives-considered, which is the same discipline the gates ask of an ADR; that filtering itself often clarifies whether the change belongs in the toolkit.
