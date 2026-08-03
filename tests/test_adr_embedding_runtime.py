"""Runtime detection at setup and upgrade (spec R16, TASK-87).

The probe is deliberately boring; the behaviour worth testing is what the report
*says* in each state, because a setup step acts on that and a user reads it. A
missing runtime must read as a normal outcome, and the GPU warning must present
itself as advice about speed rather than a capability gate.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS = REPO_ROOT / "bin" / "adr-settings"


def _load():
    name = "adr_embedding_runtime"
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "bin" / f"{name}.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


runtime = _load()


def _fake(monkeypatch, *, reachable: bool, models: list[str], gpu: bool) -> None:
    monkeypatch.setattr(
        runtime, "probe_ollama",
        lambda *a, **k: {
            "reachable": reachable,
            "models": models,
            "embedding_models": [m for m in models if runtime._looks_like_embedding_model(m)],
            "error": None if reachable else "connection refused",
        },
    )
    monkeypatch.setattr(
        runtime, "detect_gpu",
        lambda: {
            "likely_accelerated": gpu,
            "evidence": [{"probe": "test", "found": "test gpu"}] if gpu else [],
            "heuristic": True,
            "note": "heuristic",
        },
    )


def test_a_runtime_with_an_embedding_model_needs_no_question(monkeypatch):
    _fake(monkeypatch, reachable=True, models=["qwen3-embedding:8b", "gemma4:12b"], gpu=True)
    report = runtime.assess()

    assert report["state"] == "ready"
    assert report["routes"] == [], "nothing to ask when the answer is already yes"
    assert report["recommended_route"] is None


def test_a_runtime_without_an_embedding_model_offers_a_pull(monkeypatch):
    _fake(monkeypatch, reachable=True, models=["gemma4:12b"], gpu=True)
    report = runtime.assess()

    assert report["state"] == "runtime-without-model"
    assert [route["id"] for route in report["routes"]] == ["pull", "configure", "remote"]


def test_an_absent_runtime_reads_as_normal_not_as_failure(monkeypatch):
    _fake(monkeypatch, reachable=False, models=[], gpu=True)
    report = runtime.assess()

    assert report["state"] == "absent"
    assert "not an error" in report["headline"]
    assert "lexical ranking" in report["headline"], (
        "the report must say what still works, or a user reads it as breakage"
    )
    assert [route["id"] for route in report["routes"]] == ["install", "configure", "remote"]


def test_without_a_gpu_the_remote_route_is_recommended_and_the_warning_is_about_speed(monkeypatch):
    _fake(monkeypatch, reachable=False, models=[], gpu=False)
    report = runtime.assess()

    assert report["recommended_route"] == "remote"
    install = next(route for route in report["routes"] if route["id"] == "install")
    assert install["warning"], "installing without a GPU must warn first"
    assert "speed, not capability" in install["warning"]
    assert "2 s hook budget" in install["warning"]


def test_the_download_size_is_stated_before_the_pull(monkeypatch):
    _fake(monkeypatch, reachable=True, models=["gemma4:12b"], gpu=True)
    report = runtime.assess()
    pull = next(route for route in report["routes"] if route["id"] == "pull")

    assert any(runtime.RECOMMENDED_MODEL_SIZE in step for step in pull["steps"])
    assert any(runtime.SMALLER_ALTERNATIVE in step for step in pull["steps"]), (
        "a smaller variant must be offered next to the 4.7 GB one"
    )


def test_installing_third_party_software_requires_consent(monkeypatch):
    _fake(monkeypatch, reachable=False, models=[], gpu=True)
    report = runtime.assess()
    install = next(route for route in report["routes"] if route["id"] == "install")

    assert install["consent"] == "required"
    assert "without asking" in install["note"]
    assert "Declining leaves a working installation" in install["note"]


def test_the_gpu_check_declares_itself_a_heuristic():
    gpu = runtime.detect_gpu()

    assert gpu["heuristic"] is True
    assert "not a capability gate" in gpu["note"]


def test_the_probe_never_raises_on_an_unreachable_endpoint():
    result = runtime.probe_ollama("http://127.0.0.1:9/api/tags", timeout=0.2)

    assert result["reachable"] is False
    assert result["models"] == []
    assert result["error"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("qwen3-embedding:8b", True),
        ("nomic-embed-text", True),
        ("bge-m3:latest", True),
        ("gemma4:12b", False),
        ("qwen2.5:7b-instruct", False),
    ],
)
def test_embedding_models_are_told_apart_from_chat_models(name, expected):
    assert runtime._looks_like_embedding_model(name) is expected


def test_the_check_is_reachable_from_the_settings_cli(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, str(SETTINGS), "--adr-dir", str(adr_dir),
         "--check-embedding", "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["state"] in {"ready", "runtime-without-model", "absent"}
    assert payload["gpu"]["heuristic"] is True
