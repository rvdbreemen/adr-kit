"""Real-world compatibility checks against the frozen OTGW-firmware ADR set."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = ROOT / "tests" / "testsets" / "otgw-firmware"
ADR_DIR = CORPUS_ROOT / "adrs"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"
ADR_NAME_RE = re.compile(r"^ADR-\d{3,4}-.*\.md$", re.IGNORECASE)


def _run(script: str, *args: object) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / script), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(ROOT),
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"{script} returned invalid JSON\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        ) from exc
    return result.returncode, payload


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _frozen_hashes() -> dict[str, str]:
    return {
        path.name: _digest(path)
        for path in sorted(ADR_DIR.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and ADR_NAME_RE.match(path.name)
    }


@pytest.fixture(scope="module")
def plan_payload() -> dict:
    code, payload = _run(
        "adr-migrate",
        "--plan",
        "--format",
        "json",
        ADR_DIR,
    )
    assert code == 0
    return payload


def test_manifest_pins_exact_byte_preserved_corpus():
    manifest = _manifest()
    files = sorted(
        path for path in ADR_DIR.iterdir() if path.is_file()
    )
    expected_paths = [entry["path"] for entry in manifest["files"]]

    assert manifest["schema_version"] == 1
    assert manifest["corpus"] == "otgw-firmware-adrs"
    assert manifest["license"] == "GPL-3.0-only"
    assert manifest["source"]["repository_url"].endswith(
        "rvdbreemen/OTGW-firmware.git"
    )
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["source"]["revision"])
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["source"]["adr_tree_revision"])
    assert manifest["source"]["path"] == "docs/adr"
    assert manifest["source"]["numbered_adrs_clean"] is True
    assert len(files) == manifest["baseline"]["file_count"] == 169
    assert all(ADR_NAME_RE.match(path.name) for path in files)
    assert expected_paths == sorted(expected_paths, key=str.casefold)
    assert {f"adrs/{path.name}" for path in files} == set(expected_paths)
    assert not any(path.name.startswith("ADR-INDEX") for path in files)

    total_bytes = 0
    for entry in manifest["files"]:
        path = CORPUS_ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert _digest(path) == entry["sha256"]
        total_bytes += entry["bytes"]
    assert total_bytes == manifest["baseline"]["total_bytes"] == 1_946_079
    assert (CORPUS_ROOT / "LICENSE").read_text(
        encoding="utf-8"
    ).lstrip().startswith("GNU GENERAL PUBLIC LICENSE")

    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "tests/testsets/otgw-firmware/adrs/*.md -text" in attributes
    assert "tests/testsets/otgw-firmware/LICENSE -text" in attributes


def test_migration_plan_matches_reviewed_baseline_without_writes(plan_payload):
    manifest = _manifest()
    before = _frozen_hashes()
    summary = plan_payload["summary"]
    files = plan_payload["files"]
    actual = {
        "format_counts": dict(
            sorted(Counter(item["detected_format"] for item in files).items())
        ),
        "action_counts": dict(
            sorted(Counter(item["action"] for item in files).items())
        ),
        "deterministic": summary["deterministic"],
        "guided": summary["guided"],
        "notices": summary["notices"],
    }

    assert plan_payload["read_only"] is True
    assert summary["total"] == manifest["baseline"]["file_count"]
    assert actual == manifest["baseline"]["migration_plan"]
    assert _frozen_hashes() == before


def test_metadata_dry_run_is_read_only_and_failures_are_actionable():
    manifest = _manifest()
    before = _frozen_hashes()
    code, payload = _run(
        "adr-migrate",
        "--dry-run",
        "--format",
        "json",
        ADR_DIR,
    )
    expected = manifest["baseline"]["metadata_dry_run"]
    failures = [item for item in payload["files"] if not item["ok"]]

    assert code == expected["exit_code"]
    assert payload["mode"] == "dry-run"
    assert payload["summary"] == {
        "total": manifest["baseline"]["file_count"],
        "changed": expected["changed"],
        "failed": expected["failed"],
    }
    assert len(failures) == expected["failed"]
    assert all(item["issues"] for item in failures)
    assert all(
        any(
            keyword in issue
            for keyword in ("status", "supersedes", "superseded_by")
        )
        for item in failures
        for issue in item["issues"]
    )
    assert _frozen_hashes() == before


def test_deterministic_subset_migrates_to_madr_idempotently(
    tmp_path, plan_payload
):
    manifest = _manifest()
    before = _frozen_hashes()
    target = tmp_path / "adrs"
    target.mkdir()
    deterministic = [
        item for item in plan_payload["files"] if item["deterministic"]
    ]
    for item in deterministic:
        name = Path(item["file"]).name
        shutil.copyfile(ADR_DIR / name, target / name)

    assert len(list(target.glob("ADR-*.md"))) == (
        manifest["baseline"]["migration_plan"]["deterministic"]
    )

    metadata_code, metadata = _run("adr-migrate", "--format", "json", target)
    convert_code, converted = _run(
        "adr-migrate",
        "--to-profile",
        "madr",
        "--format",
        "json",
        target,
    )
    check_code, checked = _run(
        "adr-migrate",
        "--check",
        "--to-profile",
        "madr",
        "--format",
        "json",
        target,
    )

    expected_count = len(deterministic)
    assert metadata_code == 0
    assert metadata["summary"] == {
        "total": expected_count,
        "changed": expected_count,
        "failed": 0,
    }
    assert convert_code == 0
    assert converted["summary"] == {
        "total": expected_count,
        "changed": expected_count,
        "failed": 0,
    }
    assert check_code == 0
    assert checked["summary"] == {
        "total": expected_count,
        "changed": 0,
        "failed": 0,
    }
    assert all(
        'format: "madr"' in path.read_text(encoding="utf-8")
        for path in target.glob("ADR-*.md")
    )
    assert _frozen_hashes() == before


def test_index_context_related_and_lint_process_the_whole_corpus():
    manifest = _manifest()
    expected_count = manifest["baseline"]["file_count"]

    list_code, index = _run(
        "adr-index",
        "--adr-dir",
        ADR_DIR,
        "--format",
        "json",
    )
    assert list_code == 0
    assert len(index) == expected_count
    assert len({item["adr_id"] for item in index}) == expected_count

    index_code, graph = _run(
        "adr-index",
        "--adr-dir",
        ADR_DIR,
        "--format",
        "graph",
    )
    assert index_code == 0
    assert graph["schema_version"] == 2
    assert len(graph["adrs"]) == expected_count
    assert len({node["id"] for node in graph["adrs"]}) == expected_count
    assert all(ADR_NAME_RE.match(node["path"]) for node in graph["adrs"])
    assert Counter(node["format"] for node in graph["adrs"]) == Counter(
        manifest["baseline"]["migration_plan"]["format_counts"]
    )
    assert graph["relationships"]

    context_code, context = _run(
        "adr-context",
        "--adr-dir",
        ADR_DIR,
        "--format",
        "json",
        "--limit",
        "5",
        "MQTT Home Assistant discovery",
    )
    assert context_code == 0
    assert 1 <= len(context) <= 5
    corpus_path = ADR_DIR.as_posix().casefold().rstrip("/") + "/"
    assert all(
        item["path"].replace("\\", "/").casefold().startswith(corpus_path)
        for item in context
    )
    assert all(item["decision_summary"] for item in context)

    related_code, related = _run(
        "adr-related",
        "ADR-169",
        "--adr-dir",
        ADR_DIR,
        "--format",
        "json",
    )
    assert related_code == 0
    assert related["adr"]["adr_id"] == "ADR-169"
    assert related["outbound"]

    lint_code, lint = _run(
        "adr-lint",
        "--format",
        "json",
        ADR_DIR,
    )
    assert lint_code in {0, 1}
    assert lint["summary"]["total"] == expected_count
    assert (
        lint["summary"]["pass"]
        + lint["summary"]["advisory"]
        + lint["summary"]["fail"]
        + lint["summary"]["skipped"]
        == expected_count
    )
    assert len(lint["migration_notices"]) == expected_count
