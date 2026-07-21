# ADR Grilling final certification

Certification date: 2026-07-21

## Release conclusion

TASK-45 delivers the complete ADR Grilling feature behind the existing
deterministic ADR lifecycle. The implementation is ready for review:

- deterministic readiness and implementation-link analysis remain read-only;
- the grill asks one decision-relevant question at a time;
- only explicit lifecycle commands can accept, reject, defer, or supersede;
- hooks and CI invoke no model and require no secret;
- an undocumented-decision signal remains advisory;
- only an explicit implementation link to a Proposed ADR can activate the
  deterministic merge gate;
- all 15 workflows generate reproducibly for Claude, Codex, and Copilot;
- the previous after-the-fact `auto` default migrates to `assist`, while an
  explicitly configured `auto` remains supported.

ADR-011 records these boundaries as an Accepted decision.

## End-to-end coverage

Automated scenarios cover:

1. creating an ADR from a new subject;
2. reconstructing an ADR from a pull request or diff;
3. reconstructing an ADR from a chat log or document;
4. resuming an interrupted grill;
5. accepting, rejecting, deferring, and superseding;
6. detecting a shipped implementation behind a Proposed ADR;
7. emitting advisory signals for possible undocumented decisions;
8. blocking only for a deterministic Proposed-ADR implementation link;
9. detached exact-SHA, shallow-clone, missing-ref, multi-link, and escaping
   behavior in the CI action;
10. guardian queue, hook, pre-commit, MCP, packaging, upgrade, and drift paths.

The fixtures under `tests/fixtures/grill/` keep these scenarios deterministic
and model-free.

## Executed validation

The release-required Windows baseline was executed on Windows 11
`10.0.26200`:

| Validation | Result |
|---|---|
| `python -m pytest -q` on CPython 3.12.9 | 821 passed, 6 skipped in 398.57 s |
| `uv run --python 3.10 --with pytest python -m pytest -q` | 820 passed, 6 skipped in 381.82 s |
| Python 3.10 final doctor-contract regression | 11 passed |
| Focused readiness and CI suite | 29 passed |
| Broad grilling integration slice | 285 passed |
| Packaging and client slice | 117 passed, 3 skipped |
| Final doctor, documentation, packaging, client, and CI slice | 52 passed |
| Generator and release checks after optimization | 14 passed |
| Markdown lint | 66 files, 0 issues |
| Strict ADR lint | 11 PASS, 0 advisory, 0 fail, 0 skipped |
| ADR index check | 11 ADRs; generated artifacts unchanged |
| ADR-011 related-link check | all links valid |
| ADR-011 readiness | Accepted; no findings |
| Client generation check | 0 changed, 0 written |
| `git diff --check` | passed |

The skipped tests are existing environment-dependent cases; neither full run
reported a failure.

The final deep doctor reported zero required failures, zero ADR findings,
healthy generated adapters, and a healthy live five-tool MCP handshake. Its
overall state was `degraded` only for optional or machine-local conditions:
ambiguous local-model discovery, missing generated project guidance, Claude
plugin trust pending, and five-sample Windows hook timing variance. The
authoritative 30-sample hook benchmark passed under the documented variance
method.

The repository CI matrix now runs the complete suite, not a reduced smoke
slice, for Python 3.10 and 3.12 on Windows, Linux, and macOS. Windows is ADR
Kit's required native certification platform; Linux and macOS remain
best-effort platform evidence under ADR-010. Those remote jobs require a pushed
commit or pull request and were therefore not represented as locally executed
results in this working-tree certification.

## Performance certification

Both benchmark commands used 30 samples and fail non-zero on a breached budget:

```powershell
python scripts/benchmark-adr-grilling.py --samples 30
python scripts/benchmark-client-generation.py --samples 30
```

Key results:

| Path | p95 | Maximum | Result |
|---|---:|---:|---|
| Readiness core, 50 ADRs | 66.246 ms | 71.654 ms | PASS |
| Linkage, 500 paths / 50 ADRs | 150.444 ms | 160.457 ms | PASS |
| All-Proposed CLI | 314.849 ms | 357.927 ms | PASS |
| Persistent MCP | 336.830 ms | 358.672 ms | PASS |
| PR readiness action | 1,150.890 ms | 1,619.274 ms | PASS |
| Clean three-client generation | 896.896 ms | 925.082 ms | PASS |
| Warm unchanged generation | 128.694 ms | 141.799 ms | PASS |
| Index-only pre-commit signal | 616.388 ms | 721.188 ms | PASS |

Warm generation performed zero reads and zero writes. Clean generation was
10.31 percent faster and warm generation 14.20 percent faster than their
approved p95 references. Every measured pre-existing path remained below the
20 percent regression ceiling, and every new absolute budget passed. Full raw
figures and the measurement method are in
[the benchmark report](06-benchmark-report.md).

## Packaging and deterministic behavior

- `packaging/public-artifacts.json` includes the action, readiness engines,
  schema, grill workflow, templates, and feature documentation.
- `packaging/executables.json` includes the new executable entry points.
- the installer expects five MCP tools and retains its line-budget contract;
- generated Claude, Codex, and Copilot payloads are byte-stable on a warm run;
- Windows native hook binaries were rebuilt and their outcome contracts
  refreshed;
- upgrade and drift checks preserve local changes and detect stale generated
  artifacts;
- path, ref, Markdown, command, and output escaping have explicit regression
  coverage.

## Human lifecycle gate

Passing readiness is not acceptance. A Proposed ADR is complete only when the
engineer or architect has resolved its open questions and explicitly chooses
an outcome. `adr accept` remains the sole acceptance transition and reruns the
authoritative verification gates. The guardian queue keeps unfinished
Proposed ADRs visible without silently changing their state.
