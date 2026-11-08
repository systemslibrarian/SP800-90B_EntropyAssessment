# PROV-19 -- reportComplete is written only by the placeholder (false); no completed report carries the key

**Provisional ID:** PROV-19 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (schema asymmetry)
**Direction:** neutral
**Component:** claimReportTarget() writes `j["reportComplete"] = false` (cpp/non_iid_main.cpp:85, cpp/iid_main.cpp:83, cpp/restart_main.cpp:356); cpp/shared/test_run_base.h:GetBaseJson() :61-103 never writes the key.
**Spec:** n/a (report integrity).
**Prior-fix interaction (rule 12):** C14 (97fbc6c) introduced the key in the placeholder only.
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.4 ('asymmetry worth knowing', measured Q1: reportComplete present False) and 4.4.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: ea_non_iid success (errorLevel 0), ea_non_iid input error (errorLevel -1) and ea_iid statistical failure (errorLevel 2) all lack reportComplete; the placeholder (control) has reportComplete false.

**What this reproducer does not establish:** A consumer contract issue only; no figure involved.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-19-observed.log` and `PROV-19-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-19 observed.txt  2026-11-07 21:56:21 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-19/out/s.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1
rc[success]=0  stdout=s.out stderr=s.err
ea_non_iid success: rc=0 errorLevel=0 reportComplete=<absent>
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-19/out/e.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-19/out/does-not-exist.bin 8
rc[error]=255  stdout=e.out stderr=e.err
ea_non_iid input error: rc=255 errorLevel=-1 reportComplete=<absent>
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-19/out/i.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[iid]=1  stdout=i.out stderr=i.err
ea_iid statistical failure: rc=1 errorLevel=2 reportComplete=<absent>
writers of 'reportComplete' in cpp/: cpp/iid_main.cpp:83 cpp/non_iid_main.cpp:85 cpp/restart_main.cpp:356 
RESULT: PASS -- no completed report carries reportComplete; only the placeholder does (false)
```

### control.txt (verbatim)

```
# PROV-19 control.txt  2026-11-07 21:56:21 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-19/out/c_p.json
rc[placeholder]=255  stdout=c_p.out stderr=c_p.err
placeholder: rc=255 errorLevel=-1 reportComplete=false
RESULT: CONTROL-OK -- the placeholder writes reportComplete: false; the completed reports in run.sh omit the key instead of writing true
```
