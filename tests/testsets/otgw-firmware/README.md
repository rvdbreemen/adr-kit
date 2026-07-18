# OTGW-firmware ADR compatibility corpus

This directory is a frozen real-world validation set copied from
[rvdbreemen/OTGW-firmware](https://github.com/rvdbreemen/OTGW-firmware).
It exists to exercise ADR Kit against a large, organically evolved decision
log without making tests depend on an adjacent checkout or network access.

## Contents and provenance

* `adrs/` contains only numbered `ADR-NNN-*.md` source records.
* `manifest.json` records the source repository and revisions, capture date,
  current migration baseline, byte sizes, and a SHA-256 digest for every ADR.
* `LICENSE` is the source repository's GNU General Public License v3.0.

The corpus files remain GPLv3-licensed test data. ADR Kit's own source remains
MIT-licensed. Do not copy corpus prose into ADR Kit templates, examples, or
runtime documentation.

At the 2026-07-18 snapshot the corpus contains 169 ADRs and 1,946,079 bytes.
The current planner baseline is:

| Classification | Count |
| --- | ---: |
| canonical | 85 |
| nygard | 11 |
| unknown | 73 |
| deterministic preview | 81 |
| guided migration | 88 |

The metadata-only dry run currently identifies 154 writable candidates and 15
records with actionable metadata failures. Those counts are a compatibility
snapshot, not a target. Parser or migration improvements may legitimately
change them, but the changed behavior must be reviewed and the manifest updated
intentionally.

## Refreshing

The refresh command reads `../OTGW-firmware` by default:

```bash
python scripts/refresh-otgw-corpus.py
```

Use an explicit checkout when needed:

```bash
python scripts/refresh-otgw-corpus.py --source /path/to/OTGW-firmware
```

The script refuses to snapshot modified or untracked numbered ADR files. It
copies only numbered ADR Markdown files plus the repository license, removes
stale numbered fixtures, reruns the planner and metadata dry run, and rewrites
the sorted manifest. It never changes the source checkout.

After refreshing:

1. Review the source revision and every file/hash change.
2. Review changes to format and action counts; do not accept a new baseline
   merely to silence a failing test.
3. Run `python -m pytest tests/test_otgw_corpus.py -q`.
4. Run the complete ADR Kit test suite before committing.

Tests operate exclusively on this frozen directory. Migration writes are
performed only on pytest temporary copies.
