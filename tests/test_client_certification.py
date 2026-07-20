"""Three-client release certification gate contracts."""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/client_certification.py"
BUILD = ROOT / "scripts/build-client-adapters.py"
sys.path.insert(0, str(ROOT / "scripts"))
import client_evidence as EVIDENCE  # noqa: E402

SPEC = importlib.util.spec_from_file_location("client_certification", SCRIPT)
assert SPEC and SPEC.loader
CERTIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CERTIFY
SPEC.loader.exec_module(CERTIFY)


def passing() -> dict:
    value = json.loads(
        (ROOT / "tests/certification/simulated-pass.json").read_text()
    )
    today = dt.date.today().isoformat()
    value["contract_date"] = today
    for record in value["records"]:
        record["contract_date"] = today
    return value


def errors(value: dict, release: bool = False) -> list[str]:
    return CERTIFY.validate(
        value,
        value["candidate_commit"],
        release,
        30,
    )


def test_simulated_bundle_passes_pr_gate_but_not_native_release_gate():
    value = passing()
    assert errors(value) == []
    release_errors = errors(value, release=True)
    assert len(release_errors) == 7
    assert any("real commit hash" in item for item in release_errors)
    assert sum("native release-candidate evidence missing" in item for item in release_errors) == 3
    assert sum("clean commit-bound artifact hash missing" in item for item in release_errors) == 3


def test_failing_fixture_and_missing_client_are_rejected():
    failed = json.loads(
        (ROOT / "tests/certification/simulated-fail.json").read_text()
    )
    assert CERTIFY.validate(failed, "simulated-fail", False, 36500)
    value = passing()
    value["records"].pop()
    assert "exactly the three clients" in "\n".join(errors(value))


def test_candidate_freshness_and_windows_identity_are_binding():
    value = passing()
    value["records"][0]["candidate_commit"] = "another"
    value["records"][1]["surface"] = "ide"
    value["contract_date"] = "2000-01-01"
    result = errors(value)
    assert any("candidate commit mismatch" in item for item in result)
    assert any("Windows CLI identity" in item for item in result)
    assert any("stale" in item for item in result)


def test_fixture_latency_archive_inventory_and_dependency_failures_block():
    value = passing()
    record = value["records"][0]
    record["fixtures"]["hook"] = False
    record["benchmarks"][1]["p95_ms"] = 501
    record["benchmarks"][1]["writes"] = 1
    record["release_policy"]["archive_allowlist_clean"] = False
    record["inventory"]["task_40_added"] = 5
    record["dependencies"]["runtime"] = ["coverage"]
    result = errors(value)
    for expected in (
        "fixtures",
        "latency budget",
        "rewrote output",
        "archive",
        "executable budget",
        "runtime dependency",
    ):
        assert expected in "\n".join(result)


def test_same_day_release_and_policy_reversal_require_explicit_evidence():
    value = passing()
    policy = value["records"][0]["release_policy"]
    policy["stable_releases_today"] = 1
    policy["default_or_hook_reversal"] = True
    result = errors(value)
    assert any("same-day stable release" in item for item in result)
    assert any("Proposed ADR" in item for item in result)


def test_schema_and_fixture_scope_exclude_future_clients():
    raw = (
        (ROOT / "schemas/client-certification.schema.json").read_text()
        + json.dumps(passing())
    ).lower()
    for future in ("opencode", "kilocode", "kimicode", "cursor", "gemini", "qwen"):
        assert future not in raw
    assert [item["client"] for item in passing()["records"]] == list(
        CERTIFY.CLIENTS
    )


