#!/usr/bin/env python3
"""Ask an installed client which lifecycle events it actually emits.

Every hook defect this kit has shipped was the same shape: an event registered
in `hooks/manifest.json` that did not reach the code behind it. Certification
could not catch any of them, because it certified against
`tests/certification/simulated-pass.json` -- a fixture that says what we believe
rather than what a client does.

This probe runs the real binary and reads its own event stream. Claude Code
emits `hook_started` frames carrying `hook_event` when asked for
`--output-format=stream-json --include-hook-events`, so the answer comes from
the client rather than from us.

Three properties, each of which is the point rather than a detail:

* **It never fails the build.** A runner with no client, no credentials or no
  network records `not-run` and exits 0. A certification that fails when it
  cannot measure is a certification people learn to skip, and `not-run` is an
  honest evidence class -- the matrix already carries it for macOS and Linux.
* **It reports what it observed, not what it concluded.** An event that did not
  appear is `not-observed`, never `unsupported`. A prompt that uses no tools
  cannot produce `PreToolUse`, and reading that absence as a missing capability
  would put a false claim in the document this exists to make true.
* **It costs one model call.** Deliberately one short prompt: the probe is
  evidence gathering, and evidence that is expensive to collect is evidence
  nobody collects.
* **It closes the client's stdin.** The prompt arrives through `-p` and stdout
  is captured, so anything a client asked interactively would be invisible on
  this end and unanswerable from the console that started the probe. Closing
  stdin turns that into an immediate EOF instead of a wait no `timeout=` can
  end: on Windows a client installed through npm is a `.CMD` shim, and a
  timeout kills the shim while the grandchild holds the pipe open.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLIENT_BINARIES = {
    "claude-code-cli": "claude",
    "codex-cli": "codex",
    "github-copilot-cli": "copilot",
}

#: Only Claude Code documents a machine-readable hook-event stream today. The
#: other two are probed for presence and version, which is still more than a
#: fixture asserts, and their event coverage stays `not-run` until they offer
#: an equivalent. Claiming otherwise would be the failure this script exists to
#: stop, arriving from the other direction.
EVENT_STREAM_CLIENTS = {"claude-code-cli"}

PROBE_PROMPT = "Read probe.txt and reply with its contents. Nothing else."


def _binary(client: str) -> str | None:
    return shutil.which(CLIENT_BINARIES[client])


def _version(binary: str) -> str | None:
    try:
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True,
            stdin=subprocess.DEVNULL,
            encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else None


def _observe_events(binary: str, timeout: int) -> tuple[list[str], str | None]:
    """Run one prompt and collect the hook events the client reports.

    The workspace is a throwaway directory holding one file, so the prompt has
    something to read and the tool tier has a reason to fire. Nothing in the
    caller's repository is touched.
    """
    with tempfile.TemporaryDirectory(prefix="adr-kit-probe-") as workspace:
        root = Path(workspace)
        (root / "probe.txt").write_text("probe\n", encoding="utf-8")
        try:
            result = subprocess.run(
                [binary, "-p", PROBE_PROMPT,
                 "--output-format=stream-json", "--include-hook-events",
                 "--verbose", "--allowedTools", "Read"],
                cwd=root, capture_output=True, text=True,
                stdin=subprocess.DEVNULL,
                encoding="utf-8", errors="replace", timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [], f"the client did not answer within {timeout}s"
        except (OSError, subprocess.SubprocessError) as exc:
            return [], f"the client could not be run ({exc})"

    observed: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            frame = json.loads(line)
        except ValueError:
            continue
        event = frame.get("hook_event")
        if isinstance(event, str) and event:
            observed.add(event)
    if not observed:
        detail = (result.stderr or result.stdout).strip()[:200]
        return [], f"no hook events in the stream ({detail or 'empty output'})"
    return sorted(observed), None


def probe(client: str, timeout: int) -> dict:
    binary = _binary(client)
    if binary is None:
        return {
            "client": client,
            "evidence_mode": "not-run",
            "reason": f"{CLIENT_BINARIES[client]} is not on PATH",
        }
    record = {
        "client": client,
        "binary": binary,
        "version": _version(binary),
        "platform": sys.platform,
    }
    if client not in EVENT_STREAM_CLIENTS:
        record.update(
            evidence_mode="not-run",
            reason="this client exposes no machine-readable hook-event stream",
        )
        return record
    observed, failure = _observe_events(binary, timeout)
    if failure:
        record.update(evidence_mode="not-run", reason=failure)
        return record
    record.update(evidence_mode="native", observed_events=observed)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adr-kit:probe-client-events")
    parser.add_argument(
        "--clients", default=",".join(CLIENT_BINARIES),
        help="Comma-separated client ids to probe.",
    )
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write the evidence record here. Prints to stdout otherwise.",
    )
    args = parser.parse_args(argv)

    selected = [item.strip() for item in args.clients.split(",") if item.strip()]
    unknown = sorted(set(selected) - set(CLIENT_BINARIES))
    if unknown:
        print(f"unknown client(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    payload = {
        "schema_version": 1,
        "probe_id": "adr-kit-client-event-probe-v1",
        "records": [probe(client, args.timeout) for client in selected],
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    # Exit 0 whatever was found. Absence of a client is a normal outcome.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
