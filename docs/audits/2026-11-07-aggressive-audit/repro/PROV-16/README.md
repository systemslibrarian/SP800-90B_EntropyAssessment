# PROV-16 -- MCV estimate is IEEE negative zero when p_u clamps to 1: text '-0', JSON -0.0 (propagates to hAssessed)

**Provisional ID:** PROV-16 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (cosmetic; conservative)
**Direction:** neutral / conservative
**Component:** cpp/shared/most_common.h:30-31 (`ubound = min(1.0, ...)`; `entEst = -log2(ubound)` = -0.0 when ubound == 1.0); the folds min(ret, H) in cpp/non_iid_main.cpp keep -0.0 because 0.0 < -0.0 is false; jsoncpp writes -0.0.
**Spec:** SP 800-90B 6.3.1 (PDF p. 49): "p_u = min(1, p-hat + 2.576 sqrt(p-hat(1 - p-hat)/(L - 1)))" ... "The estimated min-entropy is -log2(p_u)." -log2(1) = 0 (zero bits).
**Prior-fix interaction (rule 12):** F13/OC-58 argument order `min(1.0, x)` (most_common.h:26-30) is what yields exactly 1.0 here; D-1 (ZALPHA) sets the confidence term. Inherited behaviour of -log2(1.0).
**Analysis-phase source (re-checked here):** logs/analysis/mcv.md S-4 and E-2 (MEASURED probe 2 via ea_iid); intake.md S9 / 2.10 (-0 printed on two samples).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED with ea_non_iid: 20,000 samples with one 0x01 -> 'Literal Most Common Value Estimate: min entropy = -0'; JSON 'Most Common Value' hOriginal -0.0 (negative zero True), Overall hAssessed -0.0, 'Assessed min entropy: -0'; tTupleRes -0.0 as well. Control (ten 0x01): hOriginal 0.00013391324219584911, positive.

**What this reproducer does not establish:** Under the escape only (20,000 samples); at L = 1e6 the clamp needs one symbol at >= L - ~6 occurrences (mcv.md E-10), reachable but not run.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-16-observed.log` and `PROV-16-control.log`.

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
# PROV-16 observed.txt  2026-11-07 21:56:18 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
input sha256 8b99602a725b160f22343284ffef6125ae2c042407a8e14a13f3ef3e8ecd95ea  (20,000 samples: 19,999 x 0x00, one 0x01 at index 12345; declared width 1)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/one-in-20000.bin 1
rc[vvv]=0  stdout=z.out stderr=z.err
  | Assessed min entropy: -0
raw JSON text lines containing '-0': 
  | 6:   "commandline" : "/Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/one-in-20000.bin 1",
  | 9:   "filename" : "/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/one-in-20000.bin",
  | 15:         "hOriginal" : -0.0,
  | 22:         "hOriginal" : -0.0,
  | 26:         "hOriginal" : 7.2143713666945002e-05,
  | 30:         "hOriginal" : -0.0,
  | 34:         "tTupleRes" : -0.0,
  | 42:         "hOriginal" : -0.0,
  | 46:         "hOriginal" : -0.0,
  | 50:         "hOriginal" : -0.0,
  | 54:         "hOriginal" : -0.0,
  | 59:         "hAssessed" : -0.0,
  | 60:         "hOriginal" : -0.0,
MCV hOriginal = -0.0 (negative zero: True) ; Overall hAssessed = -0.0 (negative zero: True) ; str compare to '0': False
DEFECT
RESULT: PASS -- p_u clamps to 1 -> -log2(1.0) = -0.0: text 'min entropy = -0', JSON hOriginal -0.0 on the MCV element (and hAssessed -0.0)
```

### control.txt (verbatim)

```
# PROV-16 control.txt  2026-11-07 21:56:19 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
input sha256 9da53e09266ff711b1168d2f8a01153c0d0c749ab856552f450d331358aab652  (20,000 samples: 19,990 x 0x00, ten 0x01 at seeded positions; width 1)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/c_z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/ten-in-20000.bin 1
rc[vvv]=0  stdout=c_z.out stderr=c_z.err
JSON MCV hOriginal = 0.00013391324219584911 ; lines with '-0' in the JSON: 5
RESULT: CONTROL-OK -- with p_u < 1 the MCV estimate is positive (0.00013391324219584911); the negative zero in run.sh is the clamp's -log2(1.0)
```
