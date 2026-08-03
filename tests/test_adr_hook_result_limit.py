"""Five relevant ADRs at the start of work, and both hooks agreeing (spec R5).

Two defects the audit found: the limit was 3 where the spec asks for 5, and the
documented knob `context.default_limit` never reached the hook, so a user who
set 5 still got 3. A third one mattered more than either: the Python and Rust
hooks each carried their own constant, so what an agent was told depended on the
platform - and nobody could see it happen.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _core():
    sys.path.insert(0, str(REPO_ROOT / "bin"))
    name = "adr_hook_core_limit"
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "hooks" / "adr_hook_core.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


core = _core()


def test_the_default_is_five():
    assert core.DEFAULT_MAX_RESULTS == 5


def test_the_rust_hook_carries_the_same_default():
    """A platform-dependent difference in what an agent is told is invisible."""
    text = (REPO_ROOT / "hooks" / "native" / "adr-hook.rs").read_text(encoding="utf-8")
    match = re.search(r"const MAX_RESULTS: usize = (\d+);", text)

    assert match, "the Rust hook no longer declares MAX_RESULTS"
    assert int(match.group(1)) == core.DEFAULT_MAX_RESULTS


def test_the_configured_limit_reaches_the_hook(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"context": {"default_limit": 7}}), encoding="utf-8"
    )

    assert core._configured_limit(tmp_path) == 7


def test_an_absent_config_uses_the_default(tmp_path):
    assert core._configured_limit(tmp_path) == core.DEFAULT_MAX_RESULTS


def test_a_corrupt_config_uses_the_default(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text("{not json", encoding="utf-8")

    assert core._configured_limit(tmp_path) == core.DEFAULT_MAX_RESULTS


def test_an_absurd_limit_is_bounded_rather_than_obeyed(tmp_path):
    """A typo must not turn one prompt into a context flood."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"context": {"default_limit": 5000}}), encoding="utf-8"
    )

    assert core._configured_limit(tmp_path) == core.DEFAULT_MAX_RESULTS
