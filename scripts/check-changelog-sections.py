#!/usr/bin/env python3
"""Refuse a CHANGELOG entry appended to a section that has already shipped.

`release-publish.yml` publishes a `## [X.Y.Z]` section verbatim as the GitHub
Release body, `bump-version.py` inserts the next release heading directly under
the `## [Unreleased]` marker, and `release_phases.py` reads a section from its
heading to the next `^## [`. Section membership is therefore positional, and a
bullet written under a released heading is lost twice over: it never reaches the
next release's notes, and the release that already shipped claims work it does
not contain. That happened twice, through two separate pull requests, and no
gate saw it: both diffs carry `### Fixed` as unchanged context, so the fragment
reads exactly like a correct addition unless you map the line numbers back to
the nearest `## [` heading.

WHY THIS COUNTS BULLETS RATHER THAN COMPARING TEXT. Editing a released section
is legitimate and this project does it: measured over 59 comparable sections,
six differ from their tag, and every one is a correction rather than an
addition -- a wrong count fixed from "Nine" to "Ten", a superseded npm claim
rewritten, two whitespace reflows, two rewordings. A byte-identity rule would
fail all six. Comparing bullet text fails four of them too, because a reworded
first line reads as a new bullet. The count is what separates correcting a
released note from appending to it.

Sections whose tag carries no CHANGELOG.md, and early releases made before the
tagging convention, cannot be compared at all. They are skipped and counted in
the output rather than passed silently, because a gate that reports "checked"
while checking nothing is the failure this whole file exists to prevent.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"

RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
TOP_LEVEL_BULLET = re.compile(r"^- \S")


def section(text: str, version: str) -> Optional[str]:
    """The body under `## [version]`, up to the next release heading.

    Deliberately the same shape as `release_phases._changelog_section`, because
    a gate that reads a section differently from the tool that publishes it
    would pass exactly the documents that break at release time.
    """
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else None


def bullet_count(section_text: str) -> int:
    """Top-level list items: the unit an author adds, unlike reflowed prose."""
    return sum(1 for line in section_text.splitlines() if TOP_LEVEL_BULLET.match(line))


def appended_bullets(section_text: str, published_text: str) -> List[str]:
    """The bullets present now that were not there at the tag.

    Returned for the message only. The verdict is the count, so a reworded
    bullet is not reported as an addition; this names the likely culprits by
    taking the ones whose text is new, and falls back to the tail when every
    bullet was reworded.
    """
    was = [line for line in published_text.splitlines() if TOP_LEVEL_BULLET.match(line)]
    now = [line for line in section_text.splitlines() if TOP_LEVEL_BULLET.match(line)]
    fresh = [line for line in now if line not in was]
    gained = len(now) - len(was)
    return fresh[:gained] if len(fresh) >= gained else now[-gained:]


def check(
    current: str, published_for: Callable[[str], Optional[str]]
) -> Tuple[List[Dict[str, object]], int, List[str]]:
    """Compare every release section against the same section at its tag.

    `published_for` returns the CHANGELOG.md at tag `vX.Y.Z`, or None when that
    tag is unusable. Injected rather than called directly so the rule can be
    tested without a git history, which the test matrix does not fetch.
    """
    findings: List[Dict[str, object]] = []
    compared = 0
    skipped: List[str] = []
    for version in RELEASE_HEADING.findall(current):
        published = published_for(version)
        was = section(published, version) if published is not None else None
        now = section(current, version)
        if was is None or now is None:
            skipped.append(version)
            continue
        compared += 1
        if bullet_count(now) > bullet_count(was):
            findings.append(
                {
                    "version": version,
                    "was": bullet_count(was),
                    "now": bullet_count(now),
                    "bullets": appended_bullets(now, was),
                }
            )
    return findings, compared, skipped


def _git(*args: str) -> Optional[str]:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.stdout if result.returncode == 0 else None


def _published_from_git(tags: set) -> Callable[[str], Optional[str]]:
    # Two spellings ship in this repository: 65 tags read `v0.56.0` and 14
    # older ones read `adr-kit--v0.1.0`. Resolving only the first silently
    # skipped fourteen comparable sections, which is the same kind of
    # overstated coverage this check exists to prevent.
    def resolve(version: str) -> Optional[str]:
        for tag in (f"v{version}", f"adr-kit--v{version}"):
            if tag in tags:
                published = _git("show", f"{tag}:CHANGELOG.md")
                if published is not None:
                    return published
        return None

    return resolve


def report(findings, compared, skipped, stream=None) -> None:
    # Resolved here rather than in the signature: a default bound at import
    # time keeps writing to the stream that existed then, which silently
    # bypasses any caller that replaced it.
    stream = sys.stdout if stream is None else stream
    print(
        f"Compared {compared} released CHANGELOG section(s) against their tag; "
        f"skipped {len(skipped)} with no usable tag.",
        file=stream,
    )
    for finding in findings:
        print(
            f"\nFAIL  ## [{finding['version']}] gained "
            f"{finding['now'] - finding['was']} bullet(s) since its tag "
            f"({finding['was']} -> {finding['now']}):",
            file=stream,
        )
        for bullet in finding["bullets"]:
            print(f"        {bullet[:100]}", file=stream)
    if findings:
        print(
            "\nThat section already shipped. release-publish.yml publishes it "
            "verbatim as the GitHub Release body, so an entry added here is "
            "absent from the next release's notes and falsely claimed by a "
            "release that does not contain it.\nMove these bullets under "
            "## [Unreleased], into the matching ### Added / ### Changed / "
            "### Fixed heading.",
            file=stream,
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--changelog", default=str(CHANGELOG), help="CHANGELOG.md to check"
    )
    args = parser.parse_args(argv)

    listed = _git("tag")
    if listed is None:
        print(
            "git tag failed: this check needs the tags, so the workflow step "
            "running it must check out with fetch-depth: 0.",
            file=sys.stderr,
        )
        return 2
    tags = set(listed.split())
    if not tags:
        print(
            "No tags in this checkout. The check cannot compare anything, and "
            "reporting success would be a lie; check out with fetch-depth: 0.",
            file=sys.stderr,
        )
        return 2

    current = Path(args.changelog).read_text(encoding="utf-8")
    findings, compared, skipped = check(current, _published_from_git(tags))
    report(findings, compared, skipped)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
