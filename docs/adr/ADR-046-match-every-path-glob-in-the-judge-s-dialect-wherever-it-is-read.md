---
id: "ADR-046"
title: "Match every path_glob in the judge's dialect wherever it is read"
status: "Proposed"
date: "2026-10-11"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "path_glob"
  - "glob dialect"
  - "scope matching"
  - "context injection"
aliases:
  - "fnmatch"
  - "glob_to_regex"
  - "brace expansion"
  - "**/*.py"
components:
  - "bin/adr-judge"
  - "bin/adr_query.py"
  - "hooks/adr_hook_core.py"
symbols:
  - "glob_to_regex"
  - "fnmatchcase"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-046 Match every path_glob in the judge's dialect wherever it is read

## Status

Proposed, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Claude"
    reason: Initial proposal
    changed_via: adr-kit
```

## Context and Problem Statement

ADR-004 section 3 pins the Enforcement `path_glob` as the canonical scope field
for the injector, the index and the judge. ADR-014 keeps it as "the sole
path-scope authority". The field is read in two dialects.

**The judge** uses `glob_to_regex` (`bin/adr-judge:672-738`), whose docstring
states the dialect:

| Glob | Meaning |
| --- | --- |
| `*` | stays inside one path segment |
| `**/` | zero or more directories, so `**/*.py` includes a top-level file |
| `?` | one character inside a segment |
| `{a,b}` | alternatives, not nested |
| `[` | literal |

Matching is case-sensitive. Brace support arrived in v0.12.2 because, as the
docstring records, without it "real-world Enforcement-block path_globs that
scope to a list of source files silently match nothing".

**The injection hooks and the query engine** use `fnmatch.fnmatchcase` on
casefolded strings (`hooks/adr_hook_core.py:661,708`, `bin/adr_query.py:300`).
There, `*` crosses `/`, braces do not exist, `**/` needs at least one slash, and
matching is case-insensitive.

The 2026-10-11 defect sweep (TASK-222) measured the gap against commit
`f2f6fe2`:

| Glob, path | Hook injects | Judge enforces |
| --- | --- | --- |
| `src/**/*.{ino,cpp,h}`, `src/net/main.cpp` (the guide's own example) | no | yes |
| `**/*.py`, `app.py` | no | yes |
| `src/*.py`, `src/pkg/deep.py` | yes | no |
| `src/**`, `SRC/upper.py` | yes | no |

In the first two rows the agent is never told about a decision that will refuse
its commit. In the last two it is told that a decision binds a file the floor
will never check. The brace regression that v0.12.2 fixed in the judge is
present in the injector.

Which dialect is authoritative, and where is it implemented?

## Decision Drivers

* One field has one meaning (ADR-004 section 3; ADR-014).
* The fail-closed floor is the authority. The injector may not claim a binding
  that the floor will not enforce, nor stay silent about one it will.
* Existing Enforcement blocks keep their enforced meaning, because users' CI
  depends on it.
* Matching stays within the latency budgets (ADR-015, ADR-030).

## Considered Options

* The judge's dialect everywhere, through one shared module.
* `fnmatch` everywhere.
* Keep both dialects, and let lint warn where they differ for a given glob.
* Do nothing.

## Decision Outcome

Chosen option: **the judge's dialect everywhere, through one shared module**,
because the judge is the authority whose verdict users already depend on.
Moving the injector to that meaning changes only what the agent is told, and
corrects it.

* One module implements the dialect. The judge, the index, the query engine and
  every hook import it.
* Paths are matched in their repository-relative POSIX form, as git records
  them, and case-sensitively on every platform. A hook first maps the editor's
  path to git's recorded spelling, so a different spelling on a
  case-insensitive filesystem does not miss injection (Open Question 2).
* `[` and `]` are literal, as the judge treats them today, so
  `app/[id]/page.tsx` matches the route a Next.js, Nuxt or SvelteKit project
  means (Open Question 3).
* For one minor release, lint reports an advisory for every glob whose matches
  differ between the old injector semantics and the dialect, so a project can
  see what moved.

**Proposed by:** Claude (agent) at the request of User: Robert van den Breemen,
from the 2026-10-11 defect sweep. **Decision Maker:** User: Robert van den
Breemen settled all three human decisions on 2026-10-11:

* The judge's dialect is authoritative.
* Matching is case-sensitive on git's recorded path.
* Brackets stay literal. This last answer went against the agent's first
  recommendation, after the agent found that framework route paths use literal
  brackets and that none of the 26 path_globs in this repository uses a
  character class.

### Confirmation

* One glob matrix is asserted against the judge, the query engine and the edit
  hook, and all three agree on every row. It holds the four rows above, plus
  braces, `?`, nested `**`, a case variant, an editor path spelled with
  different case on a case-insensitive filesystem, and a literal
  `app/[id]/page.tsx`.
* The sweep check DEF-10 reports `reproduced=False`.
* Each project's `adr-context --check-probes` stays green, and the latency tests
  pass.

## Decision Contract

### Must

* Every reader of `path_glob` matches through the shared module.
* The dialect is the one stated in this record and tested by one matrix.
* A hook maps the editor's path to git's recorded spelling before it matches.

### Must Not

* Match a `path_glob` with `fnmatch` or any second implementation.
* Change the set of files the judge enforces for an existing glob. The answers
  to Open Questions 2 and 3 keep the judge's current behaviour.
* Treat `[` or `]` as a character class.

### Exceptions

* None.

### Verification

* `tests/test_glob_dialect.py`, added with the implementation, run against all
  readers.

## Consequences

### Positive

* The injected context and the commit verdict agree on scope.
* The guide's own brace example works for injection again.

### Negative

* Some ADRs stop being injected for paths that `fnmatch` used to match. That is
  intended, because the floor never enforced them there. Mitigation: the
  one-release lint advisory.
* The index format may need a version bump if it stores pre-matched scopes.

## Pros and Cons of the Options

### The judge's dialect everywhere

* Good, because enforcement does not change, and injection becomes truthful.
* Bad, because injection changes for globs that relied on `*` crossing `/`.

### `fnmatch` everywhere

* Good, because it is the standard library.
* Bad, because it changes what the floor enforces: braces stop working, which
  repeats the pre-v0.12.2 regression.

### Keep both, and let lint warn

* Good, because nothing moves.
* Bad, because one field keeps two meanings, and the warning addresses authors
  rather than the agent being misled.

### Do nothing

* Good, because nothing changes.
* Bad, because the measured gap stays.

## Open Questions

- [x] Is the judge's dialect the authoritative one, so the injector, index and query engine adopt it through one shared module (recommended)? — **Answered 2026-10-11 by User: Robert van den Breemen:** The judge's dialect is authoritative. One shared module implements it, and the judge, the index, the query engine and every hook import it. What the floor enforces does not change; what the agent is told changes, and becomes correct. For one minor release, lint reports an advisory for every glob whose injection moves.
- [x] Is matching case-sensitive on every platform, as git's paths are (recommended), or case-insensitive on Windows and macOS? — **Answered 2026-10-11 by User: Robert van den Breemen:** Case-sensitive everywhere, matched against the path as git records it. The hook first maps the editor's path to that form, so a different spelling on a case-insensitive filesystem (macOS, Windows) does not miss injection. The verdict is the same on every platform, and what the judge enforces does not change.
- [x] Are character classes such as [ab] part of the dialect, matching within one segment (recommended), or do they stay literal as the judge treats them today? — **Answered 2026-10-11 by User: Robert van den Breemen:** Literal. [ and ] stay literal characters, as the judge treats them today, so a glob such as app/[id]/page.tsx matches exactly the route a Next.js, Nuxt or SvelteKit project means. This reverses the recommendation printed in this question: none of the 26 path_globs in this repository uses a character class, and framework route paths use literal brackets. What the judge enforces does not change; only injection moves off fnmatch's class meaning.

## Related Decisions

* Makes ADR-004 section 3 precise (Layered ADR context injection): the
  canonical scope field gets one canonical meaning.
* ADR-014 (Use the generated ADR graph as the selective-context query engine):
  `path_glob` remains the sole path-scope authority.
* ADR-015 and ADR-030: the latency budgets the shared module must meet.

## References

* `bin/adr-judge:672-738` (`glob_to_regex` and its docstring).
* `hooks/adr_hook_core.py:661`, `:708`; `bin/adr_query.py:300`.
* `templates/adr-kit-guide.md` (the `src/**/*.{ino,cpp,h}` example).
* 2026-10-11 defect sweep (TASK-222): DEF-10.
