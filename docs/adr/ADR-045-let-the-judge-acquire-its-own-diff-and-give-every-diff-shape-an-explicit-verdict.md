---
id: "ADR-045"
title: "Let the judge acquire its own diff and give every diff shape an explicit verdict"
status: "Accepted"
date: "2026-10-11"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-004"
  - "ADR-023"
  - "ADR-044"
topics:
  - "diff acquisition"
  - "renamed files"
  - "binary files"
  - "deleted files"
  - "fail closed"
aliases:
  - "Binary files differ"
  - "git mv bypass"
  - "diff.external"
  - "color.ui"
  - "--no-ext-diff"
components:
  - "bin/adr-judge"
  - "templates/githooks/pre-commit"
  - "hooks/adr_pr_guard.py"
  - ".github/actions/adr-judge/action.yml"
symbols:
  - "parse_diff"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-045 Let the judge acquire its own diff and give every diff shape an explicit verdict

## Status

Accepted, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Claude"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-004
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-023
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-044
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

The judge decides from a unified diff that someone else produced.

* **Ten call sites produce it.** They include the pre-commit hook
  (`templates/githooks/pre-commit:269`), `bin/adr-judge-precommit:58`, the
  pull-request guard (`hooks/adr_pr_guard.py:259`), the CI action
  (`.github/actions/adr-judge/action.yml:97`) and three skills.
* **Each runs with the user's porcelain git configuration**, and they disagree
  on flags. Only `bin/adr-audit:173` passes `--no-color`, and only
  `bin/adr-grill-signal:57` passes `-M`.
* **`parse_diff` (`bin/adr-judge:598`) understands only uncoloured text
  hunks** behind `a/` and `b/` headers. Anything else yields zero files, and
  zero files reads as "no violations".

The 2026-10-11 defect sweep reproduced this against commit `f2f6fe2`
(TASK-222). Each violating commit below went through the installed hook:

| Case | Result |
| --- | --- |
| `color.ui=always`, `diff.mnemonicPrefix=true`, or `diff.external=<script>` (the difftastic setup) | committed (exit 0); `diff.noprefix=true` is handled (exit 1) |
| `git mv scratch/x.py src/x.py` with `eval(` in the file | committed; the same file added rather than moved is refused |
| a file under a `-diff` attribute, or containing a NUL byte | `forbid_pattern` skipped, committed |
| a new file without the required text, containing a NUL byte | `require_pattern` skipped, committed |
| deleting a compliant file under a `require_pattern` | refused |

The guide says: "A deleted or unstaged file, and an unreadable or unsafe path,
still fail closed" (`templates/adr-kit-guide.md:145`). The fourth row
contradicts the second half of that sentence: the binary file is skipped, not
refused. The fifth row is the first half, working as documented, which means a
legitimate deletion needs an override.

What diff does the judge see, and what verdict does each shape of change get?

## Decision Drivers

* The verdict must not depend on a user's git configuration.
* The fail-closed floor (ADR-004) holds for every shape of change, not only for
  modified text.
* A refusal must be satisfiable by editing the change (the reasoning of
  ADR-009).
* An operation that cannot violate a rule, such as deleting a file, must not
  need an override.
* One invocation, defined once and tested for equality at every call site.

## Considered Options

* The judge owns one canonical diff invocation, and every diff shape gets an
  explicit verdict.
* Keep the user's diff and teach the parser colours, prefixes and external
  formats.
* Document the git configuration the judge requires.
* Do nothing.

## Decision Outcome

Chosen option: **the judge owns one canonical diff invocation, and every diff
shape gets an explicit verdict**, because a parser cannot recover what an
external diff tool or a binary marker never printed. Taking control of the input
is the only option that closes the class rather than its current members.

1. **One invocation.** It is defined once in a shared module and mirrored by the
   shell template:
   `git diff --no-color --no-ext-diff --src-prefix=a/ --dst-prefix=b/ --unified=0 --no-renames --text`,
   plus `--cached` or the range each site needs. The MCP `adr_judge` tool
   receives its diff from the client; for that path, item 3 applies, and the
   tool description names the canonical flags.
2. **One verdict per shape.**
   * Added or modified text: unchanged.
   * Renamed: judged as a deletion plus an addition, so moved content is judged
     against the rules of its destination path (Open Question 1).
   * Binary to git, through a `-diff` attribute or a NUL byte: diffed as text.
     A binary marker that still reaches the parser for a governed path is
     refused with a named reason (Open Question 2).
   * Deleted: complies with a `require_pattern`, because nothing remains to
     violate. A rule whose files must keep existing declares
     `"must_exist": true`, and that rule refuses the deletion. The new key
     extends the Enforcement schema and the policy gate, and
     `templates/adr-kit-guide.md:145` changes with it (Open Question 3).
3. **An unreadable diff fails closed.** The parser refuses, with exit 2 and a
   named reason, a non-empty diff that yields no files, and any hunk it cannot
   parse. The principle was settled in ADR-044's Open Question 1 (answered
   2026-10-11 by User: Robert van den Breemen): when the floor cannot reach a
   verdict in a project with Accepted enforcement, it refuses.

