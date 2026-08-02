"""Any OpenAI-compatible endpoint, including LM Studio (spec R12, TASK-85).

The behaviour worth pinning is not the HTTP call - that is the same shape
OpenRouter already speaks - but the boundary around WHERE the endpoint may come
from. ADR-017 holds that repository-tracked configuration may select a backend
and never introduce one. A base URL read from the committed config would let a
cloned repository point the judge at a server it chose and receive the diff.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    name = "adr_llm"
    loader = importlib.machinery.SourceFileLoader(name, str(REPO_ROOT / "bin" / f"{name}.py"))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


llm = _load()


def test_the_backend_is_registered_and_selectable():
    assert llm.BACKEND_OPENAI_COMPATIBLE in llm.BACKENDS


def test_lm_studio_works_on_its_default_port():
    backend = llm.OpenAICompatibleBackend(llm.LM_STUDIO_BASE_URL, "qwen2.5-7b", None)

    assert backend.unavailable_reason() is None
    assert backend.endpoint == "http://127.0.0.1:1234/v1/chat/completions"


def test_a_missing_base_url_explains_where_it_belongs():
    reason = llm.OpenAICompatibleBackend(None, "model", None).unavailable_reason()

    assert "base URL" in reason
    assert llm.LOCAL_CONFIG_NAME in reason
    assert llm.OPENAI_BASE_URL_ENV in reason
    assert "1234" in reason, "LM Studio's default port is the useful hint here"


def test_a_missing_model_is_reported_separately():
    reason = llm.OpenAICompatibleBackend(llm.LM_STUDIO_BASE_URL, None, None).unavailable_reason()

    assert "openai_model" in reason


def test_the_endpoint_is_never_taken_from_committed_config(monkeypatch):
    """The security property: a repository may not name the endpoint."""
    monkeypatch.delenv(llm.OPENAI_BASE_URL_ENV, raising=False)
    warnings: list[str] = []
    backend = llm._openai_compatible_backend(
        {"openai_base_url": "http://evil.example/v1", "openai_model": "m"}, {}, warnings
    )

    assert backend.base_url == "", "a committed base URL must be ignored, not used"
    assert warnings, "and the user must be told it was ignored"
    assert "redirect the diff" in warnings[0]


def test_machine_local_config_supplies_the_endpoint(monkeypatch):
    monkeypatch.delenv(llm.OPENAI_BASE_URL_ENV, raising=False)
    backend = llm._openai_compatible_backend(
        {"openai_model": "local-model"},
        {"judge": {"openai_base_url": llm.LM_STUDIO_BASE_URL}},
        [],
    )

    assert backend.base_url == llm.LM_STUDIO_BASE_URL
    assert backend.model == "local-model"


def test_the_environment_outranks_the_local_file(monkeypatch):
    monkeypatch.setenv(llm.OPENAI_BASE_URL_ENV, "http://127.0.0.1:8000/v1")
    backend = llm._openai_compatible_backend(
        {"openai_model": "m"},
        {"judge": {"openai_base_url": llm.LM_STUDIO_BASE_URL}},
        [],
    )

    assert backend.base_url == "http://127.0.0.1:8000/v1"


def test_no_authorization_header_when_the_endpoint_needs_no_key(monkeypatch):
    """A local runtime usually has no key; an empty Bearer would be rejected."""
    captured: dict = {}

    def fake_post(self, payload, headers, timeout_s, adr_id):
        captured["headers"] = headers
        return {"choices": [{"message": {"content": '{"ADR-001": {"verdict": "OK"}}'}}]}

    monkeypatch.setattr(llm.OpenAICompatibleBackend, "_post", fake_post, raising=False)
    backend = llm.OpenAICompatibleBackend(llm.LM_STUDIO_BASE_URL, "m", None)
    backend.judge("prompt", 30, "ADR-001")

    assert "Authorization" not in captured["headers"]


def test_a_key_is_sent_when_one_is_configured(monkeypatch):
    captured: dict = {}

    def fake_post(self, payload, headers, timeout_s, adr_id):
        captured["headers"] = headers
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr(llm.OpenAICompatibleBackend, "_post", fake_post, raising=False)
    llm.OpenAICompatibleBackend(llm.LM_STUDIO_BASE_URL, "m", "secret").judge("p", 30, "ADR-001")

    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_a_malformed_response_degrades_rather_than_raises(monkeypatch):
    monkeypatch.setattr(
        llm.OpenAICompatibleBackend, "_post",
        lambda self, payload, headers, timeout_s, adr_id: {"choices": []},
        raising=False,
    )

    assert llm.OpenAICompatibleBackend(llm.LM_STUDIO_BASE_URL, "m", None).judge("p", 30, "A") is None


def test_the_schema_accepts_the_new_backend_and_model():
    schema = json.loads((REPO_ROOT / "schemas" / "adr-kit-config.schema.json").read_text(encoding="utf-8"))
    judge = schema["properties"]["judge"]["properties"]

    assert "openai-compatible" in judge["backend"]["enum"]
    assert "openai_model" in judge
    assert "openai_base_url" not in judge, (
        "the base URL must NOT be a committed setting; additionalProperties:false "
        "is what refuses it"
    )
