# PROV-25 -- utils.h comment claims non_iid_main.cpp refuses > INT_MAX samples; it does not

**Provisional ID:** PROV-25 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (documentation of a sufficiency argument; harmless today because n_choose_2 is reached only from the IID 5.2.5 test)
**Direction:** neutral
**Component:** cpp/shared/utils.h:1023-1025 (comment above n_choose_2) vs cpp/non_iid_main.cpp (grep INT_MAX: 0 hits); cpp/iid_main.cpp:393-408 has the guard; callers of n_choose_2: cpp/shared/lrs_test.h:712-713 only.
**Spec:** n/a (documentation).
**Prior-fix interaction (rule 12):** C18 (473cd5f) wrote the comment with the int64 repair.
**Analysis-phase source (re-checked here):** logs/analysis/aggregation.md headline item 5 and 2.7; intake.md 2.6 and S5; mcv.md S-7.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED by grep: the comment names non_iid_main.cpp; `grep -c INT_MAX cpp/non_iid_main.cpp` = 0; control: iid_main.cpp carries the refusal (3 references).

**What this reproducer does not establish:** A documentation defect; no tool behaviour changes.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-25-observed.log` and `PROV-25-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- (no production binary run: source/model only)

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-25 observed.txt  2026-11-07 21:56:29 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
source sha256 a5462f85e296d8fcd908e0f7f56f445aa0905724d840ea69082cdbc97ffdc60e  cpp/shared/utils.h ; b3eb23f72c4d9f5b40faed49be22b6dea6fe6aaa9803e0b2f54d257dccb512ab  cpp/non_iid_main.cpp
the comment (utils.h:1023-1025):
  | // SUFFICIENCY IS PROVABLE, not hoped for. Callers refuse a sample count above
  | // INT_MAX (iid_main.cpp, non_iid_main.cpp), so n <= 2^31 - 1 and
  | // n*n <= 4.61e18, comfortably inside INT64_MAX = 9.22e18. The assert states
grep -c INT_MAX cpp/non_iid_main.cpp = 0
callers of n_choose_2: cpp/shared/lrs_test.h:712 cpp/shared/lrs_test.h:713 
RESULT: PASS -- the comment names non_iid_main.cpp as refusing > INT_MAX samples; non_iid_main.cpp contains no INT_MAX at all
```

### control.txt (verbatim)

```
# PROV-25 control.txt  2026-11-07 21:56:29 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
grep -n INT_MAX cpp/iid_main.cpp:
  iid_main.cpp:393:    if (testdata.len > INT_MAX) {
  iid_main.cpp:397:            std::to_string(INT_MAX) + "-bit limit of the Section 5 test code.";
  iid_main.cpp:400:               testdata.len, INT_MAX);
RESULT: CONTROL-OK -- iid_main.cpp carries the INT_MAX refusal the comment describes (3 references); non_iid_main.cpp does not
```
