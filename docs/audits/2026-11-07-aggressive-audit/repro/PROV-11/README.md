# PROV-11 -- 'type' is the empty string in every completed ea_non_iid / ea_iid report

**Provisional ID:** PROV-11 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (reporting)
**Direction:** neutral
**Component:** cpp/shared/test_run_base.h: `type` member, written at GetBaseJson() :65; never assigned in cpp/non_iid_main.cpp or cpp/iid_main.cpp (grep testRun.type: 0 each); the C14 placeholders write "non-IID" (non_iid_main.cpp:82) / "IID" (iid_main.cpp:79); restart_main.cpp assigns "Restart".
**Spec:** n/a (report integrity).
**Prior-fix interaction (rule 12):** C14 (97fbc6c) wrote the type into the placeholder only.
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.10 and 5.5 (CONFIRMED Q1/Q4b/Q4c); mcv.md section 7 item 2.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: ea_non_iid success report type "", ea_iid report (errorLevel 2) type "", ea_non_iid input-error report type ""; control placeholders carry "non-IID" and "IID".

**What this reproducer does not establish:** ea_restart not run (its reports set the field, per source).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-11-observed.log` and `PROV-11-control.log`.

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
# PROV-11 observed.txt  2026-11-07 21:56:14 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-11/out/t_n.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1
rc[noniid_ok]=0  stdout=t_n.out stderr=t_n.err
ea_non_iid success report: rc=0 errorLevel=0 type="" IID=false
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-11/out/t_i.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[iid_fail]=1  stdout=t_i.out stderr=t_i.err
ea_iid report (battery outcome rc=1): errorLevel=2 type="" assessmentMode="IID"
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-11/out/t_e.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-11/out/does-not-exist.bin 8
rc[noniid_err]=255  stdout=t_e.out stderr=t_e.err
ea_non_iid error report (missing input): rc=255 errorLevel=-1 type=""
assignments of testRun.type in the mains: non_iid_main.cpp=0 iid_main.cpp=0 restart_main.cpp(.type =)=2
RESULT: PASS -- type is the empty string in the ea_non_iid success report, the ea_iid report and the ea_non_iid error report
```

### control.txt (verbatim)

```
# PROV-11 control.txt  2026-11-07 21:56:14 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-11/out/c_p.json
rc[placeholder_n]=255  stdout=c_p.out stderr=c_p.err
ea_non_iid placeholder (no operand): rc=255 errorLevel=-1 type="non-IID"
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-11/out/c_pi.json
rc[placeholder_i]=255  stdout=c_pi.out stderr=c_pi.err
ea_iid placeholder (no operand): rc=255 errorLevel=-1 type="IID"
RESULT: CONTROL-OK -- the placeholders name the tool ('non-IID', 'IID'); the completed reports in run.sh say the empty string
```
