"""Helpers for tests that borrow a real ADR as a fixture.

Borrowing a shipped record keeps a fixture realistic: it carries the same
frontmatter, the same section set and the same prose shape the tool actually
meets. The cost is that the copy inherits the record's cross-references, and a
cross-reference only resolves inside the full directory. Copy such a record
into a temporary directory on its own and the consistency gate correctly
reports a dangling link -- a failure about the fixture, not about the behaviour
under test.

This has now bitten twice. ADR-028 records the first time, when a clarity test
ran acceptance gates over a borrowed ADR-007 and broke the moment that record
gained a `related` link. The second time was ADR-020 gaining `supersedes:
["ADR-018"]` at acceptance, which broke five tests across two modules that had
nothing to do with supersession.

`isolated_copy` is the fix for the class: neutralise exactly the fields whose
meaning depends on the neighbours the copy does not have.
"""

from __future__ import annotations

import re


#: Frontmatter keys that name another record. Inside `docs/adr` they resolve;
#: inside a one-file temporary directory they cannot, by construction.
_CROSS_REFERENCE_KEYS = ("supersedes", "superseded_by", "related")


def isolated_copy(text: str) -> str:
    """Return `text` with its cross-references emptied, for a lone-file fixture.

    Only frontmatter is touched. Prose references stay: they are what the record
    says, they are not resolved by any gate, and rewriting them would change the
    document under test. That split is ADR-028's decision, applied here.
    """
    match = re.match(r"^---\n(.*?\n)---\n", text, re.S)
    if match is None:
        return text

    frontmatter = match.group(1)
    for key in _CROSS_REFERENCE_KEYS:
        # A list value spans the lines that follow it, so consume them too.
        frontmatter = re.sub(
            rf"^{key}:.*(?:\n[ \t]+[-\S].*)*$",
            f"{key}: null" if key == "superseded_by" else f"{key}: []",
            frontmatter,
            count=1,
            flags=re.M,
        )
    return text[: match.start(1)] + frontmatter + text[match.end(1) :]
