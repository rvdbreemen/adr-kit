"""End-to-end coverage for selectable ADR body profiles (TASK-26)."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
TEMPLATES = ROOT / "templates"

sys.path.insert(0, str(BIN))
from adr_format import (  # noqa: E402
    DEFAULT_PROFILE,
    PROFILE_CATALOG,
    SUPPORTED_PROFILES,
    AdrFormatError,
    convert_profile,
    detect_profile,
    profile_catalog,
    profile_template_path,
    required_headings,
    section_text,
)


def run(
    *args: str,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def materialize(profile: str, destination: Path, number: int = 1) -> Path:
    text = (TEMPLATES / f"adr-template.{profile}.md").read_text(encoding="utf-8")
    text = text.replace("ADR-NNN", f"ADR-{number:03d}")
    text = text.replace('"Short Imperative Title"', '"Choose a Queue"')
    text = text.replace("Short Imperative Title", "Choose a Queue")
    text = text.replace("YYYY-MM-DD", "2026-07-18")
    text = text.replace("user@example.com", "test@example.com")
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"ADR-{number:03d}-choose-a-queue.md"
    path.write_text(text, encoding="utf-8")
    return path


def replace_section(path: Path, heading: str, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = rf"(^##\s+{re.escape(heading)}\s*$\n)(.*?)(?=^##\s+|\Z)"
    updated, count = re.subn(
        pattern,
        rf"\g<1>\n{content.strip()}\n\n",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert count == 1
    path.write_text(updated, encoding="utf-8")


def replace_enforcement(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index("```json", text.index("## Enforcement"))
    content_start = text.index("\n", start) + 1
    end = text.index("```", content_start)
    rules = {
        "forbid_pattern": [
            {
                "pattern": r"\bForbiddenSymbol\b",
                "path_glob": "src/**/*.py",
                "message": "Use AllowedSymbol instead.",
            }
        ],
        "forbid_import": [],
        "require_pattern": [],
        "llm_judge": False,
    }
    updated = text[:content_start] + json.dumps(rules, indent=2) + "\n" + text[end:]
    path.write_text(updated, encoding="utf-8")


def test_every_profile_has_a_deterministic_template_and_semantic_roles(tmp_path):
    assert SUPPORTED_PROFILES == ("madr", "nygard", "canonical")
    for index, profile in enumerate(SUPPORTED_PROFILES, start=1):
        path = materialize(profile, tmp_path / profile, index)
        text = path.read_text(encoding="utf-8")
        assert detect_profile(text) == profile
        assert all(heading in text for heading in required_headings(profile))
        assert section_text(text, "context")
        assert section_text(text, "decision")
        assert section_text(text, "alternatives")
        assert section_text(text, "consequences")


def test_profile_catalog_is_complete_ordered_and_marks_only_madr_preferred():
    assert tuple(PROFILE_CATALOG) == SUPPORTED_PROFILES
    assert DEFAULT_PROFILE == "madr"
    catalog = profile_catalog(TEMPLATES)
    assert [item["id"] for item in catalog] == list(SUPPORTED_PROFILES)
    assert [item["id"] for item in catalog if item["preferred"]] == ["madr"]
    assert all(item["available"] for item in catalog)
    assert all(Path(str(item["template"])).is_file() for item in catalog)


def test_profile_template_path_rejects_unsupported_and_missing_templates(tmp_path):
    with pytest.raises(AdrFormatError, match="unsupported ADR format"):
        profile_template_path("invented", TEMPLATES)
    with pytest.raises(AdrFormatError, match="shipped ADR profile 'madr' is unavailable"):
        profile_template_path("madr", tmp_path)


def test_adr_new_checks_the_shipped_template_before_creating_project_files(tmp_path):
    installed = tmp_path / "installed"
    installed_bin = installed / "bin"
    installed_bin.mkdir(parents=True)
    for name in ("adr", "adr_format.py", "adr_schema.py"):
        shutil.copy2(BIN / name, installed_bin / name)
    (installed / "templates").mkdir()

    adr_dir = tmp_path / "project" / "docs" / "adr"
    result = run(
        str(installed_bin / "adr"),
        "new",
        "Unavailable Profile",
        "--adr-dir",
        str(adr_dir),
    )

    assert result.returncode == 2
    assert "shipped ADR profile 'madr' is unavailable" in result.stderr
    assert not adr_dir.exists()


def test_adr_profiles_exposes_agent_readable_human_and_json_catalog():
    human = run(str(BIN / "adr"), "profiles")
    assert human.returncode == 0, human.stderr
    assert "only these identifiers are selectable" in human.stdout
    assert "madr (preferred)" in human.stdout
    assert "do not invent profile names" in human.stdout
    assert all(f"- {profile}" in human.stdout for profile in SUPPORTED_PROFILES)

    machine = run(str(BIN / "adr"), "profiles", "--format", "json")
    assert machine.returncode == 0, machine.stderr
    payload = json.loads(machine.stdout)
    assert payload["default"] == "madr"
    assert payload["all_templates_available"] is True
    assert [item["id"] for item in payload["profiles"]] == list(SUPPORTED_PROFILES)
    assert all(item["available"] for item in payload["profiles"])


def test_every_profile_is_detected_without_declared_frontmatter():
    for profile in SUPPORTED_PROFILES:
        text = (TEMPLATES / f"adr-template.{profile}.md").read_text(encoding="utf-8")
        text = re.sub(r'^format: "[^"]+"\n', "", text, count=1, flags=re.MULTILINE)
        assert detect_profile(text) == profile


def test_default_template_is_madr_and_json_examples_are_valid():
    default = (TEMPLATES / "adr-template.md").read_text(encoding="utf-8")
    assert detect_profile(default) == "madr"
    enforcement = section_text(default, "enforcement")
    raw = enforcement.split("```json", 1)[1].split("```", 1)[0]
    assert isinstance(json.loads(raw), dict)


def test_client_templates_and_skills_publish_the_same_profile_contract():
    client_roots = (ROOT, ROOT / "codex", ROOT / "copilot")
    for profile in SUPPORTED_PROFILES:
        expected = (TEMPLATES / f"adr-template.{profile}.md").read_text(
            encoding="utf-8"
        )
        for client in client_roots[1:]:
            actual = (client / "templates" / f"adr-template.{profile}.md").read_text(
                encoding="utf-8"
            )
            assert actual.replace("\r\n", "\n") == expected.replace("\r\n", "\n")

    skill_paths = [
        ROOT / "skills" / name / "SKILL.md"
        for name in ("adr", "migrate")
    ]
    skill_paths.extend(
        client / "skills" / name / "SKILL.md"
        for client in client_roots[1:]
        for name in ("adr", "migrate")
    )
    for path in skill_paths:
        text = path.read_text(encoding="utf-8").lower()
        assert all(profile in text for profile in SUPPORTED_PROFILES), path
        assert "madr" in text and ("default" in text or "--to-profile madr" in text)
        if path.parent.name == "adr":
            assert "adr profiles --format json" in text, path
            assert "available: true" in text, path


def test_adr_new_uses_madr_default_config_and_cli_override(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    result = run(
        str(BIN / "adr"),
        "new",
        "Default Record",
        "--adr-dir",
        str(adr_dir),
        "--date",
        "2026-07-18",
    )
    assert result.returncode == 0, result.stderr
    first = next(adr_dir.glob("ADR-001-*.md"))
    assert detect_profile(first.read_text(encoding="utf-8")) == "madr"

    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"template": {"profile": "nygard"}}), encoding="utf-8"
    )
    result = run(
        str(BIN / "adr"),
        "new",
        "Configured Record",
        "--adr-dir",
        str(adr_dir),
        "--date",
        "2026-07-18",
    )
    assert result.returncode == 0, result.stderr
    second = next(adr_dir.glob("ADR-002-*.md"))
    assert detect_profile(second.read_text(encoding="utf-8")) == "nygard"

    result = run(
        str(BIN / "adr"),
        "new",
        "Override Record",
        "--adr-dir",
        str(adr_dir),
        "--profile",
        "canonical",
        "--date",
        "2026-07-18",
    )
    assert result.returncode == 0, result.stderr
    third = next(adr_dir.glob("ADR-003-*.md"))
    assert detect_profile(third.read_text(encoding="utf-8")) == "canonical"


def test_lint_index_context_and_judge_read_every_profile(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    for index, profile in enumerate(SUPPORTED_PROFILES, start=1):
        path = materialize(profile, adr_dir, index)
        replace_enforcement(path)
        if index == 2:
            replace_section(path, "Related Decisions", "- Related to ADR-001.")
        accepted = run(
            str(BIN / "adr"),
            "accept",
            f"ADR-{index:03d}",
            "--adr-dir",
            str(adr_dir),
            "--date",
            "2026-07-18",
        )
        assert accepted.returncode == 0, accepted.stderr
        assert detect_profile(path.read_text(encoding="utf-8")) == profile

    lint = run(str(BIN / "adr-lint"), "--strict", "--format", "json", str(adr_dir))
    payload = json.loads(lint.stdout)
    assert payload["summary"]["fail"] == 0, payload

    index = run(
        str(BIN / "adr-index"),
        "--adr-dir",
        str(adr_dir),
        "--format",
        "json",
    )
    rows = json.loads(index.stdout)
    assert len(rows) == 3
    assert all(row["decision"] for row in rows)
    assert {row["format"] for row in rows} == set(SUPPORTED_PROFILES)

    graph_result = run(
        str(BIN / "adr-index"),
        "--adr-dir",
        str(adr_dir),
        "--format",
        "graph",
    )
    graph = json.loads(graph_result.stdout)
    assert graph["schema_version"] == 1
    assert {node["format"] for node in graph["adrs"]} == set(SUPPORTED_PROFILES)
    assert all(node["decision_summary"] for node in graph["adrs"])

    context = run(
        str(BIN / "adr-context"),
        "--adr-dir",
        str(adr_dir),
        "--format",
        "json",
        "chosen queue option",
    )
    ranked = json.loads(context.stdout)
    assert len(ranked) == 3

    diff = """\
