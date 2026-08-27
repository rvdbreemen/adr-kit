# Security policy

## Scope

`adr-kit` is a local ADR lifecycle and enforcement toolkit. Its deterministic
default path is Python-stdlib-only and does not require an API key, but the
project is not documentation-only.

Security-relevant surfaces include:

- parsing repository-controlled ADRs, JSON configuration, regular expressions,
  Git diffs, paths, and hook payloads;
- pre-commit and CI enforcement that can allow or block a change;
- lifecycle, migration, setup, upgrade, index, hook, and generator workflows
  that write inside a project;
- installers that change Claude, Codex, and Copilot client state;
- optional LLM passes that launch a configured `claude` command and may send
  ADR/diff content to that provider.

Treat ADRs and `.adr-kit.json` as trusted repository policy, not as harmless
prose. The deterministic judge is a guardrail, not a sandbox or a substitute
for branch protection and code review. Current known limitations are recorded
in the [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md).

## Reporting a vulnerability

If you discover a security-relevant issue, please:

1. **Do not** open a public GitHub issue with exploit details.
2. Email the maintainer at <robert@vandenbreemen.net> with the subject line `adr-kit security: <short summary>`.
3. Include reproduction steps, the affected version (`adr-kit--vX.Y.Z`), and your proposed fix if you have one.

You will get an acknowledgement within 7 days. A fix and a coordinated disclosure timeline will follow.

If you are not sure whether something qualifies, email anyway. We would rather hear about a non-issue than miss a real one.

## Supported versions

Only the latest minor release line is supported with security fixes. Older versions get a fix only if the maintainer judges the impact severe enough.

This table names no version on purpose. A number written here is correct until
the next release and false afterwards, and a stale one tells a reporter that a
supported version is unsupported. Which line is current is answered by
[the latest release](https://github.com/rvdbreemen/adr-kit/releases/latest).

| Version | Status |
|---|---|
| The latest minor release line | Supported. |
| Every earlier minor line | No routine security backports. |

## Acknowledgement

Reporters who follow this policy will be credited in the release notes of the fix release, unless they prefer to remain anonymous.
