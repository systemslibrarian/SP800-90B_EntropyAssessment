# PROV-20 -- Contradictory mode flags (-i -c, -a -t) are resolved silently by the last one

**Provisional ID:** PROV-20 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (operator error is silent; the two modes' figures differ in unit, see PROV-02)
**Direction:** neutral
**Component:** cpp/non_iid_main.cpp:main() getopt cases :163-174 (`case 'i'`/`'c'` assign initial_entropy; `case 'a'`/`'t'` assign all_bits; last assignment wins, no diagnostic).
**Spec:** n/a (CLI contract).
**Prior-fix interaction (rule 12):** None.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 4.3 and 9.12 (MEASURED i-then-c / c-then-i / a-then-t rc=0).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: `-i -c` prints h' 0.732612 (conditioned mode), `-c -i` prints H_original 6.636441 (initial mode), `-a -t -vv` runs; all exit 0; zero diagnostic lines. Control: `-c` alone prints the identical h' 0.732612.

**What this reproducer does not establish:** Only ea_non_iid run; ea_iid has the same cases.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-20-observed.log` and `PROV-20-control.log`.

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
# PROV-20 observed.txt  2026-11-07 21:56:22 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -i -c /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[i_then_c]=0  stdout=ic.out stderr=ic.err
  -i -c: rc=0  h'=0.732612  H_original lines=0  (conditioned mode won)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -c -i /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[c_then_i]=0  stdout=ci.out stderr=ci.err
  -c -i: rc=0  H_original=6.636441  h' lines=0  (initial mode won)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -a -t -vv /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[a_then_t]=0  stdout=at.out stderr=at.err
  -a -t -vv: rc=0  Number of Binary Symbols line: Number of Binary Symbols: 80000
diagnostic lines about the contradiction in any of the six streams: 0
RESULT: PASS -- -i -c assesses in -c mode, -c -i in -i mode, -a -t truncates; all exit 0 with no word about the contradiction
```

### control.txt (verbatim)

```
# PROV-20 control.txt  2026-11-07 21:56:23 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -c /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[c_only]=0  stdout=c_c.out stderr=c_c.err
  -c alone: rc=0 h'=0.732612
  run.sh's -i -c gave h'=0.732612
RESULT: CONTROL-OK -- -c alone and -i -c print the same h' (0.732612): the earlier -i was silently discarded
```
