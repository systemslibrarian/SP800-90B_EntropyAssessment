# Audit directory guide

## Purpose

This directory preserves independent audit work against [`usnistgov/SP800-90B_EntropyAssessment`](https://github.com/usnistgov/SP800-90B_EntropyAssessment), NIST's SP 800-90B entropy assessment tool. All work here dates from **2026-09-30** and audits upstream `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`. AI-assisted analysis was used; confirmed findings were reproduced on clean builds.

Nothing here is an official NIST conclusion. The reports are historical records: they must not be rewritten. New evidence or status belongs in new files, or in the tracker.

- Tracked files under `audits/`: **584**, including this README.
- Tracked subdirectories: **118**.
- Documents are described individually below. Evidence files are described per directory here and per file in the two `MANIFEST.md` files (original path, SHA-256, finding supported).

## Historical audit reports

### `audits/2026-09-30/AUDIT.md`
- **Session and date:** first-wave adversarial audit of `ea_non_iid` (14 automated attackers), 2026-09-30, at fork commit `f06166f`. Every file on the `ea_non_iid` include path is byte-identical to upstream `87c104d`.
- **Findings:** F01–F30, with the round-2 verification status recorded in each row.
- **Upstream (as recorded in the file):** F01→#253 (PR #256), F02→#254, F03+F05→#255, F04→#258, F15→#261, F16→#257 (PR #268), F18→#259, F19→#260, F17→closed #214/#163/#52.
- **Provenance:** moved unchanged (a 100% rename) from the repository root file `AUDIT-2026-09-30.md` during the 2026-09-30 cleanup.
- **Status:** historical. Leave it byte-for-byte unchanged.

### `audits/2026-09-30/novel-findings/REPORT.md`
- **Session and date:** whole-codebase novel-findings audit (parallel session, seven auditors plus a coordinator), 2026-09-30.
- **Provenance:** byte-identical copy of `audits/2026-09-30-novel-findings-audit.md` from fork commit `0e685f6`. That original path exists only on fork branch `audits/2026-09-30-novel-findings`.
- **Baseline:** upstream `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`.
- **Findings:** N-01…N-11, R-1…R-3; prior local rows F09 (verified, TOO LOW), F10 (mechanism only) and F14 (mechanism, needs > 25.8 Gbit).
- **Upstream:**
  - N-02 was filed afterwards as **#271**.
  - R-1, R-2 and R-3 are residuals of closed **#246**, **#178** and **#183**.
  - The report maps rediscoveries to #253, #254, #255, #257, #259, #260, #261, #263, #264, #153, #195, #251, #252 and others.
- **Status:** historical. Leave it byte-for-byte unchanged.

### `audits/2026-09-30/phase2-focused/REPORT.md`
- **Session and date:** phase-2 focused audit (second session), 2026-09-30. Baseline upstream `87c104d`, built with g++ 13.3.0 on Linux x86_64.
- **Provenance:** added to fork `master` in commit `3087ff4` as `audits/2026-09-30-phase2-focused-audit.md`. That byte-identical duplicate was removed in the cleanup; this file is the single canonical copy.
- **Findings:**
  - NOVEL-01: selftest does not compare the final figures, and its exit status reflects only the last file.
  - NOVEL-02: ea_iid JSON placeholder values.
  - NOVEL-03: ea_restart -i JSON row/column permutation blocks untagged.
  - Rediscoveries mapped to N-01, N-03…N-08, R-1…R-3 and to existing upstream items.
- **Upstream:** NOVEL-01 was filed afterwards as **#272**; the report predates the filing and says "not filed". NOVEL-02 and NOVEL-03 are not filed.
- **Status:** historical. Leave it byte-for-byte unchanged.

## Supporting documents

| Path | Kind | Contents |
|---|---|---|
| `2026-09-30/README.md` | index | Scope, baseline, filed vs audit-only, layout changes, reproduction steps, and what was deliberately not committed |
| `2026-09-30/FINDINGS-TRACKER.md` | tracker | One table per series: F01–F30, N-01–N-11, R-1–R-3, NOVEL-01–NOVEL-03. Columns: category, direction, repro/regression status, upstream issue/PR, status read from GitHub on 2026-09-30, fork fix branch, evidence path |
| `2026-09-30/novel-findings/MANIFEST.md` | manifest | Every file of the novel-findings tree (original path, bytes, SHA-256, finding supported, description), plus the provenance table for the removed upstream duplicates |
| `2026-09-30/phase2-focused/MANIFEST.md` | manifest | The same for the phase-2 tree, plus regeneration commands and the original SHA-256 of every regenerable dataset |
| `2026-09-30/novel-findings/BRIEF.md` | historical brief | The shared instructions given to the seven parallel auditors: scope, hard rules, known-issue dedup set, report format. It contains absolute `/tmp` paths of the original workspace |
| `2026-09-30/novel-findings/agent-reports/*.md` | auditor reports | conditioning (`ea_conditioning`, `ea_transpose`); exclusion-map (known-findings map across all upstream items and F rows); iid (`ea_iid`); io-cli-report (shared I/O, CLI and report layer); noniid-estimators (predictors, binary vs generic paths, dictionary limits); numerics-asserts (numerics, assert classification, compiler differential); restart (`ea_restart`) |
| `2026-09-30/novel-findings/repro/verify/LOG.md` | verification log | The coordinator's re-run record, keyed by internal IDs (IID-01 = N-01, IID-02 = N-02, COND-01 = N-03, COND-02 = N-05, IO-01 = N-06, IO-06 = R-3, IO-07/08 = N-04, NUM-01 = R-1, NUM-03 = R-2, NUM-05 = N-11, …) |
| `2026-09-30/novel-findings/repro/n02-fresh/ISSUE-N02.md`, `ISSUE-N02.body.md` | filed-issue text | Draft and body of upstream **#271** |
| `2026-09-30/phase2-focused/repro/issue272/issue272_posted_body.md` | filed-issue text | Body of upstream **#272** as filed |
| `2026-09-30/reference/NIST.SP.800-90B.pdf` | reference | NIST SP 800-90B (January 2018, doi:10.6028/NIST.SP.800-90B); SHA-256 `9b0dd77131ade3617a91cd8457fa09e0dc354c273bb2220a6afeaca16e5defe7` |
| `2026-09-30/reference/full_source.txt` | reference | Concatenated listing of the 26 `cpp/` source files, each identical to upstream `87c104d`, used during the audit |

## Supporting evidence and reproduction material

Every tracked subdirectory is listed below. "Direct" counts files directly in the directory; "total" includes subdirectories. Subdirectory names under an area mirror the auditor's original working layout. MANIFEST.md gives each file's original path.

| Directory | Direct | Total | Contents |
|---|---:|---:|---|
| `audits/2026-09-30/` | 3 | 583 | All material from the three 2026-09-30 audits: the first-wave report (`AUDIT.md`), a README and the canonical findings tracker. |
| `audits/2026-09-30/novel-findings/` | 3 | 509 | Whole-codebase novel-findings audit (N-01…N-11, R-1…R-3): REPORT.md, MANIFEST.md, BRIEF.md and evidence subdirectories. |
| `audits/2026-09-30/novel-findings/agent-reports/` | 7 | 7 | The seven per-area auditor reports (scope, conformance tables, tests run, candidates, exclusions): conditioning, exclusion-map, iid, io-cli-report, noniid-estimators, numerics-asserts, restart. |
| `audits/2026-09-30/novel-findings/generators/` | 0 | 14 | Deterministic input generators (and helper modules they import), by auditor area. |
| `audits/2026-09-30/novel-findings/generators/conditioning/` | 0 | 1 | Generators for the conditioning area (see `agent-reports/conditioning.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/generators/conditioning/tr/` | 1 | 1 | Generators from the conditioning auditor's working subdirectory `tr` (original path `SCRATCH/audit/work/conditioning/tr/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/generators/iid/` | 0 | 4 | Generators for the iid area (see `agent-reports/iid.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/generators/iid/edge/` | 1 | 1 | Edge-length matrix generator. |
| `audits/2026-09-30/novel-findings/generators/iid/f01/` | 1 | 1 | N-01 input generator (`gen_bern.py`). |
| `audits/2026-09-30/novel-findings/generators/iid/f02/` | 1 | 1 | N-02 input generator (`gen_nib.py`). |
| `audits/2026-09-30/novel-findings/generators/iid/noniid/` | 1 | 1 | Generator for the 10^6-sample non-IID constructions. |
| `audits/2026-09-30/novel-findings/generators/n02-fresh/` | 0 | 1 | Generators for the n02-fresh area (see the #271 fresh-clone run); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/generators/n02-fresh/run/` | 1 | 1 | Input generator for the #271 fresh-clone runs. |
| `audits/2026-09-30/novel-findings/generators/noniid/` | 5 | 5 | Generators for the noniid area (see `agent-reports/noniid-estimators.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/generators/restart/` | 3 | 3 | Generators for the restart area (see `agent-reports/restart.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/` | 4 | 387 | Captured outputs (logs, JSON, text, `-vv` outputs) by auditor area, plus baseline build/selftest logs. |
| `audits/2026-09-30/novel-findings/logs/conditioning/` | 3 | 58 | Captured outputs for the conditioning area (see `agent-reports/conditioning.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/conditioning/asanlogs/` | 33 | 33 | Hostile-CLI runs of ea_conditioning under release and ASan/UBSan (`c*.log`), including the N-11 MPFR `emax` abort. |
| `audits/2026-09-30/novel-findings/logs/conditioning/diff/` | 4 | 4 | Captured outputs from the conditioning auditor's working subdirectory `diff` (original path `SCRATCH/audit/work/conditioning/diff/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/conditioning/grid/` | 2 | 2 | Vetted Output_Entropy reference grid against mpmath (`grid.tsv`). |
| `audits/2026-09-30/novel-findings/logs/conditioning/ndebug/` | 2 | 2 | N-03 (COND-01) reproduction under -DNDEBUG (+ASan). |
| `audits/2026-09-30/novel-findings/logs/conditioning/prov/` | 3 | 3 | Captured outputs from the conditioning auditor's working subdirectory `prov` (original path `SCRATCH/audit/work/conditioning/prov/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/conditioning/repro/` | 5 | 5 | Captured outputs from the conditioning auditor's working subdirectory `repro` (original path `SCRATCH/audit/work/conditioning/repro/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/conditioning/tr/` | 6 | 6 | Captured outputs from the conditioning auditor's working subdirectory `tr` (original path `SCRATCH/audit/work/conditioning/tr/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/exclusion-map/` | 2 | 2 | Exclusion-map auditor's working files: `notes.txt` (per-item analysis of all 270 upstream issues/PRs) and `states.txt` (upstream state snapshot at audit time). |
| `audits/2026-09-30/novel-findings/logs/iid/` | 2 | 46 | Captured outputs for the iid area (see `agent-reports/iid.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/iid/edge/` | 2 | 2 | Edge-length matrix outputs (release and ASan). |
| `audits/2026-09-30/novel-findings/logs/iid/f01/` | 7 | 7 | N-01 (IID-01) reproduction outputs. |
| `audits/2026-09-30/novel-findings/logs/iid/f02/` | 6 | 6 | N-02 (IID-02) reproduction outputs. |
| `audits/2026-09-30/novel-findings/logs/iid/f03/` | 2 | 2 | R-1 balanced-count reproduction outputs. |
| `audits/2026-09-30/novel-findings/logs/iid/meta/` | 6 | 6 | Captured outputs from the iid auditor's working subdirectory `meta` (original path `SCRATCH/audit/work/iid/meta/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/iid/noniid/` | 7 | 7 | Outputs of the chi-square/LRS stages on 10^6-sample non-IID constructions. |
| `audits/2026-09-30/novel-findings/logs/iid/pval/` | 2 | 2 | Captured outputs from the iid auditor's working subdirectory `pval` (original path `SCRATCH/audit/work/iid/pval/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/iid/ref/` | 2 | 2 | Captured outputs from the iid auditor's working subdirectory `ref` (original path `SCRATCH/audit/work/iid/ref/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/iid/threads/` | 8 | 8 | Captured outputs from the iid auditor's working subdirectory `threads` (original path `SCRATCH/audit/work/iid/threads/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/iid/tsan/` | 2 | 2 | ThreadSanitizer run outputs (IID-04: race shown, no wrong verdict; hardening only). |
| `audits/2026-09-30/novel-findings/logs/io/` | 66 | 66 | Captured outputs for the io area (see `agent-reports/io-cli-report.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/n02-fresh/` | 0 | 5 | Captured outputs for the n02-fresh area (see the #271 fresh-clone run); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/n02-fresh/run/` | 5 | 5 | Outputs of the #271 fresh-clone runs. |
| `audits/2026-09-30/novel-findings/logs/noniid/` | 0 | 53 | Captured outputs for the noniid area (see `agent-reports/noniid-estimators.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/cpp_rel_copy/` | 0 | 11 | Captured outputs from the noniid auditor's working subdirectory `cpp_rel_copy` (original path `SCRATCH/audit/work/noniid/cpp_rel_copy/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/cpp_rel_copy/selftest/` | 11 | 11 | Selftest `-vv` outputs written by a copied/instrumented build during the audit (baseline-identical outputs are kept as run evidence). |
| `audits/2026-09-30/novel-findings/logs/noniid/instr/` | 0 | 11 | Captured outputs from the noniid auditor's working subdirectory `instr` (original path `SCRATCH/audit/work/noniid/instr/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/instr/cpp/` | 0 | 11 | Captured outputs from the noniid auditor's working subdirectory `instr/cpp` (original path `SCRATCH/audit/work/noniid/instr/cpp/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/instr/cpp/selftest/` | 11 | 11 | Selftest `-vv` outputs written by a copied/instrumented build during the audit (baseline-identical outputs are kept as run evidence). |
| `audits/2026-09-30/novel-findings/logs/noniid/out/` | 12 | 20 | Predictor/reference comparison outputs, including the F09 runs (`f09b_run*.txt`) and F14 logs. |
| `audits/2026-09-30/novel-findings/logs/noniid/out/det/` | 8 | 8 | Captured outputs from the noniid auditor's working subdirectory `out/det` (original path `SCRATCH/audit/work/noniid/out/det/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/small/` | 0 | 11 | Captured outputs from the noniid auditor's working subdirectory `small` (original path `SCRATCH/audit/work/noniid/small/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/small/cpp/` | 0 | 11 | Captured outputs from the noniid auditor's working subdirectory `small/cpp` (original path `SCRATCH/audit/work/noniid/small/cpp/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/noniid/small/cpp/selftest/` | 11 | 11 | Selftest `-vv` outputs written by a copied/instrumented build during the audit (baseline-identical outputs are kept as run evidence). |
| `audits/2026-09-30/novel-findings/logs/num/` | 1 | 88 | Captured outputs for the num area (see `agent-reports/numerics-asserts.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/b/` | 0 | 18 | Outputs from compiler/flag differential builds, one subdirectory per configuration. |
| `audits/2026-09-30/novel-findings/logs/num/b/clang_fast/` | 3 | 3 | Captured outputs from the num auditor's working subdirectory `b/clang_fast` (original path `SCRATCH/audit/work/num/b/clang_fast/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/b/clang_native/` | 3 | 3 | Captured outputs from the num auditor's working subdirectory `b/clang_native` (original path `SCRATCH/audit/work/num/b/clang_native/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/b/clang_sse2_nocontract/` | 3 | 3 | Captured outputs from the num auditor's working subdirectory `b/clang_sse2_nocontract` (original path `SCRATCH/audit/work/num/b/clang_sse2_nocontract/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/b/gcc_O0/` | 3 | 3 | Captured outputs from the num auditor's working subdirectory `b/gcc_O0` (original path `SCRATCH/audit/work/num/b/gcc_O0/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/b/gcc_ndebug_san/` | 3 | 3 | Captured outputs from the num auditor's working subdirectory `b/gcc_ndebug_san` (original path `SCRATCH/audit/work/num/b/gcc_ndebug_san/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/b/gcc_nocontract/` | 3 | 3 | Captured outputs from the num auditor's working subdirectory `b/gcc_nocontract` (original path `SCRATCH/audit/work/num/b/gcc_nocontract/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/chi/` | 2 | 2 | Chi-square p-value checks against mpmath. |
| `audits/2026-09-30/novel-findings/logs/num/inp/` | 11 | 11 | Outputs for the crafted inputs of the assert sweep (the inputs themselves are regenerable and not committed). |
| `audits/2026-09-30/novel-findings/logs/num/runs/` | 50 | 50 | Captured outputs from the num auditor's working subdirectory `runs` (original path `SCRATCH/audit/work/num/runs/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/num/runs_o0/` | 6 | 6 | Captured outputs from the num auditor's working subdirectory `runs_o0` (original path `SCRATCH/audit/work/num/runs_o0/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/restart/` | 2 | 65 | Captured outputs for the restart area (see `agent-reports/restart.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/restart/data/` | 52 | 52 | Captured outputs from the restart auditor's working subdirectory `data` (original path `SCRATCH/audit/work/restart/data/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/restart/src/` | 0 | 11 | Captured outputs from the restart auditor's working subdirectory `src` (original path `SCRATCH/audit/work/restart/src/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/logs/restart/src/selftest/` | 11 | 11 | Selftest `-vv` outputs written by a copied/instrumented build during the audit (baseline-identical outputs are kept as run evidence). |
| `audits/2026-09-30/novel-findings/notes/` | 1 | 3 | Provenance notes: `FINAL-REPORT.draft.diff` records the only differences between the pre-commit draft report and `REPORT.md`. |
| `audits/2026-09-30/novel-findings/notes/curation/` | 2 | 2 | How this evidence was selected from the audit workspace: `preserve.py` (the selection rules) and `preserve_skipped.txt` (every excluded workspace file with its reason). |
| `audits/2026-09-30/novel-findings/oracle/` | 0 | 18 | Reference implementations, comparators and analysis scripts, by auditor area. |
| `audits/2026-09-30/novel-findings/oracle/conditioning/` | 2 | 4 | Reference/analysis scripts for the conditioning area (see `agent-reports/conditioning.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/oracle/conditioning/repro/` | 1 | 1 | Reference/analysis scripts from the conditioning auditor's working subdirectory `repro` (original path `SCRATCH/audit/work/conditioning/repro/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/oracle/conditioning/tr/` | 1 | 1 | Reference/analysis scripts from the conditioning auditor's working subdirectory `tr` (original path `SCRATCH/audit/work/conditioning/tr/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/oracle/iid/` | 0 | 2 | Reference/analysis scripts for the iid area (see `agent-reports/iid.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/oracle/iid/ref/` | 2 | 2 | Literal Python reference for the §5 IID statistics (`ref90b.py`) and its comparison driver. |
| `audits/2026-09-30/novel-findings/oracle/noniid/` | 8 | 8 | Reference/analysis scripts for the noniid area (see `agent-reports/noniid-estimators.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/oracle/num/` | 1 | 1 | Reference/analysis scripts for the num area (see `agent-reports/numerics-asserts.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/oracle/restart/` | 3 | 3 | Reference/analysis scripts for the restart area (see `agent-reports/restart.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/` | 0 | 77 | Harness sources, instrumented copies, patches and driver scripts, plus the coordinator verification (`verify/`) and the #271 filing text. |
| `audits/2026-09-30/novel-findings/repro/iid/` | 1 | 4 | Harness sources/scripts for the iid area (see `agent-reports/iid.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/iid/edge/` | 1 | 1 | Edge-length matrix driver. |
| `audits/2026-09-30/novel-findings/repro/iid/pval/` | 1 | 1 | Harness sources/scripts from the iid auditor's working subdirectory `pval` (original path `SCRATCH/audit/work/iid/pval/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/iid/rng/` | 1 | 1 | Harness sources/scripts from the iid auditor's working subdirectory `rng` (original path `SCRATCH/audit/work/iid/rng/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/io/` | 7 | 7 | Harness sources/scripts for the io area (see `agent-reports/io-cli-report.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/n02-fresh/` | 2 | 2 | Draft (`ISSUE-N02.md`) and filed body (`ISSUE-N02.body.md`) of upstream issue #271 (N-02). |
| `audits/2026-09-30/novel-findings/repro/noniid/` | 1 | 9 | Harness sources/scripts for the noniid area (see `agent-reports/noniid-estimators.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/noniid/h/` | 4 | 4 | Literal C++ reference used for the MultiMMC/LZ78Y checks (F09/F10). |
| `audits/2026-09-30/novel-findings/repro/noniid/instr/` | 1 | 2 | Instrumented copy of estimator sources (F10 mechanism); only files differing from upstream are kept. |
| `audits/2026-09-30/novel-findings/repro/noniid/instr/cpp/` | 0 | 1 | Harness sources/scripts from the noniid auditor's working subdirectory `instr/cpp` (original path `SCRATCH/audit/work/noniid/instr/cpp/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/noniid/instr/cpp/non_iid/` | 1 | 1 | Harness sources/scripts from the noniid auditor's working subdirectory `instr/cpp/non_iid` (original path `SCRATCH/audit/work/noniid/instr/cpp/non_iid/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/noniid/small/` | 1 | 2 | Harness sources/scripts from the noniid auditor's working subdirectory `small` (original path `SCRATCH/audit/work/noniid/small/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/noniid/small/cpp/` | 0 | 1 | Harness sources/scripts from the noniid auditor's working subdirectory `small/cpp` (original path `SCRATCH/audit/work/noniid/small/cpp/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/noniid/small/cpp/non_iid/` | 1 | 1 | Harness sources/scripts from the noniid auditor's working subdirectory `small/cpp/non_iid` (original path `SCRATCH/audit/work/noniid/small/cpp/non_iid/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/num/` | 7 | 12 | Harness sources/scripts for the num area (see `agent-reports/numerics-asserts.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/num/chi/` | 1 | 1 | Chi-square p-value check source. |
| `audits/2026-09-30/novel-findings/repro/num/f14/` | 1 | 1 | F14 harness (compression `dict[]` > 2^32 blocks). |
| `audits/2026-09-30/novel-findings/repro/num/runs/` | 1 | 1 | Harness sources/scripts from the num auditor's working subdirectory `runs` (original path `SCRATCH/audit/work/num/runs/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/num/src/` | 0 | 1 | Harness sources/scripts from the num auditor's working subdirectory `src` (original path `SCRATCH/audit/work/num/src/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/num/src/non_iid/` | 1 | 1 | Harness sources/scripts from the num auditor's working subdirectory `src/non_iid` (original path `SCRATCH/audit/work/num/src/non_iid/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/num/stubinc/` | 1 | 1 | Harness sources/scripts from the num auditor's working subdirectory `stubinc` (original path `SCRATCH/audit/work/num/stubinc/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/restart/` | 11 | 13 | Harness sources/scripts for the restart area (see `agent-reports/restart.md`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/restart/asanfast/` | 1 | 1 | Restart auditor ASan build sources/scripts (differing from upstream). |
| `audits/2026-09-30/novel-findings/repro/restart/src/` | 1 | 1 | Harness sources/scripts from the restart auditor's working subdirectory `src` (original path `SCRATCH/audit/work/restart/src/`); per-file detail in MANIFEST.md. |
| `audits/2026-09-30/novel-findings/repro/verify/` | 30 | 30 | The coordinator's re-runs on the clean `87c104d` build. `LOG.md` is the verification log; the JSON/log files are its outputs, and `toctou_shim.c` is the N-07 LD_PRELOAD shim. |
| `audits/2026-09-30/phase2-focused/` | 2 | 69 | Phase-2 focused audit (NOVEL-01…NOVEL-03): REPORT.md, MANIFEST.md and evidence subdirectories. |
| `audits/2026-09-30/phase2-focused/generators/` | 4 | 4 | Byte-exact generators for all 34 phase-2 datasets, plus the spec-text extraction script. |
| `audits/2026-09-30/phase2-focused/logs/` | 0 | 51 | Captured phase-2 outputs (oracle, #272, evidence). |
| `audits/2026-09-30/phase2-focused/logs/evidence/` | 4 | 20 | Phase-2 logs: H_I fuzz, baseline selftest, build logs. |
| `audits/2026-09-30/phase2-focused/logs/evidence/json/` | 16 | 16 | Phase-2 JSON evidence (NOVEL-02, NOVEL-03, R-3/N-06 rediscoveries, restart edge cases, sanitizer runs). |
| `audits/2026-09-30/phase2-focused/logs/issue272/` | 2 | 24 | Selftest logs from the scratch mutant runs. |
| `audits/2026-09-30/phase2-focused/logs/issue272/mutant1_outputs/` | 11 | 11 | `ea_non_iid -vv` outputs from the mutant-1 build (n×H_bitstring dropped). |
| `audits/2026-09-30/phase2-focused/logs/issue272/mutant2_outputs/` | 11 | 11 | `ea_non_iid -vv` outputs from the mutant-2 build (H_original fold dropped). |
| `audits/2026-09-30/phase2-focused/logs/oracle/` | 3 | 7 | Oracle validation logs: worked examples and tool-vs-oracle comparisons at L = 64, 4096 and 10^6. |
| `audits/2026-09-30/phase2-focused/logs/oracle/bijection/` | 4 | 4 | Bijection check outputs ({0,1} vs {17,201}; {0,255} confirms #253). |
| `audits/2026-09-30/phase2-focused/notes/` | 1 | 1 | Phase-2 working notes (`PROGRESS.md`). |
| `audits/2026-09-30/phase2-focused/oracle/` | 3 | 3 | PDF-derived estimator oracles (`oracle.py`), comparison harness (`cmp.py`) and the worked-example validator. |
| `audits/2026-09-30/phase2-focused/repro/` | 1 | 8 | Harness helpers for phase 2 (`rtime.py`). |
| `audits/2026-09-30/phase2-focused/repro/issue272/` | 7 | 7 | Exact #272 (NOVEL-01) reproduction: `repro.sh`, `repro.log`, both mutant diffs, the refdata-edit diff, the #272 body as filed, and its one-cell local-draft diff. |
| `audits/2026-09-30/reference/` | 2 | 2 | The SP 800-90B PDF and `full_source.txt` used during the audits (byte-identical to fork commit `8082231`). |

### Deduplication (2026-09-30 cleanup)

- **Removed upstream copies:** 56 byte-identical copies of upstream files were removed from the evidence tree. They were five captured copies of `cpp/selftest/refdata/*.res` (55 files) and a copy of the upstream `README.md`. Each is listed with its upstream repository path, baseline commit `87c104d`, Git blob id and SHA-256 in `2026-09-30/novel-findings/MANIFEST.md` → "Removed upstream duplicates". `git show 87c104d:<path>` recovers any of them.
- **Removed duplicate report:** the second copy of the phase-2 report was removed (see above).
- **Intentional repeats kept:** some small generated outputs (selftest `-vv` outputs of several unmodified copied builds, and mutant outputs unaffected by a mutation) are byte-identical to each other. They are kept as run evidence.

## Finding ID guide

| Series | Origin | Where defined |
|---|---|---|
| **F01–F30** | First-wave adversarial audit of `ea_non_iid` at fork `f06166f`; rows carry VERIFIED/UNVERIFIED status | `2026-09-30/AUDIT.md`; F05/F09/F10/F13/F14/F20/F23 re-assessed in `2026-09-30/novel-findings/REPORT.md` §4 |
| **N-01–N-11** | Novel findings of the whole-codebase audit (all five executables and shared code) | `2026-09-30/novel-findings/REPORT.md` §2 |
| **R-1–R-3** | Residuals of closed upstream fixes (#246, #178, #183): known root cause, incomplete fix | `2026-09-30/novel-findings/REPORT.md` §3 |
| **NOVEL-01–NOVEL-03** | Novel findings of the phase-2 focused audit | `2026-09-30/phase2-focused/REPORT.md` |

Internal working IDs (IID-xx, COND-xx, IO-xx, NUM-xx, RESTART-xx, TRANS-xx) appear in `agent-reports/` and `repro/verify/LOG.md`. They map to N/R IDs as recorded in `LOG.md` and in the novel-findings report's rejected/merged table.

## Upstream issue mapping

Only mappings stated in the audit files are listed. Current status and next actions are in `2026-09-30/FINDINGS-TRACKER.md`; re-check GitHub before relying on them.

| Finding | Upstream item(s) | Relationship (as documented) |
|---|---|---|
| F01 | #253, PR #256 | filed; fix PR from branch `fix/bitstring-gate-word-size` |
| F02 | #254 | filed |
| F03, F05 | #255 (related #238) | filed together |
| F04 | #258 (dup #265) | filed |
| F11 | #263, PR #270 | filed after the AUDIT round-2 note (mapping recorded in FINDINGS-TRACKER.md); fix PR from branch `fix/compression-min-test-blocks` |
| F12 | #264 | filed after the AUDIT round-2 note (mapping recorded in FINDINGS-TRACKER.md) |
| F15 | #261 (dup #262) | filed |
| F16 | #257, PR #268 (dup PR #269) | filed; fix PR from branch `fix/multimmc-binary-overread` |
| F17 | #214, #163, #52 | known, closed; not refiled |
| F18 | #259 (dup #266) | filed |
| F19 | #260 (dup #267) | filed |
| F07 | #22 | known, closed |
| N-02 | #271 | filed |
| NOVEL-01 | #272 | filed |
| R-1 | #246 (PR #248) | residual of closed item; not reported upstream |
| R-2 | #178 | residual of closed item; not reported upstream |
| R-3 | #183 | residual/regression (merge `4d68e47`) of closed item; not reported upstream |
| (referenced) | #153, #195, #251, #252, #56/#95/#209/#224, #236 | known upstream items cited by the audits; not audit findings |

## Preservation rules

1. Historical reports stay **byte-for-byte unchanged**: `2026-09-30/AUDIT.md`, both `REPORT.md` files, `BRIEF.md`, the agent reports and `LOG.md`.
2. New evidence, status or corrections are **added as new files** or recorded in the tracker, never written into old reports.
3. Do not commit generated binaries, build trees, dependency directories, packaging archives, or large datasets that deterministic generators reproduce. Remove byte-identical copies of upstream source, but record their upstream path and baseline commit.
4. Repro scripts, small logs, JSON outputs, oracle/reference code and manifests are appropriate to preserve. Record each file's origin and SHA-256 in a manifest.
5. Check official NIST upstream status (issue/PR state on `usnistgov/SP800-90B_EntropyAssessment`) before claiming a finding is fixed, accepted or rejected. A closed upstream issue is not a fix, and a fix branch on this fork is not an upstream fix.
6. Absolute `/tmp/...` paths inside preserved evidence refer to the original session workspaces. They are left unedited to keep the evidence unaltered.
