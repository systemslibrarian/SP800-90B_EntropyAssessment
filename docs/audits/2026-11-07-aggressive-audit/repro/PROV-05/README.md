# PROV-05 -- -vvv prints no per-estimator lines (estimators print at verbose == 3 exactly; -vvv is 4)

**Provisional ID:** PROV-05 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (text only)
**Direction:** neutral
**Component:** cpp/non_iid_main.cpp:main() verbose starts at 1 (:97), `case 'v': verbose++` (:176), summary at `verbose > 2` (:653-664); estimators test `verbose == 3` (cpp/shared/most_common.h:33, cpp/non_iid/markov_test.h:55, cpp/shared/utils.h:1243 predictionEstimate, and the others). Usage text non_iid_main.cpp:35 "-v ... Can be used multiple times."
**Spec:** n/a (CLI contract).
**Prior-fix interaction (rule 12):** None; upstream-inherited. Note cpp/selftest/selftest, compareresults.pl and pin-check.sh all key on -vv (level 3) labels and are unaffected.
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.10 (measured 17 vs 0 lines).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: -vvv -> 0 'min entropy = ' lines, 1 'Assessed min entropy:' line, 12 stdout lines total; -vv (control) -> 17 per-estimator lines.

**What this reproducer does not establish:** ea_iid/ea_restart not run; the same `== 3` tests are in the shared estimator headers.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-05-observed.log` and `PROV-05-control.log`.

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
# PROV-05 observed.txt  2026-11-07 21:56:09 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -vvv /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[vvv]=0  stdout=vvv.out stderr=vvv.err
-vvv: per-estimator 'min entropy = ' lines: 0 ; 'Assessed min entropy:' lines: 1 ; total stdout lines: 12
-vvv stdout (verbatim):
  | Loaded file: '/Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin' (SHA-256 hash 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803 of assessed bytes)
  | Loaded 10000 samples of 256 distinct 8-bit-wide symbols
  | 
  | *** Warning: dataset contains 10000 samples; SP 800-90B Section 3.1.1 requires at least 1000000.
  | *** EA_ALLOW_SHORT_DATASET is set, so this run continues for test purposes only.
  | *** Its result is NOT a compliant SP 800-90B assessment. ***
  | 
  | Number of Binary Symbols: 80000
  | H_bitstring = 0.73261171806065617
  | H_bitstring Per Symbol = 5.8608937444852494
  | H_original = 6.6364412870612322
  | Assessed min entropy: 5.8608937444852494
usage text for -v: non_iid_main.cpp:35:    printf("\t -v: Optional verbosity flag for more output. Can be used multiple times.\n");
RESULT: PASS -- -vvv prints the summary but zero per-estimator lines: more -v flags give LESS output than -vv
```

### control.txt (verbatim)

```
# PROV-05 control.txt  2026-11-07 21:56:09 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -vv /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[vv]=0  stdout=vv.out stderr=vv.err
-vv: per-estimator 'min entropy = ' lines: 17 ; 'Assessed min entropy:' lines: 1
  | Bitstring Most Common Value Estimate: min entropy = 0.9833867846591503
  | Literal Most Common Value Estimate: min entropy = 7.0104540377360411
  | Bitstring Collision Estimate: min entropy = 0.83205298221524804
  | Bitstring Markov Estimate: min entropy = 0.99772497672796534
  | Bitstring Compression Estimate: min entropy = 0.73261171806065617
  | Bitstring t-Tuple Estimate: min entropy = 0.91078644573541423
  | Bitstring LRS Estimate: min entropy = 0.98193035773637416
  | Literal t-Tuple Estimate: min entropy = 7.0104540377360411
  | Literal LRS Estimate: min entropy = 7.2891986717206523
  | Bitstring MultiMCW Prediction Estimate: min entropy = 0.99453711551450596
  | Literal MultiMCW Prediction Estimate: min entropy = 7.3751922497299107
  | Bitstring Lag Prediction Estimate: min entropy = 0.98969349388795491
  | Literal Lag Prediction Estimate: min entropy = 6.6364412870612322
  | Bitstring MultiMMC Prediction Estimate: min entropy = 0.98781454404229407
  | Literal MultiMMC Prediction Estimate: min entropy = 7.3276276791880877
  | Bitstring LZ78Y Prediction Estimate: min entropy = 0.98808180379990307
  | Literal LZ78Y Prediction Estimate: min entropy = 7.3533553938353844
RESULT: CONTROL-OK -- -vv prints 17 per-estimator lines; adding a third -v (run.sh) removes all of them
```
