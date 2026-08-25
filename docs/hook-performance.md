# ADR Kit hook latency method

The method is fixed by `tests/fixtures/hooks/reference-corpus.json`, whose
method ID is `adr-kit-hook-latency-v1`. **The budgets themselves live in
`hooks/manifest.json`, keyed by event id.**

That split matters. The corpus used to carry its own copy of the budgets keyed
by client-facing event name, and `plan-exit` and `pr-create` are both registered
as `pre-tool-use` with a matcher -- so keyed by name all three collapsed onto one
entry and two of the eight events were never measured at all, while the report
still read as a pass. One source now, keyed the way the manifest is (ADR-030).

The harness fixes:

- Windows as the required native certification machine class;
- macOS and Linux as best-effort evidence;
- one unmeasured warm-up launch, then 30 release-certification samples or 5
  bounded deep-doctor samples;
- cold-process, warm-filesystem, and warm-persistent-host cache labels;
- end-to-end subprocess startup inclusion;
- the reference payload for each lifecycle event, one per manifest event id;
- 20% CI-variance metadata, and the measured interpreter floor with the
  measurement that produced it.

An event that declares no budget now fails the harness rather than being
skipped, and the measured set is asserted to equal the declared set.

Python is the host on every platform, and the only one (ADR-029). It is still
fail-open; it is no longer a fallback, because there is nothing left to fall
back from.

**The budgets now describe the Python path, because that is what ships**
(ADR-030). They were calibrated for the native binary and were exactly right for
it -- measured on the same machine, PreToolUse costs 20.2 ms native against
273.6 ms in Python. ADR-029 retired that host, and the numbers were left
describing a path that no longer runs: seven of the eight events failed their own
budget, and `bin/adr-doctor` was permanently degraded as a result.

Three of them could not have been met by any amount of optimisation. `python -c
pass` measures 183 ms on the reference machine, so a 100 ms hard timeout expires
before the process reaches the first line of `adr-hook.py`. That floor is now a
named constant, `MEASURED_INTERPRETER_FLOOR_MS`, carrying its measurement.

**The native host is gone. Python answers on every platform (ADR-029).**
Latency was never the whole certification: the Rust host also owed protocol
parity with the Python core, and that half had never run. Measured on this
repository after a rebuild from current source, it returned one of four
governing ADRs before an edit, four of five at prompt time, and nothing at all
for `ExitPlanMode`. A hook that answers in 20 ms with a quarter of the governing
decisions is not faster than one that answers in 200 ms with all of them; it is
wrong sooner.

It was retired rather than repaired, because the alternative was a permanent
second implementation of the one component every other caller shares, bought
with latency rather than with capability. `SessionStart` costs 235 ms at the
median where the binary cost 21 ms, inside the 500 ms budget that event
declares. If a native path is ever restored, ADR-029 names the shape it must
take: port `bin/adr_query.py` rather than patch a second engine, and verify it
by running the artefact — the test that existed read `adr-hook.rs` for a
constant and therefore could not see a divergent build at all.

## Client runner timeout

`hooks/manifest.json` is the source of truth for client runner timeouts.
Events use a one-second runner timeout by default. `UserPromptSubmit` uses five
seconds so a cold Windows process launch, filesystem scan, or antivirus delay
does not terminate an otherwise healthy context lookup. This outer safety
margin does not relax the hook's 250 ms p95 target or 500 ms semantic hard
timeout: benchmark and doctor output must still surface slow retrieval.

Runner timeouts are bounded to integer values from 1 through 30 seconds. Hooks
remain local, deterministic, model-free, key-free, and fail-open.

Run the focused evidence:

```bash
python -m pytest tests/test_hook_protocol.py tests/test_hook_performance.py
python bin/adr-doctor --deep --check --format json
```

The doctor uses the same method ID and fixture and reports every event's
measurements without coercing missed targets into passes.

## Current Windows development evidence

The section this replaces described the native host as the performance story
and quoted a 25 ms p50 / 50 ms p95 / 100 ms hard edit-hook budget. Both are
gone: ADR-029 retired the binary, and ADR-030 recalibrated every budget to the
Python host that actually ships, because the interpreter floor alone exceeds
100 ms. `hooks/manifest.json` is the source of truth for the current numbers.

The `no_std` process-floor evidence is kept, because it is a property of
Windows rather than of any host: a 3,072-byte no-CRT executable measured over
300 launches at 13.171 ms minimum, 18.116 ms p50, 25.857 ms p95 and 144.603 ms
maximum before any JSON parsing, ADR lookup or output. It is preserved in
`tests/fixtures/hooks/windows-process-floor.json`, and it is what proved the
original 10/25/100 ms edit budget physically unattainable.

### Python-only measurement, 2026-08-24

Taken after the native host was removed (TASK-187), 30 samples per event,
`method_id` `adr-kit-hook-latency-v1`, process startup included. Every event
reports host `python`; there is no other host left to report.

**This is a developer machine measuring against the adr-kit repository
itself, not the declared certification runner against the fixture corpus.**
Certification owns the release-blocking judgement; these numbers are recorded
rather than coerced, exactly as the method requires.

| Event | p50 | p95 | maximum | timeouts | targets |
|---|---:|---:|---:|---:|:--|
| session-start | 280.1 ms | 345.1 ms | 398.4 ms | 0 | met |
| user-prompt-submit | 328.5 ms | 627.7 ms | 926.0 ms | 1 | p95, hard timeout missed |
| subagent-start | 278.0 ms | 401.3 ms | 601.7 ms | 0 | met |
| pre-tool-use | 303.4 ms | 362.6 ms | 391.3 ms | 0 | met |
| post-tool-use | 261.6 ms | 301.6 ms | 460.4 ms | 0 | met |
| plan-exit | 263.8 ms | 303.7 ms | 304.4 ms | 0 | met |
| pr-create | 4719.5 ms | 5097.8 ms | 5223.8 ms | 13 | p50, p95, hard timeout missed |
| pre-compact | 597.8 ms | 2117.2 ms | 2208.9 ms | 2 | p95, hard timeout missed |

The edit tier — `pre-tool-use`, `post-tool-use` and `plan-exit` — is the tier
ADR-029 named as the tight one, and it passes with room on every target.

The three misses are not caused by the retirement, and saying so is a
code-level fact rather than an inference: `hooks/adr-hook.py`,
`hooks/adr_hook_core.py` and `hooks/adapters/` are byte-unchanged by that work,
and `host_command` previously returned this same Python command whenever
`ADR_KIT_NATIVE_HOOK` was unset, which was its default. The measured path is
the path that already shipped. `pr-create` is the deliberately slower
user-initiated event of ADR-031, measured here against a 41-ADR repository with
a large working tree; `user-prompt-submit` and `pre-compact` miss p95 on a
loaded machine while their medians sit inside budget. Reproduce with:

```console
python -c "import sys; sys.path.insert(0,'.'); from hooks.hook_benchmark import measure; from pathlib import Path; print(measure(Path('.'), Path('.'), samples=30))"
```
