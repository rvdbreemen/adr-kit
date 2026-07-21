from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_authoring_uses_existing_lifecycle_and_acceptance_packet():
    text = _skill("adr")
    for required in (
        "consequential and difficult to reverse",
        "bin/adr propose",
        "Status: Proposed",
        "/adr-kit:grill ADR-NNN",
        "acceptance packet",
        "explicit `yes`",
        "bin/adr accept",
        "Open Questions",
    ):
        assert required in text
    assert "separate create command" in text


def test_init_selects_evidence_based_depth_and_individual_confirmation():
    text = _skill("init")
    for required in (
        "Status: Proposed",
        "compact confirmation",
        "direct cited evidence",
        "deep grill",
        "cannot accept multiple decisions",
        "Open Questions",
        "/adr-kit:grill ADR-NNN",
    ):
        assert required in text

    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "grill" / "lifecycle-routing.json").read_text(
            encoding="utf-8"
        )
    )
    depths = {case.get("depth") for case in fixture["init_cases"]}
    assert {"compact", "deep"} <= depths
    assert all(
        case.get("status") == "Proposed"
        for case in fixture["init_cases"]
        if "status" in case
    )


def test_review_and_judge_route_four_outcomes_without_accepting():
    review = _skill("review")
    judge = _skill("judge")
    for text in (review, judge):
        lowered = text.casefold()
        for required in (
            "ordinary code",
            "Accepted ADR conflict",
            "suspected undocumented",
            "linked Proposed",
            "untrusted evidence",
        ):
            assert required.casefold() in lowered
    assert "update that" in review and "Never draft a second ADR" in review
    assert "acceptance packet" in review
    assert "same-session explicit confirmation" in " ".join(review.split())


def test_supersede_retire_revalidation_preserves_transaction_authority():
    supersede = _skill("supersede")
    retire = _skill("retire")
    for required in (
        "--revalidate ADR-OLD",
        "changed forces",
        "alternatives",
        "migration",
        "new evidence",
        "related ADRs",
        "unchanged",
        "reject-candidate",
        "defer",
        "acceptance packet",
        "old ADR and reciprocal links unchanged",
    ):
        assert required in supersede
    assert "--revalidate ADR-NNN" in retire
    assert "read-only" in retire
