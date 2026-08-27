#!/usr/bin/env python3
"""Write a release version to every declared version site in one command.

This is the canonical bump writer (ADR-013, docs/RELEASING.md). `bin/bump-version`
delegates here rather than carrying a second implementation of the same release
step: two writers with different capabilities is what left the CHANGELOG compare
links unwritten on every release (TASK-139).

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
import json
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
UNRELEASED_LINK = re.compile(r"^\[Unreleased\]:\s+.*$", re.MULTILINE)
COMPARE = "https://github.com/rvdbreemen/adr-kit/compare"

#: Which declared sites carry plugin identity, derived from the registry rather
#: than from a second list of paths. Moved here from `bin/bump-version` when that
#: script became a delegation: these were live preflight validations that only
#: the unnamed writer performed, so the tool the runbook actually names could
#: bump a tree whose manifests disagreed about the plugin's name (TASK-139).
PLUGIN_MANIFEST_POINTER = "/version"
MARKETPLACE_POINTER_RE = re.compile(r"^/plugins/(\d+)/version$")


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VersionSiteError(f"{path}: {exc}") from exc


def plugin_identity(registry: dict) -> "tuple[str, str]":
    """The (name, version) every declared client manifest agrees on.

    Nothing declares a canonical manifest, so agreement is the check: if the
    three disagree on the name, there is no defensible value to write into the
    marketplace entries.
    """
    manifests = [
        site
        for site in registry["sites"]
        if site.get("kind") == "json" and site.get("pointer") == PLUGIN_MANIFEST_POINTER
    ]
    if not manifests:
        raise VersionSiteError(
            "registry declares no client plugin manifest (a JSON site at /version)"
        )
    names: dict = {}
    version = "?"
    for site in manifests:
        data = _read_json(ROOT / site["path"])
        if not isinstance(data, dict) or not isinstance(data.get("version"), str):
            raise VersionSiteError(
                f"{site['path']}: expected an object with a string version field"
            )
        name = data.get("name")
        if not isinstance(name, str) or not name:
            raise VersionSiteError(f"{site['path']}: expected a non-empty string name")
        names.setdefault(name, []).append(site["path"])
        version = data["version"]
    if len(names) > 1:
        detail = "; ".join(f"{n!r} in {', '.join(p)}" for n, p in sorted(names.items()))
        raise VersionSiteError(
            f"all client manifests must use the same plugin name: {detail}"
        )
    return next(iter(names)), version


def check_marketplace_entries(registry: dict, plugin_name: str) -> None:
    """Every marketplace pointer must resolve to the one entry naming this plugin."""
    for site in registry["sites"]:
        match = MARKETPLACE_POINTER_RE.match(str(site.get("pointer", "")))
        if site.get("kind") != "json" or not match:
            continue
        path = ROOT / site["path"]
        index = int(match.group(1))
        document = _read_json(path)
        plugins = document.get("plugins") if isinstance(document, dict) else None
        if not isinstance(plugins, list) or index >= len(plugins):
            raise VersionSiteError(
                f"{site['path']}: {site['pointer']} does not resolve to a plugin entry"
            )
        target = plugins[index]
        if not isinstance(target, dict):
            raise VersionSiteError(
                f"{site['path']}: the entry at {site['pointer']} is not an object"
            )
        if target.get("name") != plugin_name:
            raise VersionSiteError(
                f"no plugin named {plugin_name!r} at {site['pointer']} in "
                f"{site['path']} (found {target.get('name')!r} there)"
            )
        if not isinstance(target.get("version"), str):
            raise VersionSiteError(
                f"{site['path']}: matching plugin entries require string version fields"
            )
        others = [
            position
            for position, entry in enumerate(plugins)
            if position != index
            and isinstance(entry, dict)
            and entry.get("name") == plugin_name
        ]
        if others:
            raise VersionSiteError(
                f"{site['path']}: {plugin_name!r} also appears at index {others}, "
                f"which the pointer {site['pointer']} would leave stale"
            )


def plan_changelog_links(text: str, current: str, version: str) -> str:
    """Retarget `[Unreleased]` and add the `[version]` compare link.

    The block at the bottom of CHANGELOG.md went stale on every release. The
    runbook runs this script, which had no link logic at all; the only tool that
    could write it was `bin/bump-version`, which the runbook never named. After
    v0.46.0 the block still pointed at v0.45.0 and seven earlier headings had no
    target at all, all backfilled by hand in a31cb04. Hand-backfilling is not a
    fix -- the next release reproduces the gap.

    Pure, and folded into the same CHANGELOG image as the heading insert, so the
    registry's own `[Unreleased]` site sees this edit rather than the stale
    bytes.
    """
    unreleased = f"[Unreleased]: {COMPARE}/v{version}...HEAD"
    release = f"[{version}]: {COMPARE}/v{current}...v{version}"
    if re.search(rf"^\[{re.escape(version)}\]:", text, re.MULTILINE):
        # Re-running a bump for the same version must not add a second target.
        return UNRELEASED_LINK.sub(unreleased, text, count=1)
    if UNRELEASED_LINK.search(text):
        return UNRELEASED_LINK.sub(f"{unreleased}\n{release}", text, count=1)
    return text.rstrip() + f"\n\n{unreleased}\n{release}\n"


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

        # Preflight the identity assumptions before the first byte lands. These
        # only ever ran in bin/bump-version, which the runbook does not name.
        plugin_name, manifest_version = plugin_identity(registry)
        check_marketplace_entries(registry, plugin_name)

        # Plan everything -- CHANGELOG included -- before the first byte lands,
        # then write it as one transaction that rolls back as a unit.
        #
        # The CHANGELOG is folded in order into ONE image: heading, then links,
        # then whatever the registry declares inside it. The previous shape
        # planned the registry and the CHANGELOG separately and then assigned
        # `changes[CHANGELOG] = changelog_bytes`, which silently discarded any
        # registry-computed bytes for that file -- harmless while no site
        # declared the CHANGELOG, and a silent no-op the moment one did.
        changelog_bytes, note = plan_changelog_heading(version, release_date)
        changelog_path = ROOT / "CHANGELOG.md"
        current = read_canonical(ROOT, registry) or manifest_version
        image = (
            changelog_bytes.decode("utf-8")
            if changelog_bytes is not None
            else changelog_path.read_text(encoding="utf-8")
        )
        image = plan_changelog_links(image, current, version)

        changes = plan_writes(
            ROOT, version, registry, overrides={changelog_path: image}
        )
        changed = describe_changes(ROOT, changes, registry)
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

        # The staging hint used to exist only in bin/bump-version, so the tool
        # the runbook names sent people away without it. Carried across with the
        # rest of that script's behaviour rather than lost in the merge.
        staged = sorted(path.relative_to(ROOT).as_posix() for path in changes)
        print()
        print("Next: python scripts/build-client-adapters.py   (regenerate codex/ and copilot/)")
        print("Then verify the changes and:")
        print("  git add " + " ".join(staged))
        print(f'  git commit -m "chore(release): v{version}"')
        # Deliberately not "git tag": since ADR-042 the tag is created by
        # release-publish.yml from the merged main commit. Tagging by hand is
        # how v0.55.0 was burned - the tag went on the dev tip, where every
        # version site still read the previous release, and the gate refused to
        # publish a tag that was already public.
        print()
        print(f"Do NOT tag by hand. Open a pull request into main; once it merges,")
        print(f"release-publish.yml creates v{version} on the merge commit and publishes.")
        return 0
    except VersionSiteError as exc:
        print(f"bump-version: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
