# PROV-03 -- JSON mcvEstimateMode/PHat/PU carry only the LITERAL triple; the Bitstring MCV intermediates are not in the report (F23 sub-claim a)

**Provisional ID:** PROV-03 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (reporting; hAssessed is unaffected)
**Direction:** neutral
**Component:** cpp/non_iid_main.cpp:main() :362-376 (one `NonIidTestCase tc631` passed to most_common(... "Bitstring", tc631) at :365 and to most_common(... "Literal", tc631) at :372); cpp/shared/most_common.h:41-44 (the three fields overwritten per call; `literal_mcv_estimate = literal.compare(label)` inverted and dead, test_case_base.h:66-67).
**Spec:** SP 800-90B 3.1.3 (PDF p. 20): an H_original per sample and, for non-binary data, an H_bitstring per bit are both estimated; 6.3.1 (PDF p. 49) defines the MCV estimate by p-hat and p_u. Two MCV estimates therefore run and both have a mode count / p-hat / p_u.
**Prior-fix interaction (rule 12):** Tracker F23 sub-claim (a). No fork repair touched tc631; upstream-inherited.
**Analysis-phase source (re-checked here):** logs/analysis/mcv.md S-2 (probe 3) and S-3; output.md 2.3.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED at -vv: text Bitstring triple (mode 40099, p-hat 0.5012375, p_u 0.50579098043220405) and Literal triple (58, 0.0058, 0.0077560937775866317); JSON 'Most Common Value' carries exactly the Literal triple; the Bitstring mode count 40099 occurs nowhere in the JSON text.

**What this reproducer does not establish:** Under -c the single triple is the Bitstring one (mcv.md probe 4), so the meaning of the three keys depends on the mode; not re-run here. Note the first attempt of this script used -vvv and found no estimator lines at all -- that is PROV-05, not this item.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-03-observed.log` and `PROV-03-control.log`.

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
# PROV-03 observed.txt  2026-11-07 21:56:07 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin (10,000 samples, 8-bit)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -i -vv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-03/out/m8.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[i8_vv]=0  stdout=m8.out stderr=m8.err
text Bitstring MCV: mode=40099 p-hat=0.5012375 p_u=0.50579098043220405
text Literal   MCV: mode=58 p-hat=0.0057999999999999996 p_u=0.0077560937775866317
JSON 'Most Common Value': mcvEstimateMode=58.0 mcvEstimatePHat=0.0058 mcvEstimatePU=0.007756093777586632 hBitstring=0.9833867846591503 hOriginal=7.010454037736041
number of mcvEstimate* keys on that element: 3 (two estimates ran; 3 keys = one triple)
occurrences of the Bitstring mode count '40099' anywhere in the JSON text: 0
json==literal: True json==bitstring: False literal!=bitstring: True
DEFECT
RESULT: PASS -- under -i the single JSON MCV triple is the Literal one; the Bitstring triple (printed at -vv) is not in the report because the Literal call overwrote the shared tc631
```

### control.txt (verbatim)

```
# PROV-03 control.txt  2026-11-07 21:56:08 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 3814404497a3b912f8d3db6bc05a99338f0986cd75fe54af2a5f1bdb0a12a583  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin (10,000 samples, 1-bit)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -i -vv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-03/out/m1.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1
rc[i1_vv]=0  stdout=m1.out stderr=m1.err
Bitstring MCV lines in text: 0 (0 expected)
text Literal mode=5008 ; JSON mcvEstimateMode=5008.0
RESULT: CONTROL-OK -- one MCV estimate ran, one triple in the JSON, and it matches the only triple printed; the ambiguity needs two estimates sharing tc631
```
