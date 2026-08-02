"""Detect a local embedding runtime, and say what to do when there is none.

spec.md R16. Setup and upgrade must find out whether a local runtime is
available and act on the answer, rather than leaving a user to discover the gap
when retrieval silently falls back to lexical ranking.

Three properties this module keeps, each because the alternative misleads:

**Detection is stdlib, local and fail-soft.** It reaches one loopback address
with a one-second budget and treats every failure as "absent", never as an
error. A setup step that dies because a daemon is not running is worse than one
that says so and offers a route.

**A missing runtime is a normal outcome, not a fault.** The kit works without
embeddings; retrieval degrades to lexical ranking, which is what it has always
done. The report says that plainly instead of implying breakage.

**The GPU check presents itself as a heuristic**, because that is what it is.
`nvidia-smi`, an Apple Silicon machine identifier and a Windows video-controller
query each answer part of the question and none is authoritative. Ollama runs on
CPU; the warning is about speed, not capability. It matters because an embedding
model on CPU cannot meet the 2 s hook budget of ADR-015, which turns a feature
into a regression nobody sees.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import urllib.error
import urllib.request
from typing import Dict, List, Optional

OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
PROBE_TIMEOUT_S = 1.0

# Model names that identify an embedding model rather than a chat model. Ollama
# does not label them, so the name is the only signal available without pulling
# a manifest per model.
EMBEDDING_MARKERS = ("embed", "embedding", "bge", "gte", "e5-", "minilm")

# The model the install route offers. Size is stated before any download starts:
# 4.7 GB is a decision, not a detail, and a user on a metered link deserves to
# make it knowingly.
RECOMMENDED_MODEL = "qwen3-embedding:8b"
RECOMMENDED_MODEL_SIZE = "about 4.7 GB"
SMALLER_ALTERNATIVE = "nomic-embed-text"
SMALLER_ALTERNATIVE_SIZE = "about 275 MB, English-only"


def _looks_like_embedding_model(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in EMBEDDING_MARKERS)


def probe_ollama(url: str = OLLAMA_TAGS_URL, timeout: float = PROBE_TIMEOUT_S) -> Dict:
    """Ask the local daemon what it has. Never raises."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, ValueError, urllib.error.URLError) as exc:
        return {"reachable": False, "models": [], "embedding_models": [], "error": str(exc)}
    raw = payload.get("models", []) if isinstance(payload, dict) else []
    names = sorted(
        {
            item["name"]
            for item in raw
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
    )
    return {
        "reachable": True,
        "models": names,
        "embedding_models": [name for name in names if _looks_like_embedding_model(name)],
        "error": None,
    }


def detect_gpu() -> Dict:
    """Heuristic, and labelled as one. Never raises, never blocks."""
    system = platform.system()
    checks: List[Dict] = []

    def _run(argv: List[str]) -> Optional[str]:
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=5, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout if result.returncode == 0 else None

    nvidia = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if nvidia and nvidia.strip():
        checks.append({"probe": "nvidia-smi", "found": nvidia.strip().splitlines()[0]})

    if system == "Darwin" and platform.machine() in {"arm64", "aarch64"}:
        checks.append({"probe": "apple-silicon", "found": platform.machine()})

    if system == "Windows" and not checks:
        out = _run([
            "powershell", "-NoProfile", "-Command",
            "(Get-CimInstance Win32_VideoController).Name",
        ])
        if out:
            names = [line.strip() for line in out.splitlines() if line.strip()]
            discrete = [n for n in names if re.search(r"nvidia|radeon|arc", n, re.I)]
            if discrete:
                checks.append({"probe": "win32_videocontroller", "found": discrete[0]})

    return {
        "likely_accelerated": bool(checks),
        "evidence": checks,
        "heuristic": True,
        "note": (
            "This is a heuristic, not a capability gate. Ollama runs on CPU; without "
            "acceleration an embedding model is slow enough that the 2 s hook budget "
            "(ADR-015) is unreachable, which is a speed problem, not a broken feature."
        ),
    }


def assess(url: str = OLLAMA_TAGS_URL) -> Dict:
    """One report a setup or upgrade step can act on without further probing."""
    runtime = probe_ollama(url)
    gpu = detect_gpu()

    if runtime["reachable"] and runtime["embedding_models"]:
        state = "ready"
        headline = (
            f"Local embedding runtime found with "
            f"{len(runtime['embedding_models'])} embedding model(s): "
            f"{', '.join(runtime['embedding_models'])}."
        )
        routes: List[Dict] = []
    elif runtime["reachable"]:
        state = "runtime-without-model"
        headline = (
            "Ollama is running but carries no embedding model. Retrieval keeps "
            "working on lexical ranking until one is pulled."
        )
        routes = [_pull_route(gpu), _configure_route(), _remote_route(gpu)]
    else:
        state = "absent"
        headline = (
            "No local embedding runtime is reachable at 127.0.0.1:11434. "
            "This is not an error: retrieval works on lexical ranking without it."
        )
        routes = [_install_route(gpu), _configure_route(), _remote_route(gpu)]

    return {
        "state": state,
        "headline": headline,
        "runtime": runtime,
        "gpu": gpu,
        "routes": routes,
        "recommended_route": _recommend(state, gpu),
    }


def _install_route(gpu: Dict) -> Dict:
    return {
        "id": "install",
        "title": "Install Ollama and pull an embedding model",
        "consent": "required",
        "warning": None if gpu["likely_accelerated"] else _cpu_warning(),
        "steps": [
            "Install Ollama for this platform: https://ollama.com/download",
            f"Pull the model: ollama pull {RECOMMENDED_MODEL}  ({RECOMMENDED_MODEL_SIZE})",
            f"Or a smaller one: ollama pull {SMALLER_ALTERNATIVE}  ({SMALLER_ALTERNATIVE_SIZE})",
            "Then re-run this check.",
        ],
        "note": (
            "adr-kit does not install this for you without asking, and never with "
            "silent elevation. Declining leaves a working installation."
        ),
    }


def _pull_route(gpu: Dict) -> Dict:
    return {
        "id": "pull",
        "title": "Pull an embedding model into the runtime you already have",
        "consent": "required",
        "warning": None if gpu["likely_accelerated"] else _cpu_warning(),
        "steps": [
            f"ollama pull {RECOMMENDED_MODEL}   ({RECOMMENDED_MODEL_SIZE})",
            f"ollama pull {SMALLER_ALTERNATIVE}   ({SMALLER_ALTERNATIVE_SIZE})",
        ],
        "note": "The size is stated first because a download is a decision.",
    }


def _configure_route() -> Dict:
    return {
        "id": "configure",
        "title": "Point at a runtime you already run elsewhere",
        "consent": "none",
        "warning": None,
        "steps": [
            "LM Studio, a remote Ollama, or any OpenAI-compatible endpoint.",
            "python bin/adr-settings --set judge.backend=openai-compatible",
            "python bin/adr-settings --set judge.openai_base_url=http://127.0.0.1:1234/v1   (LM Studio's default; machine-local)",
            "python bin/adr-settings --set judge.openai_model=<model the endpoint serves>",
        ],
        "note": "Nothing is installed; an existing runtime is reused.",
    }


def _remote_route(gpu: Dict) -> Dict:
    return {
        "id": "remote",
        "title": "Use a remote API endpoint",
        "consent": "none",
        "warning": None,
        "steps": [
            "python bin/adr-settings --set judge.backend=openrouter",
            "export OPENROUTER_API_KEY=...   (read from the environment only, never from the repository)",
        ],
        "note": (
            "Recommended when this machine has no GPU: the work leaves the machine, "
            "which is a privacy trade the user makes knowingly."
            if not gpu["likely_accelerated"]
            else "Useful when the local machine should stay free for other work."
        ),
    }


def _cpu_warning() -> str:
    return (
        "No GPU detected (heuristic). An embedding model on CPU is slow enough that "
        "the 2 s hook budget becomes unreachable, so the remote route is the better "
        "trade here. Ollama will still run - this is about speed, not capability."
    )


def _recommend(state: str, gpu: Dict) -> Optional[str]:
    if state == "ready":
        return None
    return "install" if gpu["likely_accelerated"] else "remote"


def render(report: Dict) -> List[str]:
    lines = [report["headline"], ""]
    runtime = report["runtime"]
    if runtime["reachable"]:
        lines.append(f"  models present: {', '.join(runtime['models']) or 'none'}")
    else:
        lines.append(f"  probe: not reachable ({runtime['error']})")
    gpu = report["gpu"]
    verdict = "likely" if gpu["likely_accelerated"] else "not detected"
    lines.append(f"  gpu: {verdict} (heuristic)")
    for check in gpu["evidence"]:
        lines.append(f"    via {check['probe']}: {check['found']}")
    if not report["routes"]:
        return lines
    lines.extend(["", "Routes:"])
    for route in report["routes"]:
        marker = " (recommended)" if route["id"] == report["recommended_route"] else ""
        lines.append(f"  [{route['id']}] {route['title']}{marker}")
        if route["warning"]:
            lines.append(f"      ! {route['warning']}")
        for step in route["steps"]:
            lines.append(f"      - {step}")
        lines.append(f"      {route['note']}")
    return lines