diff --git a/src/example.py b/src/example.py
--- a/src/example.py
+++ b/src/example.py
@@ -0,0 +1 @@
+ForbiddenSymbol
"""
    judge = run(
        str(BIN / "adr-judge"),
        "--adr-dir",
        str(adr_dir),
        "--diff",
        "-",
        "--repo-root",
        str(tmp_path),
        "--json",
        cwd=tmp_path,
        input_text=diff,
    )
    assert judge.returncode == 1, judge.stderr + judge.stdout
    judged = json.loads(judge.stdout)
    assert judged["summary"]["violations"] == 3
    assert {finding["adr"] for finding in judged["findings"]} == {
        "ADR-001",
        "ADR-002",
        "ADR-003",
    }

    related = run(
        str(BIN / "adr-related"),
        "ADR-002",
        "--adr-dir",
        str(adr_dir),
        "--format",
        "json",
    )
    graph = json.loads(related.stdout)
    assert related.returncode == 0, related.stderr
    assert any(edge["adr_id"] == "ADR-001" for edge in graph["outbound"])
    assert graph["dangling"] == []

    retired = run(
        str(BIN / "adr-retire"),
        str(adr_dir),
        "--repo-root",
        str(tmp_path),
        "--format",
        "json",
    )
    assert retired.returncode == 0, retired.stderr
    assert {row["adr_id"] for row in json.loads(retired.stdout)} == {
        "ADR-001",
        "ADR-002",
        "ADR-003",
    }

    doctor = run(
        str(BIN / "adr-doctor"),
        str(adr_dir),
        "--repo-root",
        str(tmp_path),
        "--fix-index",
        "--format",
        "json",
    )
    health = json.loads(doctor.stdout)
    assert doctor.returncode == 0, doctor.stderr + doctor.stdout
    assert health["exit_code"] == 0


@pytest.mark.parametrize("profile", SUPPORTED_PROFILES)
def test_supersession_mutates_each_profile_without_changing_its_body_contract(
    tmp_path, profile: str
):
    adr_dir = tmp_path / "docs" / "adr"
    old = materialize(profile, adr_dir, 1)
    new = materialize(profile, adr_dir, 2)
    accepted = run(
        str(BIN / "adr"),
        "accept",
        "ADR-001",
        "--adr-dir",
        str(adr_dir),
        "--date",
        "2026-07-18",
    )
    assert accepted.returncode == 0, accepted.stderr

    superseded = run(
        str(BIN / "adr"),
        "supersede",
        "ADR-001",
        "--by",
        "ADR-002",
        "--adr-dir",
        str(adr_dir),
        "--date",
        "2026-07-18",
    )
    assert superseded.returncode == 0, superseded.stderr
    old_text = old.read_text(encoding="utf-8")
    new_text = new.read_text(encoding="utf-8")
    assert detect_profile(old_text) == profile
    assert detect_profile(new_text) == profile
    assert 'status: "Superseded"' in old_text
    assert 'superseded_by: "ADR-002"' in old_text
    assert '  - "ADR-001"' in new_text

    graph = run(
        str(BIN / "adr-related"),
        "ADR-001",
        "--adr-dir",
        str(adr_dir),
        "--format",
        "json",
    )
    payload = json.loads(graph.stdout)
    assert graph.returncode == 0, graph.stderr
    assert payload["dangling"] == []
    assert any(edge["adr_id"] == "ADR-002" for edge in payload["outbound"])


@pytest.mark.parametrize("source", SUPPORTED_PROFILES)
@pytest.mark.parametrize("target", SUPPORTED_PROFILES)
def test_profile_migration_is_dry_run_safe_and_idempotent(
    tmp_path, source: str, target: str
):
    adr_dir = tmp_path / "docs" / "adr"
    path = materialize(source, adr_dir)
    before = path.read_text(encoding="utf-8")

    dry = run(
        str(BIN / "adr-migrate"),
        "--dry-run",
        "--to-profile",
        target,
        str(path),
    )
    assert dry.returncode == 0, dry.stderr
    assert path.read_text(encoding="utf-8") == before

    write = run(
        str(BIN / "adr-migrate"),
        "--to-profile",
        target,
        str(path),
    )
    assert write.returncode == 0, write.stderr
    after = path.read_text(encoding="utf-8")
    assert detect_profile(after) == target
    assert section_text(after, "decision") == section_text(before, "decision")
    assert section_text(after, "enforcement") == section_text(before, "enforcement")

    check = run(
        str(BIN / "adr-migrate"),
        "--check",
        "--to-profile",
        target,
        str(path),
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_hybrid_is_explicit_and_strict_lint_rejects_it(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    path = materialize("canonical", adr_dir)
    text = path.read_text(encoding="utf-8")
    text = text.replace('format: "canonical"\n', "")
    text = text.replace(
        "## Context\n",
        "## Context\n\nCanonical.\n\n## Context and Problem Statement\n",
    )
    text = text.replace(
        "## Decision\n",
        "## Decision\n\nCanonical.\n\n## Decision Outcome\n",
    )
    path.write_text(text, encoding="utf-8")
    assert detect_profile(text) == "hybrid"

    lint = run(str(BIN / "adr-lint"), "--strict", "--format", "json", str(path))
    payload = json.loads(lint.stdout)
    assert lint.returncode == 1
    assert "format is hybrid" in payload["files"][0]["findings"][0]["summary"]


def test_unsupported_config_profile_is_an_actionable_error(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    materialize("canonical", adr_dir)
    config = adr_dir / ".adr-kit.json"
    config.write_text(
        json.dumps({"template": {"profile": "free-form"}}), encoding="utf-8"
    )
    lint = run(
        str(BIN / "adr-lint"),
        "--config",
        str(config),
        str(adr_dir),
    )
    assert lint.returncode == 2
    assert "template.profile='free-form' is unsupported" in lint.stderr


def test_migration_rejects_a_conflicting_explicit_source_profile(tmp_path):
    path = materialize("canonical", tmp_path / "docs" / "adr")
    result = run(
        str(BIN / "adr-migrate"),
        "--from-profile",
        "madr",
        "--to-profile",
        "nygard",
        str(path),
    )
    assert result.returncode == 2
    assert "conflicts with declared format" in result.stdout + result.stderr
    assert detect_profile(path.read_text(encoding="utf-8")) == "canonical"


def test_unknown_declared_profile_is_rejected_by_strict_lint(tmp_path):
    path = materialize("canonical", tmp_path / "docs" / "adr")
    text = path.read_text(encoding="utf-8").replace(
        'format: "canonical"', 'format: "free-form"'
    )
    path.write_text(text, encoding="utf-8")
    assert detect_profile(text) == "unknown"
    lint = run(str(BIN / "adr-lint"), "--strict", "--format", "json", str(path))
    assert lint.returncode == 1
    payload = json.loads(lint.stdout)
    findings = payload["files"][0]["findings"]
    assert any("format is unknown" in finding["summary"] for finding in findings)


def test_detect_profile_is_memoized_for_repeated_document_scans():
    """detect_profile is a pure whole-document scan invoked several times per
    ADR (directly and through section_text). Memoizing it removes that
    redundant parse; this guards the hot-path win so it cannot silently regress
    into re-parsing on every call.
    """
    text = (
        "---\nformat: madr\n---\n\n"
        "# ADR-001 Memoized scan\n\n"
        "## Status\n\nAccepted\n\n"
        "## Context and Problem Statement\n\nWhy.\n\n"
        "## Decision Outcome\n\nDo it.\n"
    )

    detect_profile.cache_clear()
    first = detect_profile(text)
    after_first = detect_profile.cache_info()
    second = detect_profile(text)
    after_second = detect_profile.cache_info()

    assert first == second == "madr"
    # The first call was a miss; the repeat is served from cache with no
    # additional whole-document parse.
    assert after_first.misses == 1
    assert after_second.hits == after_first.hits + 1
    assert after_second.misses == after_first.misses