**Proposed by:** Claude (agent) at the request of User: Robert van den Breemen,
from the 2026-10-11 defect sweep. **Decision Maker:** User: Robert van den
Breemen settled all three human decisions on 2026-10-11, taking the recommended
option each time. Moved content is judged at its destination, binary-marked
content is judged as text, and a deletion complies unless the rule declares
`must_exist`. The principle behind item 3 came from ADR-044's Open Question 1.

### Confirmation

* A git-configuration matrix (`color.ui`, `diff.mnemonicPrefix`,
  `diff.noprefix`, `diff.external`, `diff.renames`, `core.quotePath`) through
  the real hook gives the same verdict as the default configuration.
* A rename, a `-diff` file, a NUL-byte file, a deletion, and a deletion under a
  `must_exist` rule each get the verdict above.
* A guard test asserts that every call site uses the shared invocation.
* The sweep checks DEF-03, DEF-04 and DEF-05 report `reproduced=False`.

## Decision Contract

### Must

* Every call site that feeds the judge uses the shared invocation.
* The parser refuses, with a named reason, input that it cannot attribute to
  files.
* Each diff shape has the verdict stated above, with a test for each.
* A `require_pattern` rule with `"must_exist": true` refuses the deletion of a
  file it governs, and the policy gate accepts the key only on
  `require_pattern` rules.

### Must Not

* Let a user's `color.ui`, `diff.external`, `diff.mnemonicPrefix`,
  `diff.renames` or `diff` attribute change a verdict.
* Report "no violations" for a non-empty diff that the parser could not read.

### Exceptions

* `--max-diff-bytes` and `judge.max_diff_bytes` still bound the input. A diff
  over the budget is refused as it is today.

### Verification

* `tests/test_judge_diff_acquisition.py`, added with the implementation.
* A guard test over the ten call sites.

## Consequences

### Positive

* The verdict is a function of the change, not of the person's git
  configuration.
* Moves, binary-marked files and deletions get a stated, tested verdict instead
  of an accidental one.

### Negative

* Moving a file that already violates a rule into a governed path is now
  refused. Mitigation: the refusal names the rule and the destination, and the
  release notes call it out.
* Binary content scanned as text can, rarely, match a `forbid_pattern`.
  Mitigation: `path_glob` scoping, and the existing override.
* The release is a minor version bump, because users' CI can observe the change.

## Pros and Cons of the Options

### The judge owns one canonical invocation

* Good, because it closes the class: the parser only ever sees one format.
* Bad, because ten call sites and the MCP tool's contract change together.

### Teach the parser every format

* Good, because no call site changes.
* Bad, because `diff.external` output has no fixed format, and a binary marker
  carries no content to judge.

### Document the required git configuration

* Good, because it costs nothing.
* Bad, because enforcement would depend on every contributor reading the
  documentation.

### Do nothing

* Good, because nothing changes.
* Bad, because difftastic users, renames and binary-marked files keep passing
  the floor.

## Open Questions

- [x] Is a renamed file judged as new content at its destination (recommended), so that moving a file into a governed path is refused when it already violates a rule there? — **Answered 2026-10-11 by User: Robert van den Breemen:** Judged as new content at its destination: the canonical invocation uses --no-renames, so moving a file that already violates a rule into a governed path is refused. This closes the two-step bypass of DEF-04 (commit outside the governed path, then git mv in). A refactor that carries old violations along fixes them first or uses the existing override.
- [x] For a file git treats as binary under a governed glob: is its content judged as text (recommended), is it refused with a named reason, or does it produce only an advisory? — **Answered 2026-10-11 by User: Robert van den Breemen:** Judged as text: the canonical invocation uses --text, so forbid rules scan files behind a -diff attribute or with a NUL byte like any other file, and a require rule on genuinely binary content fails closed, as templates/adr-kit-guide.md:145 already promises. A binary marker that still reaches the parser for a governed path is refused with a named reason. path_glob scoping bounds the rare false positive.
- [x] Does deleting a file under a require_pattern comply (recommended: yes; a rule that needs a file to exist says so), or does it stay refused as documented today? — **Answered 2026-10-11 by User: Robert van den Breemen:** Deleting a file under a require_pattern complies, because nothing remains to violate. A rule that needs its files to keep existing says so with a new rule key, must_exist: true, and that rule refuses the deletion; this extends the Enforcement schema and the policy gate. templates/adr-kit-guide.md:145 changes with it.

## Related Decisions

* ADR-004 (Layered ADR context injection): the fail-closed floor this makes
  independent of the diff's producer.
* ADR-044 (Resolve the interpreter and the engine through one resolver at every
  entry point): its Open Question 1 settles whether the floor refuses when it
  cannot reach a verdict.
* ADR-023 (Record the pull-request guard as a fail-closed tier): the guard is
  one of the call sites.
* ADR-009 (Bound heuristic gates to findings an author can act on): a refusal
  must be satisfiable by editing the change.

## References

* `bin/adr-judge:598` (`parse_diff`); `bin/adr-audit:173`;
  `bin/adr-grill-signal:57`.
* `templates/githooks/pre-commit:269`, `:343`; `bin/adr-judge-precommit:58`;
  `hooks/adr_pr_guard.py:259`; `.github/actions/adr-judge/action.yml:97`.
* `templates/adr-kit-guide.md:145`.
* 2026-10-11 defect sweep (TASK-222): DEF-03, DEF-04, DEF-05, DEF-13.
