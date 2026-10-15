# Independent audit — 2026-10-11/12

A full independent correctness and security audit of this fork, commissioned
2026-10-11. Audit only: no production file was changed, nothing was committed,
and nothing was sent upstream.

| File | What it holds |
|---|---|
| `REPORT.md` | The findings and the overall judgement. Start here. |
| `BASELINE.md` | Commits, host, toolchain, fixtures and standing caveats everything is relative to. |
| `ORCHESTRATOR-CHECKS.md` | Rechecks run by the coordinating session itself, on its own datasets, so the headline claims do not rest on one agent. |
| `COVERAGE.md` | What was examined per subsystem, by what method, and what was left unexamined or blocked. |
| `EXCLUSION-MAP.md` | Prior findings rechecked this round, with their current disposition. |
| `REGRESSION-LEDGER.md` | Per-commit verdicts on the fork's own changes against upstream. |
| `COMMANDS.md` | The commands behind the numbers, runnable as written. |
| `results.json` | Machine-readable findings. |
| `MANIFEST.sha256` | Checksums for everything in this directory. |
| `logs/`, `generators/`, `oracles/`, `reproducers/` | Raw output, dataset generators, independent reference implementations, minimal reproductions. |

## Method

Twelve auditors worked one subsystem each from a shared brief (source
inspection plus execution against four purpose-built worktrees: release
`master`, ASan+UBSan `master`, the unmerged repair branch, and upstream
`87c104d`). Each candidate finding then faced three independent adversarial
lenses — refutation from the specification and the source, independent
reproduction from scratch, and impact/prior-art assessment — before it was
allowed into the report. Findings that survived are labelled with the evidence
class and upstream relation defined in the brief; findings that did not are
recorded in `COVERAGE.md` rather than dropped.

The audit's first pass was interrupted by an infrastructure limit after eight of
twelve auditors had started work. Their partial evidence was recovered from disk
and the affected dimensions were re-run from where they had stopped;
`COVERAGE.md` records which dimensions were resumed and whether the resumption
reached the same depth as the dimensions that ran uninterrupted.
