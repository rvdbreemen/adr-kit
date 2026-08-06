"""An ADR whose named gate exists must stop saying it has none.

ADR-020 through ADR-032 were accepted with `gate: null` and `binding: false`,
because each declares a gate name that did not exist in the tree yet and
`adr-lint` refuses an Accepted *binding* ADR whose gate cannot be resolved. The
fields said what was true rather than what was intended.

The part that decays silently is the flip back. `binding: false` costs a real
thing while it lasts -- `adr_retrieval_health` only inspects Accepted binding
records, so a non-binding ADR's Decision Contract is never checked -- and nothing
reminds anyone once the gate finally ships.

This turns "someone must remember" into "the gate tells you" (TASK-127).

It lives here rather than in `bin/adr-lint` deliberately. The investigation
measured the equivalent probe at roughly +220 ms on every lint run, and lint runs
on every commit through the pre-commit hook. A governance check that makes the
commit path slower is a check people switch off.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "adr"

# Where a gate anchor may legitimately live. Mirrors adr-lint's own scan set:
# docs/ and backlog/ are excluded, because an ADR's own Verification bullet and a
# task file's table must not be able to make a gate "exist".
ANCHOR_ROOTS = ("bin", "hooks", "scripts", "tests", "clients", ".github")

# The name may be the whole bullet, or may be followed by a colon and prose --
# ADR-020..029 all use the second form. Anchoring on `$` matched neither of them
# and the check silently found nothing, which is the failure mode a gate about
# silent decay can least afford.
_GATE_NAME = re.compile(r"^\s*[*-]\s*`([a-z0-9][a-z0-9-]*-v\d+)`", re.M)

# Sentences that are only true while the gate is still pending. Each one was
# written next to `gate: null, binding: false` and is a false statement the
# moment those fields flip.
#
# This exists because the frontmatter half of the flip was mechanical and the
# prose half was not (TASK-141). The sweep that closed TASK-127 replaced the
# opening sentence of seven Verification bullets and left the trailing clause
# behind, so seven records read "the gate that anchors this decision. Both
# fields flip back together when the gate ships" -- corrected and stale in the
# same sentence. A half-applied sweep is exactly what a check catches and a
# reader does not.
_PENDING_PROSE = (
    (re.compile(r"does not exist yet", re.I), "says the gate does not exist yet"),
    (re.compile(r"flip back together", re.I), "still promises a future flip"),
    (re.compile(r"`gate` is null", re.I), "says gate is null"),
    (re.compile(r"`binding` is false", re.I), "says binding is false"),
    (re.compile(r"when the gate ships", re.I), "defers to a gate that has shipped"),
    (re.compile(r"is to be anchored by", re.I), "describes the anchor as future"),
    (re.compile(r"stays empty until", re.I), "says verified_in stays empty"),
)


def _verification_section(text: str) -> str | None:
    match = re.search(
        r"^### Verification\s*$(.*?)^##", text, re.M | re.S
    ) or re.search(r"^### Verification\s*$(.*)", text, re.M | re.S)
    return match.group(1) if match else None


def _verification_gate(text: str) -> str | None:
    """The gate name an ADR declares in its Verification section, if any."""
    section = _verification_section(text)
    if section is None:
        return None
    names = _GATE_NAME.findall(section)
    return names[0] if names else None


def _frontmatter(text: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip().strip('"') if match else None


def _anchor_exists(gate: str) -> bool:
    result = subprocess.run(
        ["git", "grep", "-l", "--", gate, "--", *ANCHOR_ROOTS],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def test_an_adr_whose_named_gate_exists_no_longer_says_it_has_none():
    """The flip is mechanical, not remembered."""
    stale = []
    for path in sorted(ADR_DIR.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        if _frontmatter(text, "status") != "Accepted":
            continue
        gate = _verification_gate(text)
        if not gate or not _anchor_exists(gate):
            continue
        declared = _frontmatter(text, "gate")
        binding = _frontmatter(text, "binding")
        if declared in (None, "null") or binding != "true":
            stale.append(
                f"{path.name}: Verification names `{gate}`, which exists in the "
                f"tree, but frontmatter carries gate: {declared} and "
                f"binding: {binding}"
            )

    assert not stale, (
        "these records now have the gate they were waiting for:\n  "
        + "\n  ".join(stale)
        + "\n\nSet gate to the declared name and binding to true, together. While "
        "binding is false, adr_retrieval_health never checks the record's "
        "Decision Contract."
    )


def test_the_prose_half_of_the_flip_is_not_left_behind():
    """A record that carries its gate must not still explain why it has none.

    The frontmatter half of a gate flip is two fields and gets remembered. The
    prose half is a paragraph arguing that `gate: null` was the honest choice,
    and it survives the flip unnoticed -- which leaves the corpus of the tool
    that lints ADR corpora stating that its own enforcement does not exist.

    Keyed on the frontmatter rather than on the gate anchor: once a record
    declares `gate` and `binding: true`, every pending-tense sentence in its
    Verification section is false, whatever the tree looks like.
    """
    stale = []
    for path in sorted(ADR_DIR.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        if _frontmatter(text, "status") != "Accepted":
            continue
        declared = _frontmatter(text, "gate")
        if declared in (None, "null") or _frontmatter(text, "binding") != "true":
            continue
        section = _verification_section(text)
        if section is None:
            continue
        for pattern, complaint in _PENDING_PROSE:
            found = pattern.search(section)
            if found:
                stale.append(
                    f"{path.name}: frontmatter carries gate: {declared} and "
                    f"binding: true, but Verification {complaint} "
                    f"({found.group(0)!r})"
                )

    assert not stale, (
        "these records flipped their frontmatter and kept the paragraph "
        "explaining why they had not:\n  "
        + "\n  ".join(stale)
        + "\n\nRewrite the Verification bullet in the present tense, naming the "
        "file the gate ships in. Both halves of the flip are the flip."
    )


def test_a_declared_gate_that_does_not_exist_yet_is_not_a_finding():
    """gate: null is correct while the anchor is genuinely absent.

    Without this the check would push people to declare a gate name that
    resolves to nothing, which adr-lint then refuses -- trading a silent decay
    for a loud false alarm.
    """
    # Assembled at run time rather than written as a literal: tests/ is in the
    # scan set, so a probe name spelled out here would find itself and the
    # assertion would be inverted by its own source.
    probe = "-".join(["adr", "no", "such", "anchor", "v9"])
    assert not _anchor_exists(probe)


def test_an_adrs_own_verification_bullet_cannot_make_its_gate_exist():
    """docs/ is excluded from the anchor scan, so a record cannot self-satisfy."""
    assert "docs" not in ANCHOR_ROOTS
    assert "backlog" not in ANCHOR_ROOTS
