---
id: TASK-92
title: >-
  Supersede ADR-018: embed the query where it is asked, and read authority from
  the index
status: To Do
assignee: []
created_date: '2026-08-03 19:30'
labels:
  - adr
  - retrieval
  - decision
dependencies: []
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-018's Decision Contract carries two clauses that block the read path it promises, and one assumption that is false.

**Clause that blocks.** Must: "Compute embeddings only in an explicit build step, never during a query or a hook." Must Not: "Call an embedding model, a language model, or any network endpoint from the hook path." Semantic retrieval is a comparison between two vectors; a path that may not produce the query vector cannot do semantic retrieval at all. `bin/adr-embed:183` calls `backend.embed()` on the query, which is why only the standalone diagnostic works and the hook path never reaches vectors.

**Assumption that is false.** ADR-018 says a content-hash mismatch marks the store stale, but `embed_text` hashes title, topics, aliases, components and decision — and a supersession never edits Decision. Reproduced twice independently: present the same record as Superseded with `superseded_by` set, and `staleness()` returns `stale: False` while `search()` returns status `Accepted`, authority `governing`, `superseded_by` None. `adr-embed status` would call the store current. `bin/adr-embed:42-46` filters only on `adr_id` presence, so a rebuild would not report the entry as removed either.

**Decided (maintainer, 2026-08-03).** Embedding the query is allowed in a query step and in a hook; the corpus stays a build step. Authority — status and `superseded_by` — is re-joined from `ADR-INDEX.json` at search time and never read from the frozen copy. The vectors find; the index decides.

One successor supersedes ADR-018 and carries both, because they are one insight about where each fact lives. Write the ADR before either implementation task starts.

Spec: R6.1 (rewritten 65c8d8a), R10, R7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A new ADR supersedes ADR-018 and states both changes: the query may be embedded in a query step and in a hook, and authority is joined from ADR-INDEX.json at search time
- [ ] #2 The Decision Contract names the three properties that keep query-time embedding honest: inside R21's ceiling, fail-soft to lexical with the route named in the output, and the local runtime of R16 as the default backend
- [ ] #3 The Consequences state plainly that the hot path now depends on a reachable embedding backend, and what happens when it is not
- [ ] #4 Both sides of the supersession are written by `bin/adr supersede`, never by hand
- [ ] #5 The ADR is Proposed until the maintainer accepts it; the agent does not self-approve
<!-- AC:END -->
