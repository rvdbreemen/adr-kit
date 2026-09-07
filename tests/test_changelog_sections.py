"""A released CHANGELOG section may be corrected, never appended to.

The rule these tests pin is narrower than "the section must not change", and
deliberately so: this project edits released sections and is right to. Over the
59 sections that can be compared against their tag, six differ today and every
one is a correction rather than an addition. A byte-identity rule would fail all
six, and comparing bullet TEXT fails four of them, because a reworded first line
reads as a new bullet. Counting top-level bullets is what separates the two.

The comparison is exercised through an injected resolver rather than through
git. The complete suite runs on `actions/checkout@v4` without `fetch-depth`, so
a test that shelled out for tags would pass on a developer machine and skip or
fail on the runner -- the exact shape of environment-dependent breakage that has
cost this project several release pull requests.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_changelog_sections", ROOT / "scripts/check-changelog-sections.py"
)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


PUBLISHED = """# Changelog

## [Unreleased]

### Added

- Something not yet released.

## [1.1.0] - 2026-01-02

### Fixed

- The first shipped fix.
- The second shipped fix.

## [1.0.0] - 2026-01-01

### Added

- The very first release.
"""


def _resolver(mapping):
    """Stand in for `git show vX.Y.Z:CHANGELOG.md`, returning None when absent."""
    return lambda version: mapping.get(version)


def _both_tags(text=PUBLISHED):
    return _resolver({"1.1.0": text, "1.0.0": text})


def test_an_appended_bullet_under_a_released_heading_is_reported():
    current = PUBLISHED.replace(
        "- The second shipped fix.",
        "- The second shipped fix.\n- A fix that belongs under Unreleased.",
    )
    findings, compared, skipped = GATE.check(current, _both_tags())
    assert compared == 2
    assert [f["version"] for f in findings] == ["1.1.0"]
    assert (findings[0]["was"], findings[0]["now"]) == (2, 3)
    assert findings[0]["bullets"] == ["- A fix that belongs under Unreleased."]


def test_a_reworded_bullet_is_a_correction_and_passes():
    """0.46.0 corrected a count from "Nine" to "Ten" long after its tag.

    A rule comparing bullet text calls that an addition. It is not one, and
    failing it would teach the next author to route around the gate.
    """
    current = PUBLISHED.replace(
        "- The second shipped fix.", "- The second shipped fix, described correctly."
    )
    findings, compared, _ = GATE.check(current, _both_tags())
    assert compared == 2
    assert findings == []


def test_a_removed_bullet_passes():
    current = PUBLISHED.replace("- The second shipped fix.\n", "")
    findings, _, _ = GATE.check(current, _both_tags())
    assert findings == []


def test_growth_under_unreleased_is_never_a_finding():
    """[Unreleased] carries no version, so no heading regex ever matches it."""
    current = PUBLISHED.replace(
        "- Something not yet released.",
        "- Something not yet released.\n- And another.\n- And a third.",
    )
    findings, compared, _ = GATE.check(current, _both_tags())
    assert compared == 2
    assert findings == []


def test_a_section_without_a_usable_tag_is_skipped_and_counted():
    """Sixteen real sections predate the tagging convention or have no file.

    Reporting them as compared would be the failure this gate exists to catch:
    a check that says it looked when it did not.
    """
    current = PUBLISHED.replace(
        "- The second shipped fix.",
        "- The second shipped fix.\n- Appended after the tag.",
    )
    findings, compared, skipped = GATE.check(current, _resolver({"1.0.0": PUBLISHED}))
    assert compared == 1
    assert skipped == ["1.1.0"]
    assert findings == []


def test_a_tag_whose_changelog_lacks_the_heading_is_skipped():
    """The section was written after the tag, so there is nothing to compare."""
    older = PUBLISHED.split("## [1.1.0]")[0] + PUBLISHED.split("## [1.0.0]", 1)[1]
    findings, compared, skipped = GATE.check(
        PUBLISHED, _resolver({"1.1.0": older, "1.0.0": PUBLISHED})
    )
    assert skipped == ["1.1.0"]
    assert compared == 1
    assert findings == []


def test_the_report_names_the_heading_and_says_why_it_matters(capsys):
    current = PUBLISHED.replace(
        "- The second shipped fix.",
        "- The second shipped fix.\n- Appended after the tag.",
    )
    findings, compared, skipped = GATE.check(current, _both_tags())
    GATE.report(findings, compared, skipped)
    out = capsys.readouterr().out
    assert "## [1.1.0]" in out
    assert "- Appended after the tag." in out
    assert "verbatim as the GitHub Release body" in out
    assert "## [Unreleased]" in out


def test_bullet_count_ignores_nested_and_continuation_lines():
    body = (
        "- A bullet whose text\n"
        "  wraps onto a second line.\n"
        "  - A nested bullet.\n"
        "    - Deeper still.\n"
        "- A second top-level bullet.\n"
    )
    assert GATE.bullet_count(body) == 2


def test_the_checked_in_changelog_has_no_appended_release_bullets():
    """The live document, through the same git path the workflow step uses.

    Skipped rather than failed where the checkout carries no tags, because the
    complete suite runs on a shallow clone; the workflow step that gates a pull
    request checks out with fetch-depth: 0 and exits non-zero there instead.
    """
    listed = subprocess.run(
        ["git", "tag"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT
    )
    tags = set(listed.stdout.split()) if listed.returncode == 0 else set()
    if not tags:
        pytest.skip("no tags in this checkout; the workflow step covers this")
    current = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    findings, compared, _ = GATE.check(current, GATE._published_from_git(tags))
    assert compared > 0
    assert findings == [], f"released sections gained bullets: {findings}"
