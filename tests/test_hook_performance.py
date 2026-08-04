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


def test_the_default_host_is_python_since_the_native_one_became_opt_in(monkeypatch):
    """v0.44.1 stopped preferring the native host, so the benchmark must too.

    Measured against the Python oracle it returned one of four governing ADRs
    before an edit, so `run-hook.cmd` now runs it only under
    `ADR_KIT_NATIVE_HOOK=1`. A benchmark that still picked it up whenever the
    file exists would publish latency for a path that no longer ships -- the
    most misleading number this file could produce.
    """
    monkeypatch.delenv("ADR_KIT_NATIVE_HOOK", raising=False)
    result = measure(ROOT, ROOT, samples=3)

    assert all(
        item["host"] == "python-fallback" for item in result["results"].values()
    ), result


def test_native_hook_host_meets_every_hard_timeout(monkeypatch):
    monkeypatch.setenv("ADR_KIT_NATIVE_HOOK", "1")
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


def test_windows_native_host_reports_p95_targets_without_masking(monkeypatch):
    # This test is about the native host, so it asks for it. Since v0.44.1 the
    # dispatcher does not, and the assertion below would otherwise pin
    # behaviour that was deliberately removed.
    monkeypatch.setenv("ADR_KIT_NATIVE_HOOK", "1")
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
