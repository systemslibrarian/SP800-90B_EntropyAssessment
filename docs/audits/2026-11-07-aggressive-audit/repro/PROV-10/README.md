# PROV-10 -- Restart JSON has no field for min(H_r, H_c, H_I), and a declined estimator is omitted with no not-run flag (F05 absent from ea_restart)

**Provisional ID:** PROV-10 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** MEDIUM (report integrity: the quantity 3.1.4.2 names as the assessment is not in the report and a consumer reading h_i alone overstates; a minimum over fewer estimators than 6.2 lists is invisible -- 'which can only make the figure higher', test_case_base.h:26-31)
**Direction:** neutral on the number; overstating in visibility (h_i >= min; a dropped estimator can only raise the minimum)
**Component:** cpp/restart_main.cpp:main() :1199-1204 (Overall carries h_r, h_c, h_i only), :1222 (the minimum is printed only under `verbose > 0`), every fallible fold :972-1001 and after (`if (ret >= 0) {...}` with no else; `grep -c not_run` = 0) vs cpp/non_iid_main.cpp (16 sites) and cpp/shared/test_case_base.h:37-38.
**Spec:** SP 800-90B 3.1.4.2 (PDF p. 21): "Otherwise, the entropy assessment of the noise source is taken as the minimum of the row, the column and the initial estimates, i.e., min(Hr, Hc, HI)." 6.2 (PDF p. 49): "the minimum of all the estimates is taken as the entropy assessment". 6.3.6 step 2 (PDF p. 56): "If v < u, this estimate cannot be computed."
**Prior-fix interaction (rule 12):** R-2 (d892b90) made the decline silent in restart (sentinel skipped, no flag); F05 (dfe325a) added literalEstimateNotRun/bitstringEstimateNotRun to ea_non_iid only; C16/C23 (7a0be01) added restartHI/restartXcutoff fields but no assessed figure; NOVEL-03 (25fbb54) touched the restart report labels. Rule-12 pair R-2+F05 undeclared.
**Analysis-phase source (re-checked here):** logs/analysis/restart.md S1 and S2; prior-repairs.md F05 row (OPEN, SOURCE-CONFIRMED) and E3; output.md 2.9.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

NOT RUN -- HEAVY (ea_restart -n on the 1,000,000-sample de Bruijn B(100,3) file from audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py 100 11, several minutes; the control is ea_non_iid on the same bytes, also 1,000,000 samples). Both self-guard unless EA_REPRO_HEAVY=1. The grep evidence (0 not_run sites in restart_main.cpp, 16 in non_iid_main.cpp) is recorded in observed.txt.

**What this reproducer does not establish:** Which LRS estimate declines (rows certainly: u = 3, v = 2; columns not necessarily) is predicted, not measured; run.sh passes on the no-min-field half alone and reports the not-run half separately. reproduced=false.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-10-observed.log` and `PROV-10-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |
| `control.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |

Binaries (sha256):
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-10 observed.txt  2026-11-07 21:56:13 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
grep -c not_run cpp/restart_main.cpp = 0 ; cpp/non_iid_main.cpp = 16
RESULT: NOT-RUN -- HEAVY: ea_restart -n on a 1,000,000-sample 8-bit de Bruijn B(100,3) matrix (ten estimators on rows and columns). Not run in this phase (brief ground rule 4: a run on >= 200,000 samples is a heavy job). Re-run with EA_REPRO_HEAVY=1 when the heavy-job slot is free.
```

### control.txt (verbatim)

```
# PROV-10 control.txt  2026-11-07 21:56:14 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
RESULT: NOT-RUN -- HEAVY: ea_non_iid on the 1,000,000-sample de Bruijn file. Not run in this phase (brief ground rule 4: a run on >= 200,000 samples is a heavy job). Re-run with EA_REPRO_HEAVY=1 when the heavy-job slot is free.
```
