# Independent audit — 2026-10-09

This directory contains a read-only production-source audit of fork commit
`106d31c4b010d9cd4ae94c0db14d9dcf11aeb353`. Production source, historical
audit evidence, reference outputs, and the adjacent TruePad checkout are not
modified. Generated datasets and disposable builds live outside the repository.

The final deliverables are:

- `REPORT.md` — executive result, detailed findings, limitations, and TruePad readiness.
- `EXCLUSION-MAP.md` — every historical finding and its current disposition.
- `REGRESSION-LEDGER.md` — existing repairs and blockers rechecked under their existing IDs.
- `COVERAGE.md` — requirement/source/test/oracle coverage matrix.
- `results.json` — machine-readable results.
- `MANIFEST.sha256` — hashes of preserved audit artifacts.
- `rerun.sh` — minimal non-destructive rerun procedure.
- `COMMANDS.md` — executed-check ledger and corresponding logs.
- `logs/` — command output and exit-status evidence.

No real pad material, extractor seed, private capture, or other sensitive data
is included. All generated inputs are synthetic or existing public fixtures.
