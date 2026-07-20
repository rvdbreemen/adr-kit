"""Latency methodology and hard-timeout certification for hook hosts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hooks.hook_benchmark import METHOD_ID, measure


def test_reference_method_fixes_machine_samples_states_and_budgets():
    reference = json.loads(
        (ROOT / "tests" / "fixtures" / "hooks" / "reference-corpus.json").read_text()
    )
    assert reference["method_id"] == METHOD_ID
    assert reference["machine_class"]["required"] == "Windows native certification runner"
    assert reference["sample_count"] == {"certification": 30, "deep_doctor": 5}
    assert reference["process_startup_included"] is True
    assert reference["cache_states"] == [
        "cold-process",
        "warm-filesystem",
        "warm-persistent-host",
    ]
    assert reference["ci_variance_percent"] == 20


def test_windows_process_floor_supports_revised_percentiles_without_hiding_outlier():
    evidence = json.loads(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "hooks"
            / "windows-process-floor.json"
        ).read_text()
    )
    assert evidence["samples"] == 300
    assert evidence["process_startup_included"] is True
    assert evidence["measurements_ms"]["p50"] <= evidence[
        "comparison_budget_ms"
    ]["p50"]
    assert evidence["measurements_ms"]["p95"] <= evidence[
        "comparison_budget_ms"
    ]["p95"]
    assert evidence["result"] == {
        "p50": True,
        "p95": True,
        "hard_timeout": False,
    }


def test_native_hook_host_meets_every_hard_timeout():
    result = measure(ROOT, ROOT, samples=5)
    assert result["method_id"] == METHOD_ID
    assert result["process_startup_included"]
    if any(
        item["host"] != "native" for item in result["results"].values()
    ):
        pytest.skip("native hook binary is unavailable on this runner")
    assert all(
        item["targets"]["hard_timeout"] for item in result["results"].values()
    ), result
    assert all(item["timeout_count"] == 0 for item in result["results"].values())


def test_windows_native_host_reports_p95_targets_without_masking():
    result = measure(ROOT, ROOT, samples=30)
    if os.name == "nt":
        assert all(
            item["host"] == "native" for item in result["results"].values()
        )
        assert all(
            isinstance(item["targets"]["p95"], bool)
            for item in result["results"].values()
        )
        # Certification, not this potentially loaded developer machine, owns
        # the release-blocking target assertion. Never coerce a miss to pass.
        assert result["all_targets_met"] == all(
            all(item["targets"].values())
            for item in result["results"].values()
        )
