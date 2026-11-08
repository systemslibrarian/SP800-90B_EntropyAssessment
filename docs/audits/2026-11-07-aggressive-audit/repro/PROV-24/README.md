# PROV-24 -- ea_iid aborts (assert n>=p in periodicity, SIGABRT 134) on inputs shorter than the largest lag under the test escape

**Provisional ID:** PROV-24 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (crash under EA_ALLOW_SHORT_DATASET=1 only; an assert is fail-closed, not UB; the -o placeholder stays)
**Direction:** crash
**Component:** cpp/iid/permutation_tests.h:periodicity() :256 `assert(n>=p);` with p = 32 the largest lag (:402-407); production builds keep asserts (cpp/Makefile:51 defines no NDEBUG). Reached only because intake's 1,000,000 minimum is bypassed by the escape.
**Spec:** SP 800-90B 5.1.9 (PDF p. 42): "lag parameter p ... p < L ... For i = 1 to L - p: If (si = si+p), increment T", p in {1, 2, 8, 16, 32}: the statistic is undefined for L <= p.
**Prior-fix interaction (rule 12):** F15 (21b0a31) and upstream #261 turned other tiny-input asserts into -1 declines; this assert was not among them. C14 leaves the placeholder in place (observed: ab.json errorLevel -1 after the abort).
**Analysis-phase source (re-checked here):** logs/analysis/mcv.md section 7 item 1 (MEASURED, analysis-mcv-probe1-iid-spec-example.log exit 134).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: the 20 samples of 6.3.1's worked example (sha256 088df27d...) -> 'Assertion failed: (n>=p), function periodicity, file permutation_tests.h, line 256.', exit 134, ab.json is the placeholder. Control (same bytes x5, L = 100): no assertion, battery completes (exit 1, errorLevel 2 -- the example sequence is non-IID).

**What this reproducer does not establish:** Not reachable without the escape (intake refuses < 1,000,000 samples).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-24-observed.log` and `PROV-24-control.log`.

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
# PROV-24 observed.txt  2026-11-07 21:56:28 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
input sha256 088df27d16a3b5cc53a47049f924a13ac135c668ecc9805aec6f9d683acf1da1  (the 20 samples of SP 800-90B 6.3.1's worked example, PDF p. 50; width inferred 2)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-24/out/ab.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-24/out/ex20.bin
rc[iid]=134  stdout=ab.out stderr=ab.err
stderr (verbatim):
  | Assertion failed: (n>=p), function periodicity, file permutation_tests.h, line 256.
rc=134 assertion lines=1 ; ab.json errorLevel=-1 reportComplete=false
code: permutation_tests.h:256:	assert(n>=p); 
RESULT: PASS -- SIGABRT (exit 134) from assert(n>=p) in periodicity() on a 20-sample input under the escape; the C14 placeholder is what remains at -o
```

### control.txt (verbatim)

```
# PROV-24 control.txt  2026-11-07 21:56:28 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
input sha256 683a02f12d1233e76262550e1ac67b93587c9c06f8e5e43dc578d527715e9edb  (100 samples = the worked example x5; width inferred 2)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-24/out/c_ab.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-24/out/ex100.bin
rc[iid]=1  stdout=c_ab.out stderr=c_ab.err
rc=1 assertion lines=0 ; c_ab.json errorLevel=2 assessmentComplete=true
RESULT: CONTROL-OK -- at L = 100 the battery completes (rc 1, a verdict); the abort in run.sh is L = 20 < p = 32
```
