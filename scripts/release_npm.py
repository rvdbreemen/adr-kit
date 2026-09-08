#!/usr/bin/env python3
"""The one step of a release npm will not let any tool finish.

npm requires proof of presence to publish, so a staged package waits for the
maintainer's 2FA no matter what drives the release. That makes this the seam
between what ADR-042 automates and what it deliberately leaves to a person,
which is why it is its own module rather than an eighth entry in PHASES.

The distinction the rest of the driver depends on is between a version that is
still staged and a version that is published while `latest` names an older
release. From outside they look the same - `npm install` gives you the wrong
package either way - but only the second is a fault, and only the second has a
remedy the maintainer can apply without npm's approval flow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_shell import PACKAGE, Context, run  # noqa: E402


DONE = "done"
WRONG_LATEST = "wrong-latest"
STAGED = "staged"
UNREACHABLE = "unreachable"


def _dist_tags(ctx: Context) -> dict | None:
    """None means npm did not answer, which is not the same as an empty answer."""
    code, out, _ = run(["npm", "view", PACKAGE, "dist-tags", "--json", "--prefer-online"])
    if code != 0:
        return None
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def npm_state(ctx: Context) -> str:
    """Which of the four things npm is currently doing about this version.

    Deciding this in one place is what keeps the driver's report and its exit
    code from disagreeing, which is the defect this function replaced: the
    predicate existed and nothing wired it to a failure.

    A registry that does not answer gets its own state rather than being folded
    into one of the others. Reporting "awaiting your 2FA" because npm was down
    would be a guess presented as a reading, and it is the reading a maintainer
    would act on.
    """
    tags = _dist_tags(ctx)
    if tags is None:
        return UNREACHABLE
    if tags.get("latest") == ctx.version:
        return DONE
    return WRONG_LATEST if npm_published(ctx) else STAGED


def npm_published(ctx: Context) -> bool:
    """Is the version on the registry at all, whatever `latest` points at?

    This separates the two npm states that look identical from outside. A
    version still staged is a release waiting on the maintainer's 2FA, which is
    the normal end of a release rather than a fault. A version that IS
    published while `latest` names an older release is the v0.55.1 defect:
    `npm install` quietly serves the wrong package. Only the second is a
    failure, and telling the maintainer to go and approve something that is
    already approved sends them to the one place that cannot fix it.
    """
    code, out, _ = run(["npm", "view", PACKAGE, "versions", "--json", "--prefer-online"])
    if code != 0:
        return False
    try:
        versions = json.loads(out)
    except json.JSONDecodeError:
        return False
    if isinstance(versions, str):  # npm returns a bare string for a lone version
        versions = [versions]
    return isinstance(versions, list) and ctx.version in versions


def npm_wrong_latest(ctx: Context) -> str:
    latest = (_dist_tags(ctx) or {}).get("latest") or "nothing this driver could read"
    return (
        f"{ctx.version} is published on npm, but `latest` names {latest}.\n\n"
        f"`npm install {PACKAGE}` therefore serves {latest} rather than the "
        f"release. npm sets `latest` to the version published LAST, not the "
        f"highest, so approving staged versions out of order does exactly "
        f"this. It left 0.55.1 released while `latest` read 0.54.0 for a "
        f"week, and nothing surfaced it.\n\n"
        f"    npm dist-tag add {PACKAGE}@{ctx.version} latest\n"
        f"    npm dist-tag ls {PACKAGE}   # latest must read {ctx.version}\n\n"
        f"Read the first command's own exit code. Piping it into `tail` "
        f"reports tail's status instead, and npm's failure disappears."
    )


def npm_instructions(ctx: Context) -> str:
    return (
        f"The OpenCode package for {ctx.tag} is STAGED, not published. npm "
        f"requires proof of presence, so no tool can finish this.\n\n"
        f"    npm login\n"
        f"    npm stage list {PACKAGE}\n"
        f"    npm stage view <stage-id>      # inspect the tarball first\n"
        f"    npm stage approve <stage-id>   # prompts for your OTP\n\n"
        f"    or from the browser: https://www.npmjs.com/staged-packages\n\n"
        f"If more than one version is staged, approve them in ASCENDING order. "
        f"npm sets `latest` to the version published LAST, not the highest. On "
        f"2026-08-26 approving 0.55.1, then 0.53.0, then 0.54.0 left `latest` on "
        f"0.54.0 while 0.55.1 was the release.\n\n"
        f"    npm dist-tag ls {PACKAGE}   # latest must read {ctx.version}"
    )
