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
    apply_transaction,
    check,
    describe_changes,
    format_findings,
    load_registry,
    plan_writes,
    read_canonical,
)

ROOT = Path(__file__).resolve().parent.parent
UNRELEASED = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)


def plan_changelog_heading(version: str, release_date: str) -> "tuple[bytes | None, str]":
    """Compute a CHANGELOG.md carrying `## [version] - date` as the top release.

    Writes nothing. The bytes join the same transaction as the declared sites,
    because the CHANGELOG heading is the version every other tool reads as
    canonical: writing it first and then failing to write the sites left the
    repository announcing a release that no manifest carried, with no rollback.

    Returns the new bytes (None when the file already says the right thing) and
    a short description of what happened.
    """
    path = ROOT / "CHANGELOG.md"
    original = path.read_text(encoding="utf-8")
    heading_re = re.compile(rf"^## \[{re.escape(version)}\][^\n]*$", re.MULTILINE)

    existing = heading_re.search(original)
    if existing:
        wanted = f"## [{version}] - {release_date}"
        if existing.group(0) == wanted:
            return None, f"CHANGELOG heading '{wanted}' already correct"
        text = original[: existing.start()] + wanted + original[existing.end() :]
        note = f"updated existing CHANGELOG heading to '{wanted}'"
    else:
        marker = UNRELEASED.search(original)
        if not marker:
            raise VersionSiteError(
                "CHANGELOG.md has no '## [Unreleased]' marker to insert the new release under"
            )
        insert_at = marker.end()
        block = (
            f"\n\n## [{version}] - {release_date}\n\n### Added\n\n"
            "- TODO: describe this release.\n"
        )
        text = original[:insert_at] + block + original[insert_at:]
        note = (
            f"inserted new CHANGELOG section '## [{version}] - {release_date}' "
            "with a TODO placeholder: replace it with the real release notes"
        )
    return text.encode("utf-8"), note


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

        # Plan everything -- CHANGELOG included -- before the first byte lands,
        # then write it as one transaction that rolls back as a unit.
        changelog_bytes, note = plan_changelog_heading(version, release_date)
        changes = plan_writes(ROOT, version, registry)
        changed = describe_changes(ROOT, changes, registry)
        if changelog_bytes is not None:
            changes[ROOT / "CHANGELOG.md"] = changelog_bytes
        apply_transaction(changes)

        print(note)
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
