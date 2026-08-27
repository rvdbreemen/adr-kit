#!/usr/bin/env python3
"""The phases of docs/RELEASING.md, each one able to say whether it is already done.

ADR-042 makes this the sanctioned way to cut a release, and keeps
docs/RELEASING.md as the specification: every phase here mirrors one step
there, in the same order, so a divergence between the two is visible in review
rather than hidden.

Every phase is idempotent. A release that dies halfway is the normal case - a
check goes red, a merge waits on CI, a machine is closed - and the recovery has
to be "run it again", not "work out which half already happened". Each phase
answers `done(ctx)` from the repository's actual state rather than from a
progress file, because a progress file is one more thing that can disagree with
reality.

Two checks here exist because nothing had them before, and both cost a release:

* `verify_tag` asserts the tag resolves to `origin/main`. v0.55.0 was burned by
  a tag on the dev tip, where every version site still read the previous
  release, and the gate correctly refused to publish it.
* `npm_latest` asserts the dist-tag names the released version. npm sets
  `latest` to the version published LAST, not the highest, so approving staged
  versions out of order silently points `npm install` at an older release.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable, List, NamedTuple, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_shell import (  # noqa: E402
    CLIENTS,
    PACKAGE,
    ROOT,
    Context,
    ReleaseError,
    _clean_tree,
    _client_version,
    _main_sha,
    _version_everywhere,
    _wait_until,
    git,
    run,
    script,
)


# --- phase 0: preflight -----------------------------------------------------


def preflight_done(ctx: Context) -> bool:
    return False  # cheap, and its answer can change between runs


def preflight(ctx: Context) -> List[str]:
    notes = []
    if not _clean_tree():
        raise ReleaseError(
            "the working tree has uncommitted changes. Commit or stash them "
            "first: a release commit must contain the version bump and nothing "
            "that happened to be lying around."
        )
    code, out, _ = script("check-branch-sync.py")
    if code == 1:
        raise ReleaseError(
            "dev does not carry every published release:\n"
            + out
            + "\nMerge main back into dev and land that first. A release branch "
            "cut from a stale dev collides with main on every version stamp."
        )
    if code == 2:
        notes.append("branch-sync check could not run; treated as infrastructure noise")
    if run(["gh", "auth", "status"])[0] != 0:
        raise ReleaseError(
            "gh is not authenticated. The driver opens the pull request with "
            "your credentials on purpose: GitHub does not start workflow runs "
            "for events caused by GITHUB_TOKEN, so a bot-opened PR would never "
            "receive the checks main requires (ADR-042)."
        )
    notes.append("working tree clean, dev current, gh authenticated")
    return notes


# --- phase 1: prepare the version and the release notes ---------------------


def prepare_done(ctx: Context) -> bool:
    return _version_everywhere(ctx) and not _changelog_is_placeholder(ctx)


def _changelog_section(ctx: Context) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"^## \[{re.escape(ctx.version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def _changelog_is_placeholder(ctx: Context) -> bool:
    body = _changelog_section(ctx)
    return (not body.strip()) or "TODO" in body


def prepare(ctx: Context) -> List[str]:
    notes = []
    if not _version_everywhere(ctx):
        _, out, _ = script("bump-version.py", ctx.version, check=True)
        notes.append(out.strip().splitlines()[0] if out.strip() else "version written")
        script("build-client-adapters.py", check=True)
        notes.append("client adapters regenerated")
    if _changelog_is_placeholder(ctx):
        raise ReleaseError(
            f"CHANGELOG.md's [{ctx.version}] section is still the placeholder.\n"
            "release-publish.yml publishes that section verbatim as the GitHub "
            "Release body, so it has to read as the announcement: group the "
            "changes, name the user-facing impact, call out upgrade steps.\n"
            "Write it, then run this command again - everything else is already "
            "in place."
        )
    notes.append(f"every version site reads {ctx.version}")
    return notes


# --- phase 2: the gates CI will run anyway ----------------------------------


def verify_done(ctx: Context) -> bool:
    return False  # the point is to run them


def verify(ctx: Context) -> List[str]:
    notes = []
    for label, cmd in (
        ("version consistency", lambda: script("check-release-version.py", "--expect", ctx.tag)),
        ("adapter drift", lambda: script("build-client-adapters.py", "--check")),
    ):
        if cmd()[0] != 0:
            raise ReleaseError(f"{label} check failed; run it directly to see the detail")
        notes.append(f"{label}: pass")
    for label, cmd in (
        ("adr-lint --strict", ["bin/adr-lint", "--strict", "docs/adr"]),
        ("adr-index --check", ["bin/adr-index", "--check", "docs/adr"]),
    ):
        if run([sys.executable, str(ROOT / cmd[0]), *cmd[1:]])[0] != 0:
            raise ReleaseError(f"{label} failed; run it directly to see the detail")
        notes.append(f"{label}: pass")
    if ctx.skip_tests:
        notes.append("pytest SKIPPED by request; CI still runs it on the pull request")
        return notes
    code, out, _ = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    tail = (out.strip().splitlines() or ["no output"])[-1]
    if code != 0:
        raise ReleaseError(
            f"the test suite failed: {tail}\n"
            "Before treating this as real, check that no second pytest is "
            "running: a killed background wrapper leaves its child alive, and "
            "two concurrent runs produce failures that are artefacts."
        )
    notes.append(f"pytest: {tail}")
    return notes


# --- phase 3: land on main --------------------------------------------------


def land_done(ctx: Context) -> bool:
    git("fetch", "origin", "--tags")
    code, head, _ = git("show", "origin/main:CHANGELOG.md")
    if code != 0:
        return False
    return bool(re.search(rf"^## \[{re.escape(ctx.version)}\]", head, re.MULTILINE))


def land(ctx: Context) -> List[str]:
    notes = []
    current = git("rev-parse", "--abbrev-ref", "HEAD")[1].strip()
    if current != ctx.branch:
        if git("rev-parse", "--verify", ctx.branch)[0] == 0:
            git("checkout", ctx.branch, check=True)
        else:
            git("checkout", "-b", ctx.branch, check=True)
        notes.append(f"on {ctx.branch}")
    if not _clean_tree():
        git("add", "-A", check=True)
        git("commit", "-m", f"chore(release): {ctx.tag}", check=True)
        notes.append("release commit written")
    git("push", "-u", "origin", ctx.branch, check=True)

    existing = run(["gh", "pr", "list", "--head", ctx.branch, "--json", "number", "--jq", ".[0].number"])[1].strip()
    if not existing:
        body = (
            f"Release {ctx.tag}. Prepared by `scripts/release.py`, which mirrors "
            f"`docs/RELEASING.md`.\n\n"
            f"**Do not tag this by hand.** Since ADR-042 `release-publish.yml` "
            f"creates the tag from the merged commit and publishes in the same "
            f"run. Tagging by hand is how v0.55.0 was burned.\n\n"
            f"Release notes are the `## [{ctx.version}]` CHANGELOG section, which "
            f"the workflow publishes verbatim."
        )
        run(["gh", "pr", "create", "--base", "main", "--head", ctx.branch,
             "--title", f"chore(release): {ctx.tag}", "--body", body], check=True)
        notes.append("pull request opened into main")
    number = run(["gh", "pr", "list", "--head", ctx.branch, "--json", "number", "--jq", ".[0].number"])[1].strip()
    run(["gh", "pr", "merge", number, "--auto", "--merge"])
    notes.append(f"auto-merge armed on #{number}; waiting for the required checks")
    _wait_until(lambda: land_done(ctx), ctx, f"pull request #{number} to merge into main")
    notes.append("merged into main")
    return notes


# --- phase 4: the tag the workflow creates ----------------------------------


def verify_tag_done(ctx: Context) -> bool:
    git("fetch", "origin", "--tags")
    peeled = git("rev-parse", f"{ctx.tag}^{{}}")
    return peeled[0] == 0 and peeled[1].strip() == _main_sha()


def verify_tag(ctx: Context) -> List[str]:
    _wait_until(lambda: git("rev-parse", f"{ctx.tag}^{{}}")[0] == 0, ctx,
                f"release-publish.yml to create {ctx.tag}")
    peeled = git("rev-parse", f"{ctx.tag}^{{}}")[1].strip()
    main = _main_sha()
    if peeled != main:
        raise ReleaseError(
            f"{ctx.tag} resolves to {peeled[:7]} but origin/main is {main[:7]}.\n"
            "A tag on a commit whose version sites disagree with it is exactly "
            "what cost v0.55.0. Do not move the tag: a pushed tag is a public "
            "ref consumers may register a marketplace from. Release the next "
            "patch version instead."
        )
    return [f"{ctx.tag} resolves to {peeled[:7]}, equal to origin/main"]


# --- phase 5: merge back into dev -------------------------------------------


def syncback_done(ctx: Context) -> bool:
    return script("check-branch-sync.py")[0] == 0


def syncback(ctx: Context) -> List[str]:
    branch = f"sync/{ctx.tag}-to-dev"
    git("fetch", "origin")
    if git("rev-parse", "--verify", branch)[0] != 0:
        git("checkout", "-b", branch, "origin/dev", check=True)
    else:
        git("checkout", branch, check=True)
    code, out, err = git("merge", "origin/main", "--no-edit")
    if code != 0:
        raise ReleaseError(
            "the merge back into dev has conflicts:\n" + out + err +
            "\nResolve them with main authoritative for anything a release "
            "touches - version sites, generated adapters, manifests, the "
            "OpenCode package - and keep dev's [Unreleased] entries above "
            "main's published sections in CHANGELOG.md. Then run this again."
        )
    git("push", "-u", "origin", branch, check=True)
    if not run(["gh", "pr", "list", "--head", branch, "--json", "number", "--jq", ".[0].number"])[1].strip():
        run(["gh", "pr", "create", "--base", "dev", "--head", branch,
             "--title", f"Merge the published {ctx.tag} release back into dev",
             "--body", "Step 5 of docs/RELEASING.md. Skipping it is silent at "
                       "the time and arms the next release to revert this one."], check=True)
    number = run(["gh", "pr", "list", "--head", branch, "--json", "number", "--jq", ".[0].number"])[1].strip()
    run(["gh", "pr", "merge", number, "--auto", "--merge"])
    return [f"sync pull request #{number} opened and armed"]


# --- phase 6: this machine's prepared-directory marketplace -----------------



def install_done(ctx: Context) -> bool:
    return all(_client_version(name) == ctx.version for name in CLIENTS)


def install(ctx: Context) -> List[str]:
    run([sys.executable, str(ROOT / "scripts" / "install-agent-envs.py"), "--clients", "all"])
    # The exit code is not the answer: read each client back. A rollback that
    # cannot validate reports failure while leaving the install intact, and an
    # install that reports success can still be blocked on one client.
    reported = {name: _client_version(name) for name in CLIENTS}
    behind = [f"{n}={v or 'unreadable'}" for n, v in reported.items() if v != ctx.version]
    if behind:
        raise ReleaseError(
            "these clients do not report the released version: " + ", ".join(behind) + "\n"
            "On Windows a client that is running holds its own plugin directory: "
            "an MCP server started with a relative command has that directory as "
            "its working directory, which locks it. Close the client, confirm no "
            "adr-mcp process survives it, then run this command again."
        )
    return [f"all three clients report {ctx.version}"]


# --- phase 7: the step npm will not let anyone automate ---------------------


def npm_latest_done(ctx: Context) -> bool:
    code, out, _ = run(["npm", "view", PACKAGE, "dist-tags", "--json", "--prefer-online"])
    if code != 0:
        return False
    try:
        return json.loads(out).get("latest") == ctx.version
    except json.JSONDecodeError:
        return False


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


class Phase(NamedTuple):
    name: str
    step: str
    done: Callable[[Context], bool]
    run: Callable[[Context], List[str]]


PHASES: Tuple[Phase, ...] = (
    Phase("preflight", "0", preflight_done, preflight),
    Phase("prepare", "1", prepare_done, prepare),
    Phase("verify", "2", verify_done, verify),
    Phase("land", "3", land_done, land),
    Phase("tag", "3", verify_tag_done, verify_tag),
    Phase("syncback", "4", syncback_done, syncback),
    Phase("install", "6", install_done, install),
)
