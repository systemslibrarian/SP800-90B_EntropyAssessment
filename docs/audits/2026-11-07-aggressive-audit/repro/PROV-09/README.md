# PROV-09 -- ea_restart IID-suite failure report has errorLevel 2 but no errorClass (ea_iid writes 'statistical' for the same outcome)

**Provisional ID:** PROV-09 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (report classification; the fail-closed verdict is correct)
**Direction:** neutral
**Component:** cpp/restart_main.cpp:main() :1149-1167 (errorLevel = 2, errorMsg set, errorClass never set, return 1) vs cpp/iid_main.cpp:535-537 (errorLevel 2, errorClass "statistical") and restart_main.cpp:810-825 / :1177-1193 (errorClass "statistical" on the other two restart rejections).
**Spec:** n/a (report integrity).
**Prior-fix interaction (rule 12):** R-3 (23dca69) chose the right report object on this path; #252/D-5 (007d0e7) made the battery fail closed; the errorClass field was added with the C14/N-09 report work and never applied here.
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.9 and 5.6; restart.md S5 (SOURCE-CONFIRMED).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

run.sh NOT RUN -- HEAVY (ea_restart -i on a 1,000,000-sample checkerboard: chi-square and LRS on rows and columns before the deterministic failure); self-guards unless EA_REPRO_HEAVY=1. control.sh RAN (light): ea_iid on rand8_short.bin 8 -> exit 1, errorLevel 2, errorClass "statistical", IID false, assessmentComplete true. The source read in run.sh (0 errorClass assignments in restart_main.cpp:1149-1167) is recorded in observed.txt.

**What this reproducer does not establish:** The restart half is source-confirmed only until run. reproduced=false.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-09-observed.log` and `PROV-09-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 3 | 3 = NOT-RUN (heavy / excluded-scope gate) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-09 observed.txt  2026-11-07 21:56:13 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
code: restart_main.cpp:1155 sets errorLevel = 2 and errorMsg; errorClass assignments in that block (lines 1149-1167): 0
RESULT: NOT-RUN -- HEAVY: ea_restart -i on a 1,000,000-sample matrix (chi-square + LRS on rows and columns before the deterministic failure). Not run in this phase (brief ground rule 4: a run on >= 200,000 samples is a heavy job). Re-run with EA_REPRO_HEAVY=1 when the heavy-job slot is free.
```

### control.txt (verbatim)

```
# PROV-09 control.txt  2026-11-07 21:56:13 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
fixture sha256 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-09/out/c_iid.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[iid_fail]=1  stdout=c_iid.out stderr=c_iid.err
rc=1 JSON errorLevel=2 errorClass="statistical" errorMessage="IID test suite failed; no IID min-entropy estimate was awarded." IID=false assessmentComplete=true
RESULT: CONTROL-OK -- ea_iid encodes the same statistical rejection as errorLevel 2 + errorClass 'statistical'; the restart path (run.sh) omits the class
```
