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

The native host is the certified Windows path for *latency*. Python is a
fail-open portable fallback.

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

**As of v0.44.1 the native host is opt-in and Python answers by default.**
Latency was never the whole certification: `hooks/native/README.md` also asks
for protocol parity with the Python core, and that half had never run. Measured
on this repository after a rebuild from current source, the native host returned
one of four governing ADRs before an edit, four of five at prompt time, and
nothing at all for `ExitPlanMode`. A hook that answers in 20 ms with a quarter
of the governing decisions is not faster than one that answers in 200 ms with
all of them; it is wrong sooner.

Set `ADR_KIT_NATIVE_HOOK=1` to use it. Restoring the default preference is gated
on an artefact-level parity test — one that runs the binary rather than reading
its source, since the test that existed read `adr-hook.rs` and therefore could
not see a divergent build at all. TASK-104 carries that work and the alternative
of retiring the binary.

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

The native host reduced the Python end-to-end SessionStart path from roughly
200 ms to roughly 20–35 ms on the development machine. SessionStart, prompt,
subagent, compact, stop, and hard-timeout budgets pass consistently.

Windows process creation proved that the original 10/25/100 ms edit-hook
budget was physically unattainable on the certification machine. The approved
Windows PreToolUse/PostToolUse budget is therefore 25 ms p50, 50 ms p95, and
a strictly enforced 100 ms hard timeout. Full pre/post-edit automation remains
enabled.

A 3,072-byte `no_std`, no-CRT executable measured over 300 launches at
13.171 ms minimum, 18.116 ms p50, 25.857 ms p95, and 144.603 ms maximum before
JSON parsing, ADR lookup, or output. The evidence is preserved in
`tests/fixtures/hooks/windows-process-floor.json`.

This is retained as an explicit certification finding, not hidden by
excluding startup or relabeling the result. The semantic benchmark enforces
the 100 ms timeout on every measured launch and reports every timeout, rather
than treating a later successful sample as representative.

The first 30-sample warm-filesystem certification after the policy decision
passed every event and every hard timeout. The edit-hook results were:

| Event | p50 | p95 | maximum | timeouts |
|---|---:|---:|---:|---:|
| PreToolUse | 22.358 ms | 28.275 ms | 30.260 ms | 0 |
| PostToolUse | 22.932 ms | 28.080 ms | 29.787 ms | 0 |
