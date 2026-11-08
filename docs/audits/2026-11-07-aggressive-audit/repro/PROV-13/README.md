# PROV-13 -- Non-binary chi-square independence test with df <= 0 is reported as applied and PASSED (5.2.1: 'do not apply the test')

**Provisional ID:** PROV-13 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (reporting; the battery verdict coincides with the standard's non-application; bounded overstatement potential at compliant size, see expected.txt)
**Direction:** neutral
**Component:** cpp/iid/chi_square_tests.h:chi_square_independence() :569 (`df = bin_expectations.size() - alphabet_size;`, size_t minus int stored in int -> -1), chi_square_pvalue() :368-370 over cephes_igamc() :279-281 (`if ((x <= 0) || (a <= 0)) return 1.0;`), chi_square_tests() :678-695 (`pvalue < 0.001` false -> pass). JSON: cpp/iid/iid_test_case.h:41-46 booleans only.
**Spec:** SP 800-90B 5.2.1 (PDF p. 44): "The test fails if T is greater than the critical value of the Chi-square test statistic with (nbin - 1) - (k - 1) = nbin - k degrees of freedom when the probability of type I error is chosen as 0.001. If the value of degrees of freedom is less than one, do not apply the test."
**Prior-fix interaction (rule 12):** N-01 (c8799f4) fixed the analogous BINARY shape (m = 1 -> igamc(0,0) = 1 -> pass) by returning false; the non-binary df < 1 shape was not touched. Also reachable through ea_restart -i (same function, rows and columns).
**Analysis-phase source (re-checked here):** logs/analysis/iid-chisquare-lrs.md 2.3(d) (MEASURED, analysis-iid-chisq-dfneg.out) and edge case 4.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED on the regenerated input (sha256 7aed588a... identical to corpus/iid-chisq-dfneg.bin; L = 2000, k = 3, counts 1992/4/4): 'Chi square independence: T = 0.17059228241416982', 'df = -1', 'P-value = 1', 'Chi square tests: Passed'; JSON passedChiSquareTests true, ranChiSquareTests true; battery passed, exit 0. Control (700/650/650): df = 6, P-value 0.7747356989584685.

**What this reproducer does not establish:** Compliant-size reachability (nbin <= k at L = 1e6 needs one symbol at >= ~99 % of the mass) is derived, not measured.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-13-observed.log` and `PROV-13-control.log`.

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
# PROV-13 observed.txt  2026-11-07 21:56:16 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
input ok 2000 [1992, 4, 4] 2000 sha256 7aed588a0c91bada25332b13b6e3af94ea8daae8c84764dccc0a5ea4c816224e  (corpus/iid-chisq-dfneg.bin was 7aed588a0c91bada25332b13b6e3af94ea8daae8c84764dccc0a5ea4c816224e)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-13/out/df.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-13/out/dfneg.bin 2
rc[iid_vvv]=0  stdout=df.out stderr=df.err
  | Chi square independence: T = 0.17059228241416982
  | Chi square independence: df = -1
  | Chi square independence: P-value = 1
  | Chi square goodness of fit: T = 0
  | Chi square goodness of fit: df = 0
  | Chi square goodness of fit: P-value = 1
  | Chi square tests: Passed
JSON passedChiSquareTests/ranChiSquareTests: true true ; rc=0 errorLevel=0 IID=true
JSON keys carrying df, T, p-value or 'applied': passedChiSquareTests,ranChiSquareTests
RESULT: PASS -- df = -1 (< 1) printed with P-value = 1 and 'Chi square tests: Passed'; JSON passedChiSquareTests true -- a test the standard says not to apply is reported as applied and passed
```

### control.txt (verbatim)

```
# PROV-13 control.txt  2026-11-07 21:56:16 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
input ok 2000 [700, 650, 650] 2001 sha256 df0929c16affa55d1140e844aed915244c0799194ae73039a92dba64f3d45d75
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-13/out/bal.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-13/out/balanced.bin 2
rc[iid_vvv]=0  stdout=bal.out stderr=bal.err
  | Chi square independence: T = 3.2664654027291435
  | Chi square independence: df = 6
  | Chi square independence: P-value = 0.7747356989584685
  | Chi square goodness of fit: T = 18.096703296703296
  | Chi square goodness of fit: df = 18
  | Chi square goodness of fit: P-value = 0.44929932758944602
  | Chi square tests: Passed
rc=0 df=6 pv=0.7747356989584685 -> OK
RESULT: CONTROL-OK -- with nbin > k the test is applied: df = 6, P-value = 0.7747356989584685 in (0,1); the df = -1 / P = 1 pair in run.sh is the not-applicable case misreported
```
