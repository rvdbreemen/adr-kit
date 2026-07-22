#!/usr/bin/env python3
"""Assert the release version is identical across every publish surface.

The three coding-agent marketplaces (Claude Code, Codex, GitHub Copilot) all
resolve adr-kit from the public repository, so a release is only coherent when
every version-bearing manifest, the CHANGELOG and the git tag agree. This check
is the gate that the release workflow runs before cutting a GitHub Release.

Version sites checked:
  - .claude-plugin/plugin.json                     -> ["version"]        (Claude plugin)
  - codex/.codex-plugin/plugin.json                -> ["version"]        (Codex plugin)
  - copilot/plugin.json                            -> ["version"]        (Copilot plugin)
  - .claude-plugin/marketplace.json                -> plugins[0].version (Claude marketplace)
  - .github/plugin/marketplace.json                -> plugins[0].version (Copilot marketplace)
  - CHANGELOG.md                                   -> first "## [X.Y.Z]" heading
  - the expected version passed via --expect       (normally the git tag, minus a leading "v")

.agents/plugins/marketplace.json (Codex marketplace) intentionally carries no
version field: it points at the local ./codex source whose version lives in
codex/.codex-plugin/plugin.json, so it is not a version site.

Usage:
  python scripts/check-release-version.py --expect 0.37.0
  python scripts/check-release-version.py --expect v0.37.0   # leading v is stripped
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (label, relative path, extractor) for every version-bearing manifest.
PLUGIN_SITES = [
    ("Claude plugin", ".claude-plugin/plugin.json", lambda d: d.get("version")),
    ("Codex plugin", "codex/.codex-plugin/plugin.json", lambda d: d.get("version")),
    ("Copilot plugin", "copilot/plugin.json", lambda d: d.get("version")),
    ("Claude marketplace", ".claude-plugin/marketplace.json", lambda d: _first_plugin_version(d)),
    ("Copilot marketplace", ".github/plugin/marketplace.json", lambda d: _first_plugin_version(d)),
]

CHANGELOG_HEADING = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]")


def _first_plugin_version(doc: dict) -> str | None:
    plugins = doc.get("plugins")
    if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict):
        return plugins[0].get("version")
    return None


def _read_json(rel: str) -> tuple[dict | None, str | None]:
    path = ROOT / rel
    if not path.is_file():
        return None, f"missing file: {rel}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {rel}: {exc}"


def _changelog_version() -> tuple[str | None, str | None]:
    path = ROOT / "CHANGELOG.md"
    if not path.is_file():
        return None, "missing CHANGELOG.md"
    for line in path.read_text(encoding="utf-8").splitlines():
        m = CHANGELOG_HEADING.match(line.strip())
        if m:
            return m.group(1), None
    return None, "no '## [X.Y.Z]' release heading found in CHANGELOG.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        required=True,
        help="Expected release version (git tag). A leading 'v' is stripped.",
    )
    args = parser.parse_args(argv)
    expected = args.expect.lstrip("vV").strip()

    findings: list[str] = []
    observed: list[tuple[str, str | None]] = []

    for label, rel, extract in PLUGIN_SITES:
        doc, err = _read_json(rel)
        if err:
            findings.append(err)
            observed.append((label, None))
            continue
        value = extract(doc)
        observed.append((label, value))
        if value != expected:
            findings.append(f"{label} ({rel}) = {value!r}, expected {expected!r}")

    changelog_version, cl_err = _changelog_version()
    if cl_err:
        findings.append(cl_err)
    else:
        observed.append(("CHANGELOG top", changelog_version))
        if changelog_version != expected:
            findings.append(
                f"CHANGELOG.md top release = {changelog_version!r}, expected {expected!r}"
            )

    print(f"Expected release version: {expected}")
    for label, value in observed:
        mark = "ok" if value == expected else "MISMATCH"
        print(f"  [{mark}] {label}: {value}")

    if findings:
        print("\nRelease version check FAILED:", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nAll publish surfaces agree on the release version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
