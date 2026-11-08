# PROV-04 -- 'Symbols appear to be narrower than described' is printed under -q and never reaches the JSON (errorLevel stays 0)

**Provisional ID:** PROV-04 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (reporting; the mis-declared width lowers the figure on this fixture, so the direction is conservative)
**Direction:** neutral / conservative
**Component:** cpp/shared/utils.h:read_file_subset() :483-485 (unconditional printf + `testRun->errorMsg = ...` with errorLevel untouched; same in read_file :671-673); cpp/shared/test_run_base.h:GetBaseJson() :69-72 (`if (errorLevel != 0) baseJson["errorMessage"] = errorMsg;`).
**Spec:** n/a (report integrity).
**Prior-fix interaction (rule 12):** F02 (97571de) added bitsPerSymbol/bitsPerSymbolInferred to the JSON; the test_run_base.h:38-43 decision not to add a warning concerns the INFERRED-width case, not this pre-existing declared-wider warning. Inherited from upstream.
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.5 item 2 (Q4d); intake.md 2.8 and S6; cli-build.md 3.3; aggregation.md headline item 6; prior-repairs.md F02 row.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: `-q -o w8.json rand4_short.bin 8` -> stdout carries the warning (plus the escape banner), exit 0, JSON errorLevel 0, errorMessage absent, bitsPerSymbol 8 / bitsPerSymbolInferred false, hAssessed 1.5157083660394497 (vs 3.2154882678767365 declared 4).

**What this reproducer does not establish:** Only ea_non_iid was run; ea_iid and ea_restart share read_file_subset/read_file and the same GetBaseJson, so the same loss is expected there (not measured).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-04-observed.log` and `PROV-04-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-04 observed.txt  2026-11-07 21:56:08 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 a9e2169cb1accc78cd23892d793a232b84b0cd13ccc3923526e0b20762bd77ac  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand4_short.bin (10,000 samples, 4-bit values; declared 8 below)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-04/out/w8.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand4_short.bin 8
rc[declared8_q]=0  stdout=w8.out stderr=w8.err
stdout under -q (verbatim):
  | Warning: Symbols appear to be narrower than described.
  | 
  | *** Warning: dataset contains 10000 samples; SP 800-90B Section 3.1.1 requires at least 1000000.
  | *** EA_ALLOW_SHORT_DATASET is set, so this run continues for test purposes only.
  | *** Its result is NOT a compliant SP 800-90B assessment. ***
  | 
warning lines on stdout under -q: 1
JSON errorLevel=0 errorMessage=<absent> bitsPerSymbol=8 bitsPerSymbolInferred=false
JSON top-level keys: IID assessedSampleCount bitsPerSymbol bitsPerSymbolInferred commandline dateTimeStamp errorLevel filename nonCompliantShortDataset sha256 sha256Scope testCases toolVersion type
JSON Overall.hAssessed=1.5157083660394497
RESULT: PASS -- the width-mismatch warning is printed on stdout despite -q, exit 0, and the JSON (errorLevel 0) carries no errorMessage, no warning field; a JSON-only consumer cannot see that the declared width was wrong
```

### control.txt (verbatim)

```
# PROV-04 control.txt  2026-11-07 21:56:09 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-04/out/w4.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand4_short.bin 4
rc[declared4_q]=0  stdout=w4.out stderr=w4.err
stdout under -q (verbatim):
  | 
  | *** Warning: dataset contains 10000 samples; SP 800-90B Section 3.1.1 requires at least 1000000.
  | *** EA_ALLOW_SHORT_DATASET is set, so this run continues for test purposes only.
  | *** Its result is NOT a compliant SP 800-90B assessment. ***
  | 
warning lines: 0 ; JSON errorLevel=0 bitsPerSymbol=4 errorMessage=<absent> hAssessed=3.2154882678767365
RESULT: CONTROL-OK -- declared at the true width: no warning, identical JSON shape -- the declared-8 run differs only by the lost warning
```
