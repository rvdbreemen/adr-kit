"""`inject.enabled` and `watch.enabled` do what the schema says they do.

Both keys shipped in `schemas/adr-kit-config.schema.json` with descriptions that
promise a behaviour:

    inject.enabled  "When false, the PreToolUse injector never emits context and
                     the hook is a no-op for this project."
    watch.enabled   "When false, adr-watch never emits a nudge and the PostToolUse
                     hook is effectively a no-op for this project."

Neither was read by anything a hook reaches. `hooks/adr_hook_core.py` opened
`.adr-kit.json` exactly once, for `context.default_limit`. `inject.enabled` had
one reader -- `bin/adr-watch` -- which no client's generated `hooks.json`
invokes. A user who set either to false was told the hook was now a no-op, and
the injection kept firing.

`guardian.enabled` has worked since v0.18, so the pattern was the kit's own; only
these two tiers were unreachable from the settings surface.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "adr-hook.py"

ADR_BODY = textwrap.dedent(
    '''\
    ---
    id: "ADR-001"
    title: "Serve Both Protocol Eras"
    status: "Accepted"
    date: "2026-05-01"
    binding: true
    gate: null
    context_scope: "global"
    topics: ["retrieval", "protocol"]
    components: ["src"]
    documents_shipped: false
    verified_in: []
    supersedes: []
    superseded_by: null
    ---

    # ADR-001 Serve Both Protocol Eras

    ## Status

    Accepted, 2026-05-01.

    ## Context

    The retrieval layer in src/ has to answer both protocol eras.

    ## Decision

    Serve both protocol eras from one process, reading src/ only.

    ## Alternatives Considered

    - Two processes: rejected, because the era is a property of the frame.
    - Refuse the older era: rejected, because clients in the wild still speak it.

    ## Consequences

    **Positive:**
    - One process to reason about.

    **Negative:**
    - The dispatch has to stay a pure function of the frame.

    ## Related Decisions

    - None.

    ## References

    - src/retrieval.py
    '''
)

# Appended rather than embedded: the fenced block carries a regex whose
# backslashes do not survive being written inside a dedented triple-quoted
# literal without becoming unreadable. The `path_glob` is what makes this ADR
# govern `src/thing.py` -- without it the edit tier has nothing to inject, and
# the test would pass for the wrong reason by silencing an already-silent hook.
ADR_BODY += """
## Enforcement

```json
{
  "forbid_pattern": [
    {
      "pattern": "\\\\bpickle\\\\b",
      "path_glob": "src/**",
      "message": "The frame is parsed, never unpickled (ADR-001)."
    }
  ],
  "forbid_import": [],
  "require_pattern": [],
  "llm_judge": false
}
```
"""


@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    """A project with one governing ADR and its index generated."""
    root = tmp_path_factory.mktemp("edit-tier")
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-serve-both-protocol-eras.md").write_text(
        ADR_BODY, encoding="utf-8"
    )
    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("# governed\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-index"), str(adr_dir)],
        capture_output=True, check=True,
    )
    return root


def _fire(workspace: Path, event: str, config) -> bytes:
    path = workspace / "docs" / "adr" / ".adr-kit.json"
    if config is None:
        path.unlink(missing_ok=True)
    elif isinstance(config, str):
        path.write_text(config, encoding="utf-8")
    else:
        path.write_text(json.dumps(config), encoding="utf-8")
    payload = {
        "hook_event_name": "PreToolUse" if event == "pre-tool-use" else "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "src/thing.py"},
        "cwd": str(workspace),
    }
    result = subprocess.run(
        [sys.executable, str(HOOK), "--client", "claude-code-cli", "--event", event],
        input=json.dumps(payload).encode("utf-8"), capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout


@pytest.mark.parametrize("event", ["pre-tool-use", "post-tool-use"])
def test_the_edit_tier_injects_by_default(workspace, event):
    assert _fire(workspace, event, None), "the fixture must produce context to silence"


def test_inject_enabled_false_silences_the_pre_edit_tier(workspace):
    assert _fire(workspace, "pre-tool-use", {"inject": {"enabled": False}}) == b""


def test_watch_enabled_false_silences_the_post_edit_tier(workspace):
    assert _fire(workspace, "post-tool-use", {"watch": {"enabled": False}}) == b""


def test_the_two_switches_are_independent(workspace):
    """A team may want the pre-edit constraint without the post-edit backstop.

    One key silencing both would be a different feature from the one the schema
    documents, and the reverse pairing is a reasonable thing to want.
    """
    assert _fire(workspace, "pre-tool-use", {"watch": {"enabled": False}})
    assert _fire(workspace, "post-tool-use", {"inject": {"enabled": False}})


@pytest.mark.parametrize(
    "config",
    [
        pytest.param("{not json", id="malformed"),
        pytest.param({}, id="empty"),
        pytest.param({"inject": "yes"}, id="wrong-type"),
        pytest.param({"inject": {"enabled": "false"}}, id="string-not-boolean"),
        pytest.param({"inject": {}}, id="key-absent"),
    ],
)
def test_only_an_explicit_false_switches_a_tier_off(workspace, config):
    """A settings surface must not be able to silence governance by being broken.

    Every one of these is a config the hook cannot honestly read as "off": a
    typo, an empty document, a wrong type, the string "false", a missing key.
    Each has to keep injecting, because the failure mode of guessing wrong here
    is silent loss of the constraint the user thinks is in force.
    """
    assert _fire(workspace, "pre-tool-use", config)