def test_public_generator_entrypoint_validates_and_renders_support_matrix(tmp_path):
    fixture = ROOT / "tests/certification/simulated-pass.json"
    output = tmp_path / "support.md"
    command = [
        sys.executable,
        str(BUILD),
        "--certify",
        str(fixture),
        "--candidate-commit",
        "simulated-task40",
        "--support-output",
        str(output),
        "--format",
        "json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["passed"] is True
    text = output.read_text(encoding="utf-8")
    assert text.count("| CLI |") == 3
    assert "simulated only" in text
    assert subprocess.run([*command, "--check"]).returncode == 0


def test_failing_evidence_never_writes_support_claims(tmp_path):
    output = tmp_path / "support.md"
    result = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--certify",
            str(ROOT / "tests/certification/simulated-fail.json"),
            "--candidate-commit",
            "simulated-task40",
            "--support-output",
            str(output),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1
    assert not output.exists()


def _native_observations(tmp_path: Path, *, candidate: str) -> Path:
    evidence_root = tmp_path / "native"
    templates = {item["client"]: item for item in passing()["records"]}
    paths = {
        "claude-code-cli": "claude",
        "codex-cli": "codex",
        "github-copilot-cli": "copilot",
    }
    for client, directory in paths.items():
        source = ROOT / "tests" / "certification" / directory / "windows-native.json"
        observation = json.loads(source.read_text(encoding="utf-8"))
        template = templates[client]
        observation.update({
            "source_commit": candidate,
            "working_tree_clean": True,
            "release_eligible": True,
            "contract_date": dt.date.today().isoformat(),
            "certification": {
                key: copy.deepcopy(template[key])
                for key in (
                    "required_outcomes",
                    "fixtures",
                    "native_smoke",
                    "lifecycle_preservation",
                    "native_optimization",
                    "release_policy",
                )
            },
        })
        destination = evidence_root / directory / "windows-native.json"
        destination.parent.mkdir(parents=True)
        destination.write_text(json.dumps(observation), encoding="utf-8")
    return evidence_root


def test_native_observations_assemble_into_a_release_gate_bundle(tmp_path):
    candidate = "a" * 40
    evidence_root = _native_observations(tmp_path, candidate=candidate)
    bundle = EVIDENCE.assemble_native_bundle(evidence_root, ROOT, candidate)

    assert [record["client"] for record in bundle["records"]] == list(
        CERTIFY.CLIENTS
    )
    assert errors(bundle, release=True) == []
    assert {record["artifact_sha256"] for record in bundle["records"]} == {
        bundle["records"][0]["artifact_sha256"]
    }
    assert all(record["evidence_mode"] == "native" for record in bundle["records"])


def test_native_assembler_rejects_dirty_or_cross_commit_observations(tmp_path):
    candidate = "b" * 40
    evidence_root = _native_observations(tmp_path, candidate=candidate)
    claude = evidence_root / "claude/windows-native.json"
    observation = json.loads(claude.read_text(encoding="utf-8"))
    observation["working_tree_clean"] = False
    claude.write_text(json.dumps(observation), encoding="utf-8")

    try:
        EVIDENCE.assemble_native_bundle(evidence_root, ROOT, candidate)
    except EVIDENCE.CertificationError as exc:
        assert "not captured clean" in str(exc)
    else:
        raise AssertionError("dirty native evidence unexpectedly assembled")

    observation["working_tree_clean"] = True
    observation["source_commit"] = "c" * 40
    claude.write_text(json.dumps(observation), encoding="utf-8")
    try:
        EVIDENCE.assemble_native_bundle(evidence_root, ROOT, candidate)
    except EVIDENCE.CertificationError as exc:
        assert "commit mismatch" in str(exc)
    else:
        raise AssertionError("cross-commit native evidence unexpectedly assembled")


def test_native_assembler_rejects_mixed_payloads_and_release_policy(tmp_path):
    candidate = "e" * 40
    evidence_root = _native_observations(tmp_path, candidate=candidate)
    copilot = evidence_root / "copilot/windows-native.json"
    observation = json.loads(copilot.read_text(encoding="utf-8"))
    observation["prepared_payload_sha256"] = "f" * 64
    copilot.write_text(json.dumps(observation), encoding="utf-8")
    try:
        EVIDENCE.assemble_native_bundle(evidence_root, ROOT, candidate)
    except EVIDENCE.CertificationError as exc:
        assert "one prepared payload" in str(exc)
    else:
        raise AssertionError("mixed prepared payloads unexpectedly assembled")

    observation["prepared_payload_sha256"] = json.loads(
        (evidence_root / "claude/windows-native.json").read_text(encoding="utf-8")
    )["prepared_payload_sha256"]
    observation["certification"]["release_policy"]["stable_releases_today"] = 1
    copilot.write_text(json.dumps(observation), encoding="utf-8")
    try:
        EVIDENCE.assemble_native_bundle(evidence_root, ROOT, candidate)
    except EVIDENCE.CertificationError as exc:
        assert "one release policy" in str(exc)
    else:
        raise AssertionError("mixed release policy unexpectedly assembled")


def test_public_entrypoint_assembles_and_checks_external_native_bundle(tmp_path):
    candidate = "d" * 40
    evidence_root = _native_observations(tmp_path, candidate=candidate)
    output = tmp_path / "release-candidate.json"
    command = [
        sys.executable,
        str(BUILD),
        "--root",
        str(ROOT),
        "--assemble-native-evidence",
        str(evidence_root),
        "--candidate-commit",
        candidate,
        "--evidence-output",
        str(output),
        "--format",
        "json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["passed"] is True
    assert output.is_file()
    checked = subprocess.run(
        [*command, "--check"], capture_output=True, text=True, encoding="utf-8"
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    output.write_text("{}\n", encoding="utf-8")
    drift = subprocess.run(
        [*command, "--check"], capture_output=True, text=True, encoding="utf-8"
    )
    assert drift.returncode == 1
    assert json.loads(drift.stdout)["errors"] == ["assembled evidence bundle drift"]
    assert output.read_text(encoding="utf-8") == "{}\n"


def test_release_workflow_pins_evidence_separately_from_candidate():
    workflow = (ROOT / ".github/workflows/release-candidate.yml").read_text(
        encoding="utf-8"
    )
    assert "ADR_KIT_GATE_ID: three-client-release" in workflow
    assert "evidence_ref:" in workflow
    assert "Evidence ref must be an exact 40-character commit SHA" in workflow
    assert "path: .release-evidence" in workflow
    assert "git -C .release-evidence rev-parse HEAD" in workflow
    assert "${{ steps.evidence.outputs.bundle }}" in workflow
    assert '--certify "${{ inputs.evidence_bundle }}"' not in workflow
    assert "--support-output .release-output/client-support.md" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "include-hidden-files: true" in workflow
    assert "docs/client-support.md `" not in workflow
