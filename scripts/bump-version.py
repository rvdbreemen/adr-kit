#!/usr/bin/env python3
"""Write a release version to every declared version site in one command.

Releasing used to mean hand-editing the version in nine files, discovered one
error at a time across several tool runs. This writer takes the version once and
propagates it everywhere `packaging/version-sites.json` declares, including the
CHANGELOG release heading, the three client plugin manifests, the two versioned
marketplace manifests, the template version stamps and the README version pins.

Usage:
  python scripts/bump-version.py 0.39.0
  python scripts/bump-version.py 0.39.0 --date 2026-07-23
  python scripts/bump-version.py 0.39.0 --check     # report, change nothing

After bumping, run `python scripts/build-client-adapters.py` to regenerate the
codex/ and copilot/ trees, then the release gates.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date as date_cls
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from version_sites import (  # noqa: E402
    SEMVER,
    VersionSiteError,
    check,
    format_findings,
    load_registry,
    read_canonical,
    write_all,
)

ROOT = Path(__file__).resolve().parent.parent
UNRELEASED = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)


def ensure_changelog_heading(version: str, release_date: str) -> str:
    """Make sure CHANGELOG.md carries `## [version] - date` as the top release.

    Returns a short description of what happened.
    """
    path = ROOT / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    heading_re = re.compile(rf"^## \[{re.escape(version)}\][^\n]*$", re.MULTILINE)

    existing = heading_re.search(text)
    if existing:
        wanted = f"## [{version}] - {release_date}"
        if existing.group(0) != wanted:
            text = text[: existing.start()] + wanted + text[existing.end() :]
            path.write_text(text, encoding="utf-8", newline="\n")
            return f"updated existing CHANGELOG heading to '{wanted}'"
        return f"CHANGELOG heading '{wanted}' already correct"

    marker = UNRELEASED.search(text)
    if not marker:
        raise VersionSiteError(
            "CHANGELOG.md has no '## [Unreleased]' marker to insert the new release under"
        )
    insert_at = marker.end()
    block = f"\n\n## [{version}] - {release_date}\n\n### Added\n\n- TODO: describe this release.\n"
    text = text[:insert_at] + block + text[insert_at:]
    path.write_text(text, encoding="utf-8", newline="\n")
    return (
        f"inserted new CHANGELOG section '## [{version}] - {release_date}' "
        "with a TODO placeholder: replace it with the real release notes"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release version, MAJOR.MINOR.PATCH (a leading 'v' is stripped)")
    parser.add_argument("--date", help="Release date for the CHANGELOG heading (default: today)")
    parser.add_argument("--check", action="store_true", help="Report drift and change nothing")
    args = parser.parse_args(argv)

    version = args.version.lstrip("vV").strip()
    if not SEMVER.match(version):
        parser.error(f"not a MAJOR.MINOR.PATCH version: {args.version!r}")
    release_date = args.date or date_cls.today().isoformat()

    try:
        registry = load_registry(ROOT)

        if args.check:
            findings = check(ROOT, version, registry)
            if findings:
                print(f"Version drift against {version}:", file=sys.stderr)
                print(format_findings(findings), file=sys.stderr)
                return 1
            print(f"All declared version sites already carry {version}.")
            return 0

        print(ensure_changelog_heading(version, release_date))
        changed = write_all(ROOT, version, registry)
        if changed:
            print(f"Wrote {version} to {len(changed)} site(s):")
            for entry in changed:
                print(f"  - {entry}")
        else:
            print(f"All declared version sites already carried {version}.")

        canonical = read_canonical(ROOT, registry)
        if canonical != version:
            print(
                f"WARNING: canonical CHANGELOG heading is {canonical!r}, expected {version!r}",
                file=sys.stderr,
            )
            return 1

        remaining = check(ROOT, version, registry)
        if remaining:
            print("Sites still not matching after the write:", file=sys.stderr)
            print(format_findings(remaining), file=sys.stderr)
            return 1

        print("\nNext: python scripts/build-client-adapters.py   (regenerate codex/ and copilot/)")
        return 0
    except VersionSiteError as exc:
        print(f"bump-version: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
