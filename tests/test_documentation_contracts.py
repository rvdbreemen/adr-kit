"""Regression tests for executable examples in canonical documentation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
# The authority model is shared, never re-stated: validate.yml runs this file in
# a targeted job that does not include tests/test_adr_query.py, so the path
# insert has to live here rather than being inherited.
if str(REPO_ROOT / "bin") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "bin"))

from adr_query import HISTORICAL_STATUSES  # noqa: E402
from client_generation_model import WORKFLOW_IDS  # noqa: E402

ADR_TEMPLATE = REPO_ROOT / "templates" / "adr-template.md"
AGENT_INSTALL = REPO_ROOT / "INSTALL-AGENT.md"
README = REPO_ROOT / "README.md"
PROJECT_GUIDE = REPO_ROOT / "templates" / "adr-kit-guide.md"


# --- README "What's new" contract (TASK-163) --------------------------------
#
# The table documents the releases that change what ADR Kit does, so most
# releases deliberately have no row: 0.43, 0.45, 0.46, 0.47 and 0.49 have none.
# A "the newest CHANGELOG version must appear here" gate would have to be
# defeated on five of the last seven releases, which is ADR-009's failure mode -
# a gate maintainers learn to discount rather than obey.
#
# What is mechanical, and what actually went wrong, is a row that keeps pointing
# a reader at a decision that stopped governing. ADR-018 became Superseded when
# ADR-020 landed in 0.45.0; the 0.44.0 row kept linking it through three
# releases and was still doing so when 0.48.0 deleted the subsystem. It was
# caught by hand after the merge, by no gate at all.

# Any one of these anywhere in the row clears it. Both are satisfiable without a
# successor decision, because a retirement does not always have one.
RETIREMENT_MARKERS = (
    re.compile(r"\bretired in \d+\.\d+\.\d+\b", re.IGNORECASE),
    re.compile(r"\bsuperseded by ADR-\d{3,4}\b", re.IGNORECASE),
)
WHATS_NEW_ROW = re.compile(r"^\| \*\*([^*]+)\*\*\s*\|")
ADR_REFERENCE = re.compile(r"\bADR-\d{3,4}\b")
ADR_STATUS = re.compile(r"^status:\s*\"?([A-Za-z]+)\"?", re.MULTILINE)


def _whats_new_rows(readme_text: str) -> list[tuple[str, str]]:
    """Return (version label, row text) for every row of the table."""
    section = re.search(
        r"^## What's new\b(.*?)^## ", readme_text, re.MULTILINE | re.DOTALL
    )
    assert section, "README has no '## What's new' section; this gate reads nothing"
    rows = []
    for line in section.group(1).splitlines():
        match = WHATS_NEW_ROW.match(line)
        if match:
            rows.append((match.group(1), line))
    return rows


def _adr_status_by_id() -> dict[str, str]:
    statuses = {}
    for path in (REPO_ROOT / "docs" / "adr").glob("ADR-*.md"):
        match = ADR_STATUS.search(path.read_text(encoding="utf-8"))
        if match:
            statuses[path.name.split("-")[0] + "-" + path.name.split("-")[1]] = match.group(1)
    return statuses


def stale_adr_links(readme_text: str, status_by_id: dict[str, str]) -> list[tuple[str, str, str]]:
    """Rows linking an ADR that stopped governing, without saying so."""
    findings = []
    for version, line in _whats_new_rows(readme_text):
        if any(marker.search(line) for marker in RETIREMENT_MARKERS):
            continue
        for adr_id in dict.fromkeys(ADR_REFERENCE.findall(line)):
            status = status_by_id.get(adr_id, "Unknown")
            if status in HISTORICAL_STATUSES:
                findings.append((version, adr_id, status))
    return findings


def test_whats_new_table_never_points_at_a_retired_decision():
    """A row may cite a superseded ADR only if the row says it is superseded.

    Not "the newest release must have a row": most releases deliberately have
    none, and a gate that has to be defeated routinely is one nobody reads.
    """
    readme_text = README.read_text(encoding="utf-8")
    rows = _whats_new_rows(readme_text)
    assert len(rows) >= 8, f"expected the full table, parsed {len(rows)} rows"

    stale = stale_adr_links(readme_text, _adr_status_by_id())
    assert not stale, (
        "README 'What's new' rows link decisions that no longer govern; either "
        "say so in the row (\"retired in X.Y.Z\", \"superseded by ADR-NNN\") or "
        f"drop the link: {stale}"
    )


def test_whats_new_gate_fires_on_a_retired_link_and_stays_quiet_when_marked():
    link = "([ADR-018](docs/adr/ADR-018-x.md))"
    statuses = {"ADR-018": "Superseded", "ADR-036": "Accepted", "ADR-050": "Amended"}

    unmarked = f"## What's new\n\n| **0.44.0** | a vector layer {link} | why |\n\n## Next\n"
    assert stale_adr_links(unmarked, statuses) == [("0.44.0", "ADR-018", "Superseded")]

    for marker in ("retired in 0.48.0", "superseded by ADR-036"):
        marked = f"## What's new\n\n| **0.44.0** | a vector layer {link}, {marker} | why |\n\n## Next\n"
        assert stale_adr_links(marked, statuses) == [], marker

    governing = f"## What's new\n\n| **0.48.0** | lexical ([ADR-036](docs/adr/x.md)) | why |\n\n## Next\n"
    assert stale_adr_links(governing, statuses) == []

    # Amended is historical in bin/adr_query.py, which adr-context also honours.
    amended = "## What's new\n\n| **0.51.0** | thing ([ADR-050](docs/adr/x.md)) | why |\n\n## Next\n"
    assert stale_adr_links(amended, statuses) == [("0.51.0", "ADR-050", "Amended")]


def test_whats_new_links_resolve_to_files_that_still_ship():
    readme_text = README.read_text(encoding="utf-8")
    checked, missing = [], []
    for _version, line in _whats_new_rows(readme_text):
        for target in re.findall(r"\]\((docs/[^)#]+)\)", line):
            checked.append(target)
            if not (REPO_ROOT / target).is_file():
                missing.append(target)
    assert len(checked) >= 12, f"expected the table's links, found {len(checked)}"
    assert not missing, f"README 'What's new' links point at files that are gone: {missing}"


def test_public_json_examples_are_machine_parseable():
    documents = [
        README,
        REPO_ROOT / "INSTALL.md",
        AGENT_INSTALL,
        PROJECT_GUIDE,
        REPO_ROOT / "agents" / "adr-generator.md",
        REPO_ROOT / "skills" / "install-hooks" / "SKILL.md",
        REPO_ROOT / "skills" / "lint" / "SKILL.md",
    ]
    checked = 0
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"```json\s*\n(.*?)```", text, re.DOTALL):
            json.loads(match.group(1))
            checked += 1
    assert checked >= 10


def test_every_generated_adr_index_surface_is_current():
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "bin" / "adr-index"),
            "--check",
            str(REPO_ROOT / "docs" / "adr"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_canonical_template_enforcement_example_is_valid_json():
    text = ADR_TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"## Enforcement.*?```json\s*(.*?)```", text, re.DOTALL)
    assert match is not None

    enforcement = json.loads(match.group(1))
    assert set(enforcement) == {
        "forbid_pattern",
        "forbid_import",
        "require_pattern",
    }
    assert isinstance(enforcement["forbid_pattern"], list)
    assert isinstance(enforcement["forbid_import"], list)
    assert isinstance(enforcement["require_pattern"], list)
    # The scaffold must NOT ship llm_judge. It used to ship `false`, and every
    # ADR in this repository inherited that opt-out verbatim -- which is how a
    # default-on LLM pass ended up with an empty population (TASK-74). Absent
    # means the default, and the default is now true.
    assert "llm_judge" not in enforcement


def test_filled_canonical_template_passes_strict_schema_gate(tmp_path):
    text = ADR_TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("ADR-NNN", "ADR-005")
    text = text.replace("YYYY-MM-DD", "2026-07-18")
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-005-short-imperative-title.md").write_text(
        text,
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "bin" / "adr-lint"),
            "--strict",
            "--gates",
            "schema",
            str(adr_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_readme_prominently_links_the_agent_install_runbook():
    lines = (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if "INSTALL-AGENT.md" in line]
    assert matches
    assert matches[0] < 30


def test_agent_docs_explain_json_graph_discovery_before_source_reading():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    context_skill = (REPO_ROOT / "skills" / "context" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert readme.index("ADR-INDEX.json") < readme.index("## Why")
    for text in (readme, install, context_skill):
        assert "ADR-INDEX.json" in text
        assert "adr-context" in text
        assert "Markdown" in text
    assert "Never hand-edit" in readme
    assert "must never be hand-edited" in install
    assert "Never treat it as the decision authority" in re.sub(
        r"\s+", " ", context_skill
    )


def test_agent_install_runbook_covers_native_and_portable_paths():
    text = AGENT_INSTALL.read_text(encoding="utf-8")
    required = [
        "--detect-only",
        "--dry-run",
        "Claude Code",
        "OpenAI Codex",
        "GitHub Copilot CLI",
        "## Fallback A: MCP",
        "## Fallback B: Agent Skills",
        "## Fallback C: Direct Python commands",
        "adr_context",
        "template.profile",
        "--project-root",
        "adr-migrate --plan",
        "adr-migrate --dry-run",
    ]
    assert all(item in text for item in required)


def test_first_class_client_docs_and_skill_metadata_are_english():
    readme = README.read_text(encoding="utf-8")
    for client in ("Claude Code", "OpenAI Codex", "GitHub Copilot CLI"):
        assert client in readme
    assert "quiet-by-default" in readme

    dutch_markers = re.compile(
        r"\b(?:maak|werk|zoek|controleer|gebruik|voor|naar|nieuwste|bruikbare)\b",
        re.IGNORECASE,
    )
    skill_files = [
        *sorted((REPO_ROOT / "skills").glob("*/SKILL.md")),
        *sorted((REPO_ROOT / "codex" / "skills").glob("*/SKILL.md")),
        *sorted((REPO_ROOT / "copilot" / "skills").glob("*/SKILL.md")),
    ]
    # One skill per workflow, per client. Derived from the registry rather than
    # hardcoded, so adding a workflow does not fail this test with a number
    # that says nothing about the English-metadata contract it is checking.
    assert len(skill_files) == len(WORKFLOW_IDS) * 3
    for path in skill_files:
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        assert match, f"{path} has no description metadata"
        description = match.group(1).strip(" '\"")
        assert description, f"{path} has an empty description"
        assert not dutch_markers.search(description), (
            f"{path} description is not English: {description}"
        )


def test_product_docs_do_not_advertise_removed_client():
    removed_client = "cur" + "sor"
    evidence_directories = {"plans", "research", "reviews", "superpowers"}
    product_docs = [
        path
        for path in sorted((REPO_ROOT / "docs").rglob("*.md"))
        if not evidence_directories.intersection(
            path.relative_to(REPO_ROOT / "docs").parts
        )
    ]
    roots = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "INSTALL.md",
        REPO_ROOT / "INSTALL-AGENT.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "MIGRATING-FROM-ADR-SKILL.md",
        REPO_ROOT / ".claude-plugin" / "plugin.json",
        *product_docs,
        *sorted((REPO_ROOT / "instructions").glob("*.md")),
    ]
    for path in roots:
        assert removed_client not in path.read_text(encoding="utf-8").lower(), (
            f"removed client reference remains in {path}"
        )


def test_shipped_hook_manifests_have_no_routine_progress_messages():
    manifests = [
        REPO_ROOT / ".claude-plugin" / "plugin.json",
        REPO_ROOT / "templates" / "cc-settings" / "guardian-hook-entry.json",
        REPO_ROOT / "codex" / "templates" / "cc-settings" / "guardian-hook-entry.json",
        REPO_ROOT / "copilot" / "templates" / "cc-settings" / "guardian-hook-entry.json",
    ]
    for path in manifests:
        assert "statusMessage" not in path.read_text(encoding="utf-8")


def test_agent_install_runbook_is_prominent_and_client_neutral():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    normalized_install = re.sub(r"\s+", " ", install)

    assert readme.index("[INSTALL-AGENT.md](INSTALL-AGENT.md)") < readme.index(
        "## Why"
    )
    assert "Do not read the full README" in normalized_install
    assert "scripts/install-agent-envs.py --detect-only" in install
    assert "scripts/install-agent-envs.py --dry-run" in install
    assert "scripts/install-agent-envs.py --agents auto" in install

    for native_client in ("Claude Code", "OpenAI Codex", "GitHub Copilot CLI"):
        assert native_client in install
    for portable_surface in ("MCP", "Agent Skills", "Direct Python commands"):
        assert portable_surface in install


def test_agent_install_runbook_has_project_init_and_verification_contracts():
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    normalized_install = re.sub(r"\s+", " ", install)

    assert "/adr-kit:init" in install
    assert "$adr-kit:init" in install
    assert "instead of guessing client configuration" in normalized_install
    assert "<absolute-adr-kit-checkout>" in install
    assert "<absolute-target-project>" in install
    assert "adr_context" in install
    assert "adr-lint --strict" in install
    assert "adr-migrate --plan" in install
    assert "template.profile" in install
    assert (REPO_ROOT / "docs" / "format-migration.md").is_file()

    for relative_path in (
        "scripts/install-agent-envs.py",
        "bin/adr-mcp",
        "instructions/adr.coding.md",
        "instructions/adr.review.md",
    ):
        assert (REPO_ROOT / relative_path).is_file()


def test_template_default_is_explained_for_humans_and_agents():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    project_guide = PROJECT_GUIDE.read_text(encoding="utf-8")

    for text in (readme, install, project_guide):
        assert "no authoritative format census exists" in text.lower()
        assert "agent-reliability" in text.lower()

    assert "### Why MADR is the default" in readme
    assert "4.52/5" in readme
    for text in (readme, install):
        assert "docs/research/adr-format-evaluation.md" in text
        assert "ADR-005-selectable-agent-friendly-adr-formats.md" in text

    assert "## Choosing an ADR body profile" in project_guide
    assert "`nygard`" in project_guide
    assert "`canonical`" in project_guide


def test_agent_docs_use_only_the_shipped_profile_catalog_and_templates():
    readme = README.read_text(encoding="utf-8")
    install = AGENT_INSTALL.read_text(encoding="utf-8")
    project_guide = PROJECT_GUIDE.read_text(encoding="utf-8")

    assert readme.index("adr profiles --format json") < readme.index("## Why")
    for text in (readme, install, project_guide):
        normalized = text.lower()
        assert "adr profiles --format json" in normalized
        assert "madr" in normalized
        assert "nygard" in normalized
        assert "canonical" in normalized
        assert "invent" in normalized

    for client in ("codex", "copilot"):
        skill = (
            REPO_ROOT / client / "skills" / "adr" / "SKILL.md"
        ).read_text(encoding="utf-8").lower()
        assert "adr profiles --format json" in skill
        assert "available: true" in skill
        assert "never invent" in skill


def test_install_docs_define_the_three_platform_runtime_contract():
    readme = README.read_text(encoding="utf-8")
    install = (REPO_ROOT / "INSTALL.md").read_text(encoding="utf-8")
    agent_install = AGENT_INSTALL.read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "validate.yml").read_text(
        encoding="utf-8"
    )

    for text in (readme, install, agent_install):
        assert "Windows" in text
        assert "macOS" in text
        assert "Linux" in text
        assert "Python 3.10" in text
        assert "prepar" in text.lower()

    assert "initialize plus tools/list" in install
    assert "macos-latest" in workflow
    assert "os: [ubuntu-latest, macos-latest, windows-latest]" in workflow
    assert "update the installed `.mcp.json`" not in agent_install.lower()
