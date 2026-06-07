"""Regression guard for adr-kit#9 across every tool that parses ## Enforcement.

The original ``ENFORCEMENT_BLOCK_RE`` used a nested lazy quantifier
``(?:.*?\\n)*?`` under ``re.DOTALL``. With no ```json fence after the heading to
anchor the match, the engine explored combinatorially many partitions of the
file tail before failing — fast on match, catastrophic on non-match. The fix in
adr-retire shipped in v0.19.1; the same pattern lived on in adr-judge,
adr-generate-scripts and adr-lint. This test pins all of them to a linear,
non-nested pattern so the ReDoS cannot be reintroduced.
"""

import runpy
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tools whose module namespace exposes ENFORCEMENT_BLOCK_RE.
ENFORCEMENT_TOOLS = ["adr-judge", "adr-generate-scripts", "adr-lint"]

# A ## Enforcement section with no ```json fence and a long prose body. The old
# nested-quantifier regex hung for seconds on inputs of this size; the linear
# rewrite returns in well under a millisecond.
_FENCE_LESS_ENFORCEMENT = "## Enforcement\n\n" + "\n".join(
    f"- manual review rule {n}" for n in range(400)
)


def _load(tool: str) -> dict:
    return runpy.run_path(str(REPO_ROOT / "bin" / tool))


@pytest.mark.parametrize("tool", ENFORCEMENT_TOOLS)
def test_enforcement_regex_is_linear_on_fence_less_section(tool):
    namespace = _load(tool)
    pattern = namespace["ENFORCEMENT_BLOCK_RE"]
    start = time.perf_counter()
    match = pattern.search(_FENCE_LESS_ENFORCEMENT)
    elapsed = time.perf_counter() - start
    assert match is None, f"{tool}: fence-less Enforcement must not match"
    assert elapsed < 0.5, f"{tool}: regex took {elapsed:.2f}s (ReDoS regression)"


@pytest.mark.parametrize("tool", ENFORCEMENT_TOOLS)
def test_enforcement_regex_has_no_nested_quantifier(tool):
    pattern = _load(tool)["ENFORCEMENT_BLOCK_RE"].pattern
    assert "(?:.*?\\n)*?" not in pattern, (
        f"{tool}: nested lazy quantifier reintroduced — ReDoS risk (adr-kit#9)"
    )


@pytest.mark.parametrize("tool", ENFORCEMENT_TOOLS)
def test_enforcement_regex_still_matches_fenced_block(tool):
    pattern = _load(tool)["ENFORCEMENT_BLOCK_RE"]
    fenced = (
        "## Enforcement\n\n"
        "some prose\nmore prose\n\n"
        '```json\n{"forbid_pattern": []}\n```\n'
    )
    match = pattern.search(fenced)
    assert match is not None, f"{tool}: must still match a properly fenced block"
    assert '"forbid_pattern": []' in match.group(1)
