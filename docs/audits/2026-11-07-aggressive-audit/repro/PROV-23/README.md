# PROV-23 -- permutationTestResults carry partial C0/C1/C2 counts (early termination) with no field for the number of permutations evaluated

**Provisional ID:** PROV-23 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (reporting; verdict unchanged -- the early termination is proved verdict-equivalent in iid-permutation.md 2.1)
**Direction:** neutral
**Component:** cpp/iid/permutation_tests.h:permutation_tests() :672-674 (stop a statistic once C0+C1 > 5 and C1+C2 > 5), populateTestCase() :484-576 (three PermutationTestResult objects, 'iteration' 0/1/2 = C0/C1/C2); cpp/iid/permutation_test_result.h (no denominator field).
**Spec:** SP 800-90B 5.1 Figure 4 (PDF p. 37): "2. For j = 1 to 10 000 ... 2.2.2 If (T > Ti), increment Ci,0. If (T = Ti), increment Ci,1. 3. If ((Ci,0 + Ci,1 <= 5) or (Ci,0 >= 9995)) for any i, reject" -- the counters the standard defines are out of exactly 10,000.
**Prior-fix interaction (rule 12):** NOVEL-03 (25fbb54) added dataLayout to these objects; #252 (007d0e7) made the battery fail closed; neither added the denominator. OC-53 excludes the field from bit-identity comparison because it varies.
**Analysis-phase source (re-checked here):** logs/analysis/iid-permutation.md 2.9 (measured P1 avgCollision 6/0/39).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: 10,000 fair bits -> IID true, all 19 statistics have C-sums between 12 and 116 (e.g. covariance32 110/0/6, periodicity8 6/0/6); no key names the number evaluated. Control (anti-correlated lag 64: b_i = 1-b_{i-64} w.p. 0.75): chi-square and LRS pass, permutation fails; avgCollision, covariance8, maxCollision at C0 = 10000 and covariance16/32, periodicity16/32 at C2 = 10000 -- sums of exactly 10,000 only for the statistics that ran to the end. A first control attempt with POSITIVE lag-64 copying failed GOF and LRS first (kept as logs/repro/PROV-23-control.first-attempt.log).

**What this reproducer does not establish:** The IID verdict is urandom-seeded; the run.sh PASS criterion (any partial sum, no denominator key) does not depend on the verdict, the control's does (it says so if the battery is skipped).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-23-observed.log` and `PROV-23-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-23 observed.txt  2026-11-07 21:56:25 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
input sha256 8414daeefef2ee495b135f83d6d210223404b1f5f1dfce303e5019d1e89644d3  (10,000 fair bits, seed 23, width 1)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-23/out/p.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-23/out/fair10k.bin 1
rc[iid]=0  stdout=p.out stderr=p.err
rc=0 errorLevel=0 IID=true
  avgCollision           C0=    6 C1=    0 C2=   17  sum=   23  partial
  compression            C0=    5 C1=    1 C2=   10  sum=   16  partial
  covariance1            C0=   13 C1=    0 C2=    6  sum=   19  partial
  covariance16           C0=    5 C1=    1 C2=   47  sum=   53  partial
  covariance2            C0=    6 C1=    0 C2=    6  sum=   12  partial
  covariance32           C0=  110 C1=    0 C2=    6  sum=  116  partial
  covariance8            C0=    6 C1=    0 C2=    8  sum=   14  partial
  excursion              C0=   15 C1=    0 C2=    6  sum=   21  partial
  lenDirectionalRuns     C0=    5 C1=    4 C2=    2  sum=   11  partial
  lenRunsMedian          C0=    2 C1=    4 C2=   32  sum=   38  partial
  maxCollision           C0=    5 C1=    1 C2=   12  sum=   18  partial
  numDirectionalRuns     C0=    5 C1=    1 C2=    6  sum=   12  partial
  numIncreasesDecreases  C0=    6 C1=    0 C2=    6  sum=   12  partial
  numRunsMedian          C0=    6 C1=    0 C2=   24  sum=   30  partial
  periodicity1           C0=    6 C1=    0 C2=    6  sum=   12  partial
  periodicity16          C0=    6 C1=    0 C2=   15  sum=   21  partial
  periodicity2           C0=    9 C1=    0 C2=    6  sum=   15  partial
  periodicity32          C0=    7 C1=    0 C2=    6  sum=   13  partial
  periodicity8           C0=    6 C1=    0 C2=    6  sum=   12  partial
statistics with partial counts: 19 of 19 ; keys that could name the number of permutations evaluated: none
DEFECT
RESULT: PASS -- the counters are partial (early termination) and nothing in the report states the number of permutations evaluated per statistic
```

### control.txt (verbatim)

```
# PROV-23 control.txt  2026-11-07 21:56:25 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
input sha256 2fb87448f625ebb60588962d1b5103fade48676d173ba1d6b31e7f7a08b49ae5  (10,000 bits, b_i = 1-b_{i-64} w.p. 0.75 else fresh, seed 2323)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -vv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-23/out/c_p.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-23/out/lag64anti.bin 1
rc[iid]=1  stdout=c_p.out stderr=c_p.err
rc=1 errorLevel=2 IID=false
  | Chi square tests: Passed
  | Length of longest repeated substring test: Passed
  | IID permutation tests: Failed
statistics evaluated for all 10,000 permutations: avgCollision(C0=10000,C1=0,C2=0), covariance16(C0=0,C1=0,C2=10000), covariance32(C0=0,C1=0,C2=10000), covariance8(C0=10000,C1=0,C2=0), maxCollision(C0=10000,C1=0,C2=0), numRunsMedian(C0=1,C1=0,C2=9999), periodicity16(C0=0,C1=0,C2=10000), periodicity32(C0=0,C1=0,C2=10000)
FULL
RESULT: CONTROL-OK -- a failing statistic runs the full 10,000 permutations and its C-sum is 10,000; the passing statistics in run.sh stop early with sums of a few dozen, and the report does not say which happened
```
