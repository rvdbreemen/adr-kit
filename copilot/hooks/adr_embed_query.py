"""Embed one query for the hook path, or decline.

This module exists so that `hooks/adr_hook_core.py` does not have to. That file
must stay unable to reach a model or the network -- a test walks its imports and
fails if it can -- and that assertion is what stops someone putting embedding
*into* the retrieval core to make it simpler. ADR-020 permits embedding the
query in a hook; it does not permit the ranking core to acquire a socket.

So the capability lives here, beside the entrypoint, and arrives at the core as
a callable. The one place already allowed to reach out is `hooks/adr-hook.py`,
which spawns `adr-judge` for the pull-request guard.

Everything here declines rather than raises. A hook that cannot embed falls back
to lexical ranking and says so; a hook that raises produces silence, which is
the failure this whole path keeps rediscovering.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional

_BIN_DIR = Path(__file__).resolve().parents[1] / "bin"
STORE_NAME = ".adr-kit-vectors.json"

#: Well under the 500 ms budget of the events that may embed, so a slow backend
#: degrades to lexical rather than getting the whole hook killed by the client.
EMBED_TIMEOUT_S = 2


def _load_embed_module() -> Any:
    """Load `bin/adr-embed`, which owns backend resolution and has no suffix."""
    name = "adr_embed_for_hook"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    script = _BIN_DIR / "adr-embed"
    if not script.is_file():
        return None
    loader = importlib.machinery.SourceFileLoader(name, str(script))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def _store_model(adr_dir: Path) -> Optional[str]:
    """The model the corpus was embedded with.

    The query has to use the same one. Embedding it with a different model
    produces numbers that are the right shape and mean nothing -- similarities
    computed across two vector spaces -- and nothing downstream could tell.
    """
    try:
        payload = json.loads((adr_dir / STORE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    model = payload.get("model") if isinstance(payload, dict) else None
    return model if isinstance(model, str) and model.strip() else None


def embedder_for(adr_dir: Path) -> Optional[Callable[[str], Optional[List[float]]]]:
    """A callable that embeds one query, or None when this cannot work.

    None on any doubt: no store, no recorded model, no resolvable backend, an
    import that fails. The caller then takes the lexical route, which is what a
    user without a local runtime should get anyway.
    """
    if not (adr_dir / STORE_NAME).is_file():
        return None
    model = _store_model(adr_dir)
    if model is None:
        return None
    embed_module = _load_embed_module()
    if embed_module is None:
        return None

    def embed(query: str) -> Optional[List[float]]:
        try:
            backend = embed_module._resolve_embed_backend(adr_dir)
            if backend is None:
                return None
            vectors = backend.embed([query], model, EMBED_TIMEOUT_S)
        except BaseException:
            # Fail-soft is the contract: retrieval degrades, the hook does not.
            return None
        if not vectors:
            return None
        first = vectors[0]
        return list(first) if first else None

    return embed
