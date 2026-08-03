---
name: audit
description: "Are we still on course? Lint the decisions and judge the code in one run. Use for ADR audit, architecture drift, a whole-codebase compliance check, or a governance report. Read-only."
argument-hint: "[--whole-codebase | a diff path; defaults to the working tree]"
allowed-tools: [Read, Bash, Glob, Grep]
---

# ADR Audit

Use `$ARGUMENTS` to pick the scope. Empty means the whole codebase, because
that is the question people mean when they ask whether the project is still on
course. Read-only: this skill reports, it never edits an ADR or a source file.

## Why one command for two questions

Two answers are needed and either one alone is misleading:

- **Are the decisions any good?** A clean judge over vague ADRs proves nothing,
  because a vague rule cannot be violated.
- **Does the code obey them?** A sharp ADR set nobody checks the code against is
  documentation, not governance.

`bin/adr-audit` runs `adr-lint` and `adr-judge` together so the caller does not
have to know the answers come from two binaries.

## Run it

```bash
# The whole codebase: every tracked file judged as if newly added, so forbid
# rules reach code no recent diff touched.
"$ADR_KIT/bin/adr-audit" --whole-codebase --adr-dir docs/adr --repo-root .

# A specific diff: the hook and pull-request case.
git diff --unified=0 origin/main...HEAD | "$ADR_KIT/bin/adr-audit" --diff -

# Machine-readable, for a CI job or another tool.
"$ADR_KIT/bin/adr-audit" --whole-codebase --format json
```

Add `--llm` to include the judge's LLM pass for `llm_judge` ADRs. It costs
money and time proportional to the number of opted-in ADRs, so confirm with the
user before adding it — never on your own initiative.

## Read the exit code before you read the output

The two failures have different owners, so they have different codes:

| Exit | Meaning | Who fixes it |
|---|---|---|
| 0 | on course | nobody |
| 1 | the code violates an Accepted ADR | the author of the code, or supersede the decision |
| 3 | the ADR set fails its own gates | the author of the records |
| 4 | both | both, and report them separately |
| 2 | the audit could not run | tooling or configuration; it did **not** answer "no" |

Never collapse 1 and 3 into "the audit failed". Say which one, and to whom it
belongs. Exit 2 is not a finding: report that the audit could not run and why,
and do not present its silence as a pass.

## Responding to findings

- **Code violations** — cite ADR, file and line. Offer to fix the code, or, if
  the decision itself is what is wrong, to supersede it with `/adr-kit:adr`.
  Never work around an Accepted ADR silently.
- **ADR-quality failures** — name the failing gate, not just the ADR. Offer
  `/adr-kit:grill ADR-NNN` for a Proposed record. An Accepted record's body is
  immutable: the honest routes are a supersession or a retirement, never a
  rewrite.
- **Whole-codebase mode surfacing old violations** — expected and worth saying
  plainly. A rule added after a file was written has never been applied to that
  file. Offer a remediation task rather than a large unrequested edit.

## Where it fits

- `/adr-kit:judge` judges one staged diff at commit time. Narrower and faster.
- `/adr-kit:lint` checks the records alone.
- `/adr-kit:guardian` runs a version of this combination on a cadence.
- `/adr-kit:audit` is the on-demand form a person, a hook or a CI job can
  simply demand, and the only one that reaches code no diff has touched.

`bin/adr-discover` is a different thing despite the old name: it is the init
scanner that looks for decision-shaped artefacts. It does not audit anything.
