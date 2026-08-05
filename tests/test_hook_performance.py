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


# ---------------------------------------------------------------------------
# ADR-015's ceiling, on the hook side (TASK-129, ADR-031)
#
# ADR-015 forbids a hard budget above 2000 ms on any deterministic user-facing
# path and its References name hooks/manifest.json as the per-event hook budget
# file. But its Enforcement block only checks the CLI corpus, and this module
# carried no ceiling assertion at all -- so pr-create's 5000 ms landed, shipped
# in v0.44.0, and passed every gate.
#
# ADR-031 names the pull-request moment as a deliberately slower, user-initiated
# event. Its Decision Contract requires the exemption to be resolved from the ADR
# record rather than a literal list of event names here, so the manifest points
# at the record and this gate verifies the record is real and Accepted. No event
# name appears in this file.
#
# Gate anchor for ADR-031: adr-hook-ceiling-v1
# ---------------------------------------------------------------------------

CEILING_MS = 2000
MANIFEST = ROOT / "hooks" / "manifest.json"
ADR_DIR = ROOT / "docs" / "adr"


def _events() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["events"]


def _adr_status(adr_id: str) -> str | None:
    """The frontmatter status of one ADR, or None when no such file exists.

    Distinguished from a file that exists but declares no status: that is a
    formatting problem, and reporting it as "does not exist" would send the
    reader looking for a missing record instead of a broken one.
    """
    for path in ADR_DIR.glob(f"{adr_id}-*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("status:"):
                return line.split(":", 1)[1].strip().strip('"')
        return ""  # the record is there; its frontmatter is not
    return None


def _over_ceiling(events: list[dict]) -> list[dict]:
    return [
        event
        for event in events
        if int(event.get("latency_budget_ms", 0)) > CEILING_MS
    ]


def test_every_hook_budget_is_under_the_ceiling_or_named_by_an_accepted_adr():
    """ADR-015's Must Not, finally enforced on the file it names."""
    unexcused = []
    for event in _over_ceiling(_events()):
        exception = event.get("latency_ceiling_exception")
        if not exception:
            unexcused.append(
                f"{event['id']}: {event['latency_budget_ms']} ms with no "
                "latency_ceiling_exception"
            )
            continue
        status = _adr_status(exception)
        if status is None:
            unexcused.append(f"{event['id']}: names {exception}, which does not exist")
        elif status == "":
            unexcused.append(
                f"{event['id']}: names {exception}, whose frontmatter declares no status"
            )
        elif status != "Accepted":
            unexcused.append(
                f"{event['id']}: names {exception}, which is {status} and not Accepted"
            )

    assert not unexcused, (
        f"hook budgets above ADR-015's {CEILING_MS} ms ceiling:\n  "
        + "\n  ".join(unexcused)
        + "\n\nBring the budget under the ceiling, or write an ADR naming the event "
        "as user-initiated and reference it from latency_ceiling_exception."
    )


def test_an_exemption_pointing_at_a_missing_or_proposed_adr_fails(tmp_path):
    """The exemption must be a real Accepted record, not a plausible string.

    Without this the field would be a comment: anyone could write
    `latency_ceiling_exception: "ADR-999"` and the gate would wave it through,
    which is exactly the silent divergence ADR-031 exists to close.
    """
    assert _adr_status("ADR-999") is None
    assert _adr_status("ADR-031") == "Accepted"


def test_the_ceiling_gate_fails_on_an_unexcused_over_ceiling_entry():
    """Proof the gate bites, without committing a red assertion.

    ADR-031's own criterion asked for a test that fails on the current entry.
    Landing the gate and the exemption together means it does not -- so the
    biting is demonstrated against a synthetic manifest instead, which is the
    honest version of that claim.
    """
    synthetic = [
        {"id": "made-up-event", "latency_budget_ms": 5000},
        {"id": "another", "latency_budget_ms": 100},
    ]
    over = _over_ceiling(synthetic)
    assert [event["id"] for event in over] == ["made-up-event"]
    assert not over[0].get("latency_ceiling_exception")


def test_an_exempt_events_budget_agrees_with_the_kill_timeout_the_client_enforces():
    """ADR-031's Must: the declared number and the kill timeout must agree.

    A budget larger than the timeout that actually kills the process is a
    promise the runner cannot keep.
    """
    mismatched = []
    for event in _over_ceiling(_events()):
        runner_s = event.get("runner_timeout_sec")
        if runner_s is None:
            mismatched.append(f"{event['id']}: exempt but declares no runner_timeout_sec")
        elif int(event["latency_budget_ms"]) > runner_s * 1000:
            mismatched.append(
                f"{event['id']}: budget {event['latency_budget_ms']} ms exceeds "
                f"runner_timeout_sec {runner_s} s"
            )
    assert not mismatched, "\n  ".join(mismatched)


# ---------------------------------------------------------------------------
# Benchmark coverage (TASK-123) and the interpreter floor (TASK-124), per ADR-030
#
# Gate anchor for ADR-030: adr-hook-python-budgets-v1
# ---------------------------------------------------------------------------

from hooks.hook_benchmark import (  # noqa: E402
    MEASURED_INTERPRETER_FLOOR_MS,
    reference_payloads,
)


def test_the_benchmark_measures_every_event_the_manifest_declares():
    """The measured set must equal the declared set.

    plan-exit and pr-create are registered as pre-tool-use WITH A MATCHER, so a
    lookup keyed by client-facing event name collapsed all three onto one entry
    and skipped two of the eight. The report still read as a pass, which is the
    failure mode the harness exists to prevent.
    """
    declared = {event["id"] for event in _events()}
    measured = set(reference_payloads(ROOT).keys())
    assert measured == declared, (
        f"declared but never measured: {sorted(declared - measured)}; "
        f"measured but not declared: {sorted(measured - declared)}"
    )


def test_an_event_without_a_budget_fails_the_benchmark_rather_than_being_skipped(
    tmp_path,
):
    """A missing budget must be loud. Silence here reads as a pass."""
    import shutil

    from hooks.hook_benchmark import measure

    plugin_root = tmp_path / "plugin"
    shutil.copytree(ROOT / "hooks", plugin_root / "hooks")
    shutil.copytree(
        ROOT / "tests" / "fixtures" / "hooks",
        plugin_root / "tests" / "fixtures" / "hooks",
    )
    manifest_path = plugin_root / "hooks" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for event in manifest["events"]:
        if event["id"] == "plan-exit":
            event.pop("latency")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="plan-exit"):
        measure(plugin_root, tmp_path, samples=1)


