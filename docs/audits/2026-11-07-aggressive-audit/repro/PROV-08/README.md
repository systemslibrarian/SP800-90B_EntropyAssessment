# PROV-08 -- ea_restart -q still prints 'H_I: ...' (unconditional printf at restart_main.cpp:735)

**Provisional ID:** PROV-08 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (text only)
**Direction:** neutral
**Component:** cpp/restart_main.cpp:main() :735 `printf("H_I: %f\n", H_I);` with no `if (verbose > 0)`; compare :1170-1176 where the same value is reprinted under the guard.
**Spec:** n/a (CLI contract; usage :208 "-q: Quiet mode, less output to screen.").
**Prior-fix interaction (rule 12):** C16 (7a0be01) scales H_I before this line; none touched the print.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 4.10 and 9.10; output.md 2.9 (both SOURCE-CONFIRMED only).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

NOT RUN -- HEAVY. Every ea_restart run reads exactly 1,000,000 samples (restart_main.cpp:694, no EA_ALLOW_SHORT_DATASET escape), which the brief classes as a heavy job. run.sh is written in full and self-guards (exit 3) unless EA_REPRO_HEAVY=1; its input (every row constant) makes the sanity check fail immediately after line 735, so the measured cost is the file read plus counting (well under a second) -- it is heavy by the rule's sample count, not by CPU.

**What this reproducer does not establish:** Source-confirmed only until run. reproduced=false.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-08-observed.log` and `PROV-08-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |
| `control.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |

Binaries (sha256):
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-08 observed.txt  2026-11-07 21:56:12 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
code: restart_main.cpp:735:    printf("H_I: %f\n", H_I);;restart_main.cpp:1173:        printf("H_I: %f\n", H_I);;
RESULT: NOT-RUN -- HEAVY: ea_restart requires a 1,000,000-sample matrix (restart_main.cpp:694), no test escape. Not run in this phase (brief ground rule 4: a run on >= 200,000 samples is a heavy job). Re-run with EA_REPRO_HEAVY=1 when the heavy-job slot is free.
```

### control.txt (verbatim)

```
# PROV-08 control.txt  2026-11-07 21:56:12 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
RESULT: NOT-RUN -- HEAVY: ea_restart requires a 1,000,000-sample matrix. Not run in this phase (brief ground rule 4: a run on >= 200,000 samples is a heavy job). Re-run with EA_REPRO_HEAVY=1 when the heavy-job slot is free.
```
