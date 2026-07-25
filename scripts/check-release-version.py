#!/usr/bin/env python3
"""Assert the release version is identical across every publish surface.

The three coding-agent marketplaces (Claude Code, Codex, GitHub Copilot) all
resolve adr-kit from the public repository, so a release is only coherent when
every version-bearing file, the CHANGELOG and the git tag agree. This check is
the gate the release workflow runs before cutting a GitHub Release.

The sites are not hard-coded here: they come from `packaging/version-sites.json`
via scripts/version_sites.py, which is the same registry the bump writer and the
test suite use. Declaring a new version-bearing file there teaches every tool at
once. Every mismatch is reported in one pass.

Usage:
  python scripts/check-release-version.py --expect 0.39.0
  python scripts/check-release-version.py --expect v0.39.0   # leading v is stripped
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from version_sites import (  # noqa: E402
    SEMVER,
    VersionSiteError,
    check,
    format_findings,
    load_registry,
    read_all,
    read_canonical,
)

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        required=True,
        help="Expected release version (git tag). A leading 'v' is stripped.",
    )
    args = parser.parse_args(argv)
    expected = args.expect.lstrip("vV").strip()
    if not SEMVER.match(expected):
        parser.error(f"not a MAJOR.MINOR.PATCH version: {args.expect!r}")

    try:
        registry = load_registry(ROOT)
    except VersionSiteError as exc:
        print(f"check-release-version: {exc}", file=sys.stderr)
        return 1

    print(f"Expected release version: {expected}")
    canonical = read_canonical(ROOT, registry)
    mark = "ok" if canonical == expected else "MISMATCH"
    print(f"  [{mark}] {registry['canonical']['label']}: {canonical}")
    for site, values in read_all(ROOT, registry):
        for value in values:
            mark = "ok" if value == expected else "MISMATCH"
            print(f"  [{mark}] {site['label']}: {value}")

    findings = check(ROOT, expected, registry)
    if findings:
        print("\nRelease version check FAILED:", file=sys.stderr)
        print(format_findings(findings), file=sys.stderr)
        print(
            f"\nFix them all at once: python scripts/bump-version.py {expected}",
            file=sys.stderr,
        )
        return 1

    print("\nAll publish surfaces agree on the release version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
