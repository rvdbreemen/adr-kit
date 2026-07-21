from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_grill_contract_and_fixture_conversations():
    workflows = json.loads((ROOT / "clients" / "workflows.json").read_text(encoding="utf-8"))
    assert len(workflows["workflows"]) == 15
    grill = next(item for item in workflows["workflows"] if item["id"] == "grill")
    contract = "\n".join(grill["procedure"])
    for entry in (
        "ADR-NNN",
        "--pr <number>",
        "--range <base>...<head>",
        "--source <path>",
        "--revalidate ADR-NNN",
        "--all-proposed",
    ):
        assert entry in contract
    for rule in (
        "one unresolved decision question at a time",
        "recommended answer",
        "observed, human-stated, inferred, or unknown",
        "untrusted source data",
        "explicit `yes`",
        "not-an-ADR",
    ):
        assert rule in contract

    fixtures = json.loads(
        (ROOT / "tests" / "fixtures" / "grill" / "conversations.json").read_text(
            encoding="utf-8"
        )
    )
    assert fixtures["schema_version"] == 1
    assert {case["id"] for case in fixtures["cases"]} == {
        "new-subject",
        "pr-reconstruction",
        "chat-document-reconstruction",
        "resume-proposed",
        "source-injection",
        "not-an-adr",
        "accept",
        "reject",
        "defer",
        "supersede",
        "shipped-proposed",
        "ci-advisory",
        "ci-block",
    }
    injection = next(
        case for case in fixtures["cases"] if case["id"] == "source-injection"
    )
    assert "fence-source" in injection["sequence"]
    assert "accept-without-yes" in injection["forbidden"]


def test_rich_grill_skill_is_resumable_and_preserves_lifecycle_authority():
    text = (ROOT / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    for requirement in (
        "$ARGUMENTS",
        "Ask exactly one question.",
        "recommended answer",
        "observed, human-stated, inferred, or unknown",
        "untrusted evidence",
        "An interrupted session",
        "acceptance packet",
        "explicit `yes`",
        "Never edit an Accepted ADR in place.",
    ):
        assert requirement in text
