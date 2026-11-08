# PROV-18 -- EXCLUDED-SCOPE: ea_conditioning folds collision_test's -1 'declined' sentinel into h' (no >= 0 guard)

**Provisional ID:** PROV-18 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW in scope terms (unsupported tool; the supported callers are guarded); the mechanism itself is a wrong result in the conservative direction (h' = -1, h_out negative)
**Direction:** understates (garbage, conservative)
**Component:** cpp/conditioning_main.cpp:computeEntropyOfConditionedData() :388-389 (`ret_min_entropy = collision_test(...); h_bitstring = min(ret_min_entropy, h_bitstring);`) vs the guarded folds in the same function (:397, :405, :410, :416, :422, :428, :434); cpp/non_iid/collision_test.h:47-50 (`if (v < 2) return -1.0;`). ea_conditioning has no dataset_meets_minimum() call and no alph_size <= 1 refusal (grep: 0 each).
**Spec:** SP 800-90B 6.3.2 step 5 (PDF p. 50) needs v >= 2 collisions for the sample standard deviation; 3.1.5.2 (PDF p. 25): "Let the obtained entropy estimate per bit be h'" -- an entropy in [0, 1].
**Prior-fix interaction (rule 12):** F12 (c217f20) added the -1 sentinel to collision_test and the `>= 0` guard to non_iid_main.cpp; R-2 (d892b90) guarded restart_main.cpp; conditioning_main.cpp was not updated. N-03 records ea_conditioning as unsupported (cpp/Makefile SUPPORTED_TARGETS excludes it).
**Analysis-phase source (re-checked here):** Task candidate (18); logs/analysis/mcv.md 2.4 (conditioning_main.cpp:376,384 noted) and F15 row (N-03).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

NOT RUN -- EXCLUDED-SCOPE and STALE. cpp/ea_conditioning (sha256 b7a55528..., built 2026-10-20 21:06) predates cpp/shared/TestRunUtils.h (changed 2026-10-21..26: de61365, b63aff1, 36cafb3, b53ff5d), and rebuilding is a build. run.sh/control.sh are written in full, record the source evidence, and self-guard (exit 3) unless EA_REPRO_FORCE=1.

**What this reproducer does not establish:** The predicted outcome (h' = -1, h_out = -8 on a 3-sample 1-bit file) is derived from the current source and not measured. reproduced=false.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-18-observed.log` and `PROV-18-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |
| `control.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |

Binaries (sha256):
- `b7a55528a8270672a89bd26265feb529293718a83d2a19a350cd035289d83460 (built 2026-10-20, STALE against cpp/shared/TestRunUtils.h; not run)`  ea_conditioning

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-18 observed.txt  2026-11-07 21:56:20 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 b7a55528a8270672a89bd26265feb529293718a83d2a19a350cd035289d83460  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_conditioning  (mtime 2026-10-20 21:06:00)
fold without guard: conditioning_main.cpp:388:        ret_min_entropy = collision_test(data.bsymbols, data.blen, verbose, "Bitstring");
sentinel:           collision_test.h:49:		return -1.0; 
intake in ea_conditioning: dataset_meets_minimum calls = 0 ; alph_size<=1 refusal = 0
sources newer than the binary: cpp/shared/TestRunUtils.h 
RESULT: NOT-RUN -- EXCLUDED-SCOPE and STALE: cpp/ea_conditioning predates cpp/shared/TestRunUtils.h ; not run (EA_REPRO_FORCE=1 overrides)
```

### control.txt (verbatim)

```
# PROV-18 control.txt  2026-11-07 21:56:20 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 b7a55528a8270672a89bd26265feb529293718a83d2a19a350cd035289d83460  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_conditioning  (mtime 2026-10-20 21:06:00)
RESULT: NOT-RUN -- EXCLUDED-SCOPE and STALE: 1 source files are newer than cpp/ea_conditioning
```
