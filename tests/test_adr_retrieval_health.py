"""Project-level selective-context probes and health reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))

from adr_retrieval_health import run_retrieval_health  # noqa: E402
from adr_schema import render_frontmatter  # noqa: E402


def _node(
    adr_id: str,
    *,
    title: str,
    status: str = "Accepted",
    binding: bool = False,
    topics: list[str] | None = None,
    context_scope: str = "selective",
) -> dict:
    return {
        "id": adr_id,
        "title": title,
        "path": f"{adr_id}-{title.lower().replace(' ', '-')}.md",
        "format": "madr",
        "status": status,
        "date": "2026-07-23",
        "decision_summary": f"Use {title.lower()}.",
        "topics": topics or [],
        "aliases": [],
        "components": [],
        "symbols": [],
        "context_scope": context_scope,
        "decision_contract": {
            "must": [],
            "must_not": [],
            "exceptions": [],
            "verification": [],
        },
        "scope": {"path_globs": []},
        "metadata": {
            "binding": binding,
            "gate": None,
            "documents_shipped": False,
            "verified_in": [],
            "supersedes": [],
            "superseded_by": None,
        },
    }


def _write_graph(adr_dir: Path) -> None:
    adr_dir.mkdir(parents=True)
    payload = {
        "schema_version": 2,
        "adrs": [
            _node(
                "ADR-001",
                title="Indexed Retrieval",
                binding=True,
                topics=["selective context"],
            ),
            _node(
                "ADR-002",
                title="Missing Metadata",
                binding=True,
            ),
            _node(
                "ADR-003",
                title="Historical Retrieval",
                status="Rejected",
                topics=["selective context"],
            ),
        ],
        "relationships": [],
    }
    (adr_dir / "ADR-INDEX.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_probes(adr_dir: Path, expected: str = "ADR-001") -> Path:
    path = adr_dir / "adr-context-probes.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "probes": [
                    {
                        "id": "selective-context",
                        "query": "selective context",
                        "topics": ["selective context"],
                        "limit": 3,
                        "expect": {
                            "include": [expected],
                            "exclude": ["ADR-003"],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_probe_schema_and_dogfood_file_validate():
    schema = json.loads(
        (ROOT / "schemas" / "adr-context-probes.schema.json").read_text(
            encoding="utf-8"
        )
    )
    payload = json.loads(
        (ROOT / "docs" / "adr" / "adr-context-probes.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(payload, schema)


def test_probe_pass_and_metadata_advisory_are_read_only(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_graph(adr_dir)
    _write_probes(adr_dir)
    before = (adr_dir / "ADR-INDEX.json").read_bytes()

    health = run_retrieval_health(adr_dir)

    assert health["status"] == "pass"
    assert health["probes"]["summary"] == {"total": 1, "pass": 1, "fail": 0}
    assert health["probes"]["results"][0]["historical_leakage"] == []
    assert health["metadata_findings"][0]["adr_id"] == "ADR-002"
    assert health["metadata_findings"][0]["level"] == "ADVISORY"
    assert (adr_dir / "ADR-INDEX.json").read_bytes() == before


def test_probe_failure_explains_expected_actual_authority_and_matches(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_graph(adr_dir)
    _write_probes(adr_dir, expected="ADR-002")

    health = run_retrieval_health(adr_dir)
    failure = health["probes"]["results"][0]

    assert health["status"] == "fail"
    assert failure["missing"] == ["ADR-002"]
    assert failure["actual"][0]["adr_id"] == "ADR-001"
    assert failure["actual"][0]["authority"] == "governing"
    assert failure["actual"][0]["matches"]


def test_retrieval_completeness_is_strict_only_when_opted_in(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    _write_graph(adr_dir)

    advisory = run_retrieval_health(
        adr_dir,
        config={"context": {"retrieval_completeness": "advisory"}},
    )
    strict = run_retrieval_health(
        adr_dir,
        config={"context": {"retrieval_completeness": "strict"}},
    )
    off = run_retrieval_health(
        adr_dir,
        config={"context": {"retrieval_completeness": "off"}},
    )

    assert advisory["status"] == "pass"
    assert advisory["metadata_findings"][0]["level"] == "ADVISORY"
    assert strict["status"] == "fail"
    assert strict["metadata_findings"][0]["level"] == "FAIL"
    assert off["metadata_findings"] == []


def test_lint_metadata_finding_defaults_advisory_and_can_be_strict(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    data = {
        "id": "ADR-001",
        "title": "Binding Without Retrieval Metadata",
        "status": "Accepted",
        "date": "2026-07-23",
        "binding": True,
        "gate": "example-gate",
        "documents_shipped": False,
        "verified_in": [],
        "supersedes": [],
        "superseded_by": None,
        "format": "madr",
    }
    path = adr_dir / "ADR-001-binding-without-retrieval-metadata.md"
    path.write_text(
        render_frontmatter(data)
        + "# ADR-001 Binding Without Retrieval Metadata\n\n"
        + "## Status\n\nAccepted, 2026-07-23.\n",
        encoding="utf-8",
    )
    config = adr_dir / ".adr-kit.json"

    outcomes = {}
    for mode in ("advisory", "strict"):
        config.write_text(
            json.dumps({"context": {"retrieval_completeness": mode}}),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(BIN / "adr-lint"),
                "--gates",
                "policy",
                "--format",
                "json",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        outcomes[mode] = (result.returncode, json.loads(result.stdout))

    assert outcomes["advisory"][0] == 0
    assert outcomes["advisory"][1]["files"][0]["bucket"] == "ADVISORY"
    assert outcomes["strict"][0] == 1
    finding = outcomes["strict"][1]["files"][0]["findings"][0]
    assert finding["code"] == "SELECTIVE_CONTEXT_METADATA"
    assert finding["level"] == "FAIL"


def test_doctor_status_guardian_and_context_surface_dogfood_health():
    context = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-context"),
            "--check-probes",
            "--format",
            "json",
            "--adr-dir",
            "docs/adr",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    doctor = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-doctor"),
            "--check",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    status = subprocess.run(
        [sys.executable, str(BIN / "adr-status"), "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    state = ROOT / "docs" / "adr" / ".adr-kit-state.json"
    before = state.read_bytes() if state.is_file() else None
    guardian = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-guardian"),
            "retrieval-health",
            "--format",
            "json",
            "--adr-dir",
            "docs/adr",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    after = state.read_bytes() if state.is_file() else None

    assert context.returncode == status.returncode == 0
    # Doctor may also report unrelated accepted-evidence drift from the active
    # working tree; retrieval health remains independently inspectable.
    assert doctor.returncode in {0, 1}
    assert guardian.returncode == 0
    assert json.loads(context.stdout)["probes"]["summary"]["fail"] == 0
    assert json.loads(doctor.stdout)["adr"]["retrieval"]["status"] == "pass"
    assert json.loads(status.stdout)["retrieval"]["status"] == "pass"
    assert json.loads(guardian.stdout)["status"] == "pass"
    assert after == before


def test_representative_otgw_project_probes_pass_without_historical_leakage(
    tmp_path,
):
    corpus = ROOT / "tests" / "testsets" / "otgw-firmware" / "adrs"
    generated = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-index"),
            "--adr-dir",
            str(corpus),
            "--format",
            "graph",
            "--output",
            str(tmp_path / "ADR-INDEX.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert generated.returncode == 0, generated.stderr
    expected = {
        "mqtt-source-topics": ("mqtt source specific topics", "ADR-040"),
        "wifi-reconnect": ("wifi reconnect timeout tuning", "ADR-075"),
        "retained-discovery": ("retained discovery verification", "ADR-062"),
        "heap-contract": ("heap tier machine contract", "ADR-089"),
        "summary-parsing": ("ps1 print summary parsing", "ADR-045"),
    }
    (tmp_path / "adr-context-probes.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "probes": [
                    {
                        "id": probe_id,
                        "query": query,
                        "limit": 3,
                        "expect": {"include": [adr_id], "exclude": []},
                    }
                    for probe_id, (query, adr_id) in expected.items()
                ],
            }
        ),
        encoding="utf-8",
    )

    health = run_retrieval_health(
        tmp_path,
        config={"context": {"retrieval_completeness": "off"}},
    )

    assert health["status"] == "pass"
    assert health["probes"]["summary"] == {"total": 5, "pass": 5, "fail": 0}
    assert all(
        not result["historical_leakage"]
        for result in health["probes"]["results"]
    )


def test_retrieval_migration_suggestions_are_dry_run_and_human_gated(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    data = {
        "id": "ADR-001",
        "title": "Use Local Queue Worker",
        "status": "Accepted",
        "date": "2026-07-23",
        "binding": True,
        "gate": "queue-worker-gate",
        "documents_shipped": False,
        "verified_in": ["src/queue/worker.py:QueueWorker"],
        "supersedes": [],
        "superseded_by": None,
        "format": "madr",
    }
    path = adr_dir / "ADR-001-use-local-queue-worker.md"
    path.write_text(
        render_frontmatter(data)
        + """# ADR-001 Use Local Queue Worker

## Status

Accepted, 2026-07-23.

## Decision Outcome

Use a local queue worker for deterministic jobs.

## Enforcement

```json
{"forbid_pattern":[],"forbid_import":[],"require_pattern":[],"llm_judge":false}
```
""",
        encoding="utf-8",
    )
    before = path.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-migrate"),
            "--dry-run",
            "--suggest-retrieval",
            "--format",
            "json",
            str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    suggestion = payload["files"][0]
    assert payload["read_only"] is True
    assert payload["writes_automatically"] is False
    assert payload["requires_human_approval"] is True
    assert suggestion["suggested"]["components"] == ["src"]
    assert suggestion["suggested"]["symbols"] == ["QueueWorker"]
    assert suggestion["suggested"]["decision_contract"]["must"]
    assert suggestion["suggested"]["decision_contract"]["verification"]
    assert path.read_bytes() == before

    unsafe = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-migrate"),
            "--suggest-retrieval",
            str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert unsafe.returncode == 2
    assert "requires --dry-run" in unsafe.stderr
