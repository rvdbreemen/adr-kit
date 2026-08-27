#!/usr/bin/env python3
"""Drive a release end to end, leaving only what a person must do.

ADR-042: the release runs from the maintainer's machine, with the maintainer's
own credentials, because GitHub does not start workflow runs for events caused
by GITHUB_TOKEN - a pull request a workflow opens never receives the checks
`main` requires, so it can never merge. The tag is not typed here either:
`release-publish.yml` creates it from the merged commit and publishes in the
same run, and this driver only verifies that it landed where it belongs.

What stays human: deciding to release and choosing the version, writing the
release notes, approving the merge, and npm's 2FA. Everything between those is
mechanical, and mechanical steps performed by hand are what cost v0.55.0 and
left three npm versions unapproved for a week.

Safe to re-run. Each phase asks the repository whether its work is already
done, so an interrupted release is resumed rather than restarted:

    python scripts/release.py 0.57.0
    python scripts/release.py 0.57.0 --skip-tests     # CI still runs them
    python scripts/release.py 0.57.0 --status         # what is left, changing nothing
    python scripts/release.py 0.57.0 --only prepare   # one phase

docs/RELEASING.md is the specification; the phases mirror its steps in order.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_npm import (  # noqa: E402
    DONE,
    STAGED,
    UNREACHABLE,
    WRONG_LATEST,
    npm_instructions,
    npm_state,
    npm_wrong_latest,
)
from release_phases import PHASES, Context, ReleaseError  # noqa: E402

NPM_LABEL = {
    DONE: "done",
    WRONG_LATEST: "PUBLISHED, but `latest` names another version",
    STAGED: "awaiting your 2FA",
    UNREACHABLE: "npm did not answer; run this again",
}

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _say(text: str = "") -> None:
    print(text, flush=True)


def _status(ctx: Context) -> int:
    _say(f"Release {ctx.tag}: what each phase reports about the repository now.")
    _say()
    for phase in PHASES:
        try:
            state = "done" if phase.done(ctx) else "to do"
        except ReleaseError as exc:  # a phase that cannot even answer
            state = f"unknown ({exc})"
        _say(f"  step {phase.step}  {phase.name:<10} {state}")
    _say(f"  step 3a  npm        {NPM_LABEL[npm_state(ctx)]}")
    _say()
    _say("Nothing was changed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="release version, for example 0.57.0")
    parser.add_argument(
        "--only",
        choices=[phase.name for phase in PHASES],
        help="run a single phase, skipping the done-check for it",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="report what each phase would do and change nothing",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="skip the local pytest run; the pull request still runs it in CI",
    )
    parser.add_argument(
        "--timeout-min",
        type=int,
        default=45,
        help="how long to wait for a merge or for the publish workflow (default 45)",
    )
    args = parser.parse_args(argv)

    version = args.version.lstrip("vV").strip()
    if not SEMVER.match(version):
        parser.error(f"not a MAJOR.MINOR.PATCH version: {args.version!r}")

    ctx = Context(
        version=version,
        skip_tests=args.skip_tests,
        timeout_min=args.timeout_min,
    )

    if args.status:
        return _status(ctx)

    phases = [p for p in PHASES if p.name == args.only] if args.only else list(PHASES)
    _say(f"Releasing {ctx.tag}. Re-running this command is safe; finished phases are skipped.")
    _say()

    for phase in phases:
        label = f"step {phase.step}  {phase.name}"
        if not args.only and phase.done(ctx):
            _say(f"  {label:<22} already done")
            continue
        _say(f"  {label:<22} running")
        try:
            for note in phase.run(ctx):
                _say(f"      {note}")
        except ReleaseError as exc:
            _say()
            _say(f"Stopped in {phase.name}:")
            _say()
            _say(str(exc))
            _say()
            _say("Nothing after this phase ran. Fix the above and run the same "
                 "command again; the phases that finished will be skipped.")
            return 1

    _say()
    state = npm_state(ctx)

    if state == DONE:
        _say(f"npm already serves {ctx.version} as latest.")
        _say()
        _say(f"{ctx.tag} is released and every surface agrees.")
        return 0

    if state == WRONG_LATEST:
        _say("=" * 72)
        _say("RELEASED, BUT npm SERVES A DIFFERENT VERSION")
        _say("=" * 72)
        _say()
        _say(npm_wrong_latest(ctx))
        return 1

    if state == UNREACHABLE:
        _say(f"Everything up to npm is done, but npm did not answer, so this "
             f"cannot say whether {ctx.version} is published or still staged. "
             f"Run the same command again once you have a connection.")
        return 1

    _say("=" * 72)
    _say("ONE THING LEFT, AND ONLY YOU CAN DO IT")
    _say("=" * 72)
    _say()
    _say(npm_instructions(ctx))
    _say()
    _say("Then re-run this command: it will verify the dist-tag and finish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