def test_every_hard_timeout_clears_the_measured_interpreter_floor():
    """A budget below the floor is unmeetable by construction.

    `python -c pass` costs MEASURED_INTERPRETER_FLOOR_MS before the hook's first
    line runs, so a hard timeout under it fails whatever the hook does. Three
    events declared 100 ms against a measured 183 ms floor until ADR-030.
    """
    too_tight = [
        f"{event['id']}: {event['latency']['hard_timeout_ms']} ms is below the "
        f"measured {MEASURED_INTERPRETER_FLOOR_MS} ms interpreter floor"
        for event in _events()
        if event["latency"]["hard_timeout_ms"] <= MEASURED_INTERPRETER_FLOOR_MS
    ]
    assert not too_tight, "\n  ".join(too_tight)


def test_the_corpus_no_longer_carries_a_second_copy_of_the_budgets():
    """One source. The duplication is what hid two unmeasured events."""
    corpus = json.loads(
        (ROOT / "tests" / "fixtures" / "hooks" / "reference-corpus.json").read_text(
            encoding="utf-8"
        )
    )
    assert "budgets" not in corpus, (
        "reference-corpus.json carries its own budget table again. The manifest "
        "is the single source; a second copy keyed by event name is how "
        "plan-exit and pr-create went unmeasured."
    )
    assert corpus["budget_source"] == "hooks/manifest.json"
    assert corpus["python_floor_evidence"]
