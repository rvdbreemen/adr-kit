---
id: TASK-192
title: This repository's own .adr-kit/ADR-guide.md is stamped v0.35.0 and unmanaged
status: To Do
assignee: []
created_date: '2026-08-26 19:46'
labels: []
dependencies: []
references:
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
  - packaging/version-sites.json
  - templates/adr-kit-guide.md
priority: low
type: bug
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`.adr-kit/ADR-guide.md` is git-tracked in this repository and its first line reads `<!-- adr-kit-guide v0.35.0 -->`. The project ships 0.55.1, so the guide this repository dogfoods is twenty minor versions behind whatever the current template says.

WHY THE OBVIOUS FIX IS THE WRONG ONE. `packaging/version-sites.json` already declares `templates/adr-kit-guide.md` for its stamp, so adding `.adr-kit/ADR-guide.md` alongside it looks like a one-line change. It is not: the two files are different documents, not copies.

```
.adr-kit/ADR-guide.md        104 lines, header "Generated ADR Kit guidance.
                             Local additions belong in .adr-kit/ADR-guide.local.md."
templates/adr-kit-guide.md   357 lines, header "Canonical project-side ADR guide."
```

Bumping the stamp alone would put a fresh version number over stale content, which is worse than the current honest lag: right now the number tells you the content is old, and after a naive bump it would not.

PRECEDENT THAT SAYS THIS IS A REAL GAP RATHER THAN BY DESIGN. `.githooks/pre-commit` IS declared in the registry, with the label "own pre-commit wrapper stamp (this repo dogfoods the template)". The project therefore already treats its own dogfood copies as version sites. This one was left out.

WHAT AN IMPLEMENTER NEEDS TO ESTABLISH FIRST, before choosing a fix: which tool writes `.adr-kit/ADR-guide.md`. The header says "Generated", so something produces it - most likely an install, upgrade or setup workflow. If that generator runs from the template, the fix is to re-run it and then decide whether the output belongs in the registry at all. If nothing regenerates it any more, the file is an orphan and the question is whether it should be tracked.

Found during the documentation sweep of TASK-190, which deliberately left it out of scope for exactly this reason: it is not a stale string, it is an unowned artefact.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The tool that produces .adr-kit/ADR-guide.md is identified by name, or the file is established to be an orphan
- [ ] #2 The file's content matches what its generator currently produces, rather than only its version stamp being updated
- [ ] #3 If the file stays tracked, it is either declared in packaging/version-sites.json or the record states why a dogfood copy is exempt where .githooks/pre-commit is not
- [ ] #4 python scripts/check-release-version.py --expect v0.55.1 still passes
<!-- AC:END -->
