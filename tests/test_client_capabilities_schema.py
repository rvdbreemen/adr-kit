import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "client-capabilities.schema.json"
CLIENT_IDS = {
    "claude-code-cli",
    "codex-cli",
    "github-copilot-cli",
}
OUTCOMES = {
    "workflow-discovery",
    "task-context",
    "edit-governance",
    "mcp",
    "pre-commit",
    "lifecycle",
    "doctor",
}


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_is_versioned_and_rejects_unknown_top_level_fields():
    schema = _schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "$schema",
        "schema_version",
        "program_scope",
        "ownership",
        "settings",
        "clients",
        "certification",
    }


def test_schema_permits_exactly_the_three_task_40_clients():
    schema = _schema()
    clients = schema["properties"]["clients"]
    client_ids = set(schema["$defs"]["client"]["properties"]["id"]["enum"])

    assert clients["minItems"] == clients["maxItems"] == 3
    assert client_ids == CLIENT_IDS
    assert set(
        schema["properties"]["program_scope"]["properties"][
            "first_class_clients"
        ]["const"]
    ) == CLIENT_IDS
    contains_ids = {
        rule["contains"]["properties"]["id"]["const"]
        for rule in clients["allOf"]
    }
    assert contains_ids == CLIENT_IDS


def test_client_contract_requires_scope_outcomes_events_and_lifecycle_probes():
    schema = _schema()
    client = schema["$defs"]["client"]
    required = set(client["required"])

    assert {
        "id",
        "surface",
        "platforms",
        "required_outcomes",
        "event_mappings",
        "degradations",
        "probes",
        "settings_keys",
        "certification_ref",
    } <= required
    assert set(schema["$defs"]["outcome"]["enum"]) == OUTCOMES
    assert set(schema["$defs"]["probes"]["required"]) == {
        "detect",
        "install",
        "update",
        "rollback",
        "disable",
        "remove",
        "doctor",
    }


def test_platform_and_release_contract_is_windows_first():
    schema = _schema()
    platforms = schema["$defs"]["platformScope"]["properties"]
    certification = schema["properties"]["certification"]["properties"]

    assert platforms["windows"]["const"] == "release-required"
    assert platforms["macos"]["const"] == "best-effort"
    assert platforms["linux"]["const"] == "best-effort"
    assert certification["windows_native_required"]["const"] is True
    assert certification["all_clients_block_release"]["const"] is True
    assert certification["best_effort_platforms"]["const"] == [
        "macos",
        "linux",
    ]


def test_schema_records_artifact_and_settings_ownership_without_future_clients():
    schema = _schema()
    raw = SCHEMA_PATH.read_text(encoding="utf-8").lower()

    assert set(schema["properties"]["ownership"]["required"]) == {
        "canonical",
        "generated",
        "hand_authored_validated",
    }
    assert schema["properties"]["settings"]["properties"]["precedence"][
        "const"
    ] == ["project", "global", "detected-default"]
    for deferred_client in (
        "opencode",
        "kilo",
        "kimi",
        "cursor",
        "gemini",
        "qwen",
    ):
        assert deferred_client not in raw
