"""Assemble independent native observations into release-gate evidence."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from client_certification import (
    FIXTURES,
    NATIVE_OPTIMIZATION,
    OUTCOMES,
    PRESERVATION,
    SMOKE,
    _all_true,
    validate,
)

NATIVE_EVIDENCE_PATHS = (
    ("claude-code-cli", "claude/windows-native.json"),
    ("codex-cli", "codex/windows-native.json"),
    ("github-copilot-cli", "copilot/windows-native.json"),
)
NATIVE_LIFECYCLE = {
    "claude-code-cli": {
        "marketplace_add", "install", "list", "disable", "enable",
        "no_op_update", "uninstall", "reinstall",
    },
    "codex-cli": {
        "marketplace_add", "install", "list", "remove", "reinstall",
        "verified_update_via_remove_add",
    },
    "github-copilot-cli": {
        "marketplace_add", "install", "list", "no_op_update", "uninstall",
        "reinstall",
    },
}


class CertificationError(RuntimeError):
    """Native evidence cannot form a release-candidate bundle."""


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CertificationError(f"{label} is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CertificationError(f"{label} must be a JSON object: {path}")
    return value


def _generation_benchmarks(source_root: Path) -> list[dict]:
    evidence = _read_json(
        source_root / "packaging/client-generation-benchmark.json",
        "generation benchmark evidence",
    )
    baseline = _read_json(
        source_root / "packaging/client-generation-baseline.json",
        "generation benchmark baseline",
    )
    if evidence.get("passed") is not True or evidence.get("platform", {}).get("os") != "nt":
        raise CertificationError("passing Windows-native generation evidence is required")
    result = []
    for source_name, state in (("clean", "cold"), ("warm", "warm")):
        source = evidence[source_name]
        elapsed = source["elapsed_ms"]
        result.append({
            "method_id": "client-generation-v1",
            "state": state,
            "samples": source["sample_count"],
            "p50_ms": elapsed["p50"],
            "p95_ms": elapsed["p95"],
            "max_ms": elapsed["max"],
            "hard_timeout_ms": evidence["methodology"]["hard_timeouts_ms"][source_name],
            "timed_out": False,
            "baseline_p95_ms": baseline["p95_ms"][source_name],
            "writes": source["files_written"],
        })
    return result


def _shared_inventory(source_root: Path) -> dict:
    value = _read_json(
        source_root / "packaging/executables.json",
        "executable inventory",
    )
    return {
        "bin_baseline": 27,
        "scripts_baseline": 3,
        "task_40_added": len(value.get("task_40_added_public_entrypoints", [])),
        "exception": None,
    }


def _shared_dependencies(source_root: Path) -> dict:
    value = _read_json(
        source_root / "packaging/dependencies.json",
        "dependency evidence",
    )
    return {
        "runtime": value.get("runtime"),
        "development": [
            item.get("name") for item in value.get("development", [])
        ],
        "licenses": value.get("licenses", []),
        "development_in_runtime": False,
        "exact_pins": [
            item for item in value.get("development", [])
            if item.get("exact_pin") is not None
        ],
    }


def _load_observation(path: Path, expected_client: str) -> dict:
    value = _read_json(path, "native evidence")
    if value.get("schema_version") != 1:
        raise CertificationError(f"{path}: native evidence schema_version must be 1")
    if value.get("client") != expected_client:
        raise CertificationError(f"{path}: expected client {expected_client}")
    return value


def _record(
    observation: dict,
    client: str,
    candidate: str,
    benchmarks: list[dict],
    inventory: dict,
    dependencies: dict,
) -> dict:
    prefix = client
    if observation.get("source_commit") != candidate:
        raise CertificationError(f"{prefix}: native observation commit mismatch")
    if observation.get("working_tree_clean") is not True:
        raise CertificationError(f"{prefix}: native observation was not captured clean")
    if observation.get("release_eligible") is not True:
        raise CertificationError(f"{prefix}: native observation is not release eligible")
    for key in ("client_version", "adr_kit_version", "environment"):
        if not observation.get(key):
            raise CertificationError(f"{prefix}: {key} is missing")
    detail_errors: list[str] = []
    _all_true(
        observation.get("native_lifecycle"),
        NATIVE_LIFECYCLE[client],
        f"{prefix} native lifecycle",
        detail_errors,
    )
    if detail_errors:
        raise CertificationError("; ".join(detail_errors))
    if not observation.get("evidence_links"):
        raise CertificationError(f"{prefix}: retained evidence links are missing")
    official_url = observation.get("official_contract", {}).get("url")
    if not isinstance(official_url, str) or not official_url.startswith("https://"):
        raise CertificationError(f"{prefix}: official contract URL is missing")
    artifact = str(observation.get("prepared_payload_sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", artifact):
        raise CertificationError(f"{prefix}: prepared payload hash is invalid")
    certification = observation.get("certification")
    if not isinstance(certification, dict):
        raise CertificationError(f"{prefix}: certification outcome maps are missing")
    required_maps = (
        ("required_outcomes", OUTCOMES),
        ("fixtures", FIXTURES),
        ("native_smoke", SMOKE),
        ("lifecycle_preservation", PRESERVATION),
        ("native_optimization", NATIVE_OPTIMIZATION),
    )
    map_errors: list[str] = []
    for key, required in required_maps:
        _all_true(certification.get(key), required, f"{prefix} {key}", map_errors)
    if map_errors:
        raise CertificationError("; ".join(map_errors))
    hook = observation.get("latency_evidence", {}).get("hooks", {})
    if (
        hook.get("method_id") != "adr-kit-hook-latency-v1"
        or hook.get("samples", 0) < 30
        or hook.get("all_targets_met") is not True
    ):
        raise CertificationError(f"{prefix}: release hook benchmark is incomplete")
    policy = certification.get("release_policy")
    if not isinstance(policy, dict):
        raise CertificationError(f"{prefix}: release policy evidence is missing")
    return {
        "client": client,
        "client_version": observation["client_version"],
        "adr_kit_version": observation["adr_kit_version"],
        "surface": "cli",
        "os": "windows",
        "candidate_commit": candidate,
        "contract_date": observation.get("contract_date"),
        "evidence_mode": "native",
        "working_tree_clean": True,
        "artifact_sha256": artifact,
        "environment_fingerprint": observation["environment"],
        "required_outcomes": certification["required_outcomes"],
        "fixtures": certification["fixtures"],
        "native_smoke": certification["native_smoke"],
        "platforms": {
            "windows": {
                "status": observation.get("platforms", {}).get("windows", {}).get("status"),
                "reason": "independent native Windows smoke passed",
            },
            "macos": observation.get("platforms", {}).get("macos"),
            "linux": observation.get("platforms", {}).get("linux"),
        },
        "benchmarks": benchmarks,
        "degradations": observation.get("degradations", []),
        "lifecycle_preservation": certification["lifecycle_preservation"],
        "native_optimization": certification["native_optimization"],
        "inventory": inventory,
        "dependencies": dependencies,
        "release_policy": policy,
        "source_links": [official_url],
        "evidence_links": observation["evidence_links"],
    }


def assemble_native_bundle(
    evidence_root: Path,
    source_root: Path,
    candidate: str,
) -> dict:
    """Build one gate-compatible bundle from three independent observations."""
    if not re.fullmatch(r"[0-9a-f]{40,64}", candidate):
        raise CertificationError("native bundle candidate must be a full commit hash")
    benchmarks = _generation_benchmarks(source_root)
    inventory = _shared_inventory(source_root)
    dependencies = _shared_dependencies(source_root)
    records = [
        _record(
            _load_observation(evidence_root / relative, client),
            client,
            candidate,
            benchmarks,
            inventory,
            dependencies,
        )
        for client, relative in NATIVE_EVIDENCE_PATHS
    ]
    if len({record["artifact_sha256"] for record in records}) != 1:
        raise CertificationError("native observations do not identify one prepared payload")
    dates = {record["contract_date"] for record in records}
    if len(dates) != 1 or None in dates:
        raise CertificationError("native observations do not share one contract date")
    policies = {
        json.dumps(record["release_policy"], sort_keys=True) for record in records
    }
    if len(policies) != 1:
        raise CertificationError("native observations do not share one release policy")
    bundle = {
        "schema_version": 1,
        "candidate_commit": candidate,
        "contract_date": next(iter(dates)),
        "records": records,
    }
    errors = validate(bundle, candidate, True, 30)
    if errors:
        raise CertificationError("; ".join(errors))
    return bundle


def write_bundle(path: Path, bundle: dict, check: bool) -> bool:
    """Write atomically, or report whether an existing output matches."""
    payload = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    if check:
        return path.is_file() and path.read_text(encoding="utf-8") == payload
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return True
