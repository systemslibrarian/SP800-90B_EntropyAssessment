# PROV-01 -- Stale success report survives when an option error precedes -o (all three tools)

**Provisional ID:** PROV-01 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** MEDIUM (report integrity; the file channel can present a complete errorLevel-0 report that belongs to a different run -- the exact hazard C14 was written to close; overstates only for a consumer that reads the report without the exit status, which is C14's own threat model)
**Direction:** overstates (file channel) / neutral (exit status is correct)
**Component:** cpp/non_iid_main.cpp:claimReportTarget() called only inside getopt `case 'o'` (:230-234); print_usage() exits reached earlier in the getopt loop at :182-192 (-l) and :236 (default/unknown option). Same shape: cpp/iid_main.cpp:227-231, cpp/restart_main.cpp:444-448 (claim) vs :451-460 (-s/unknown).
**Spec:** n/a (report integrity). The contract broken is the code's own: non_iid_main.cpp:67-76 "After any run, including an abort, the file is either this run's report or a report saying the assessment did not complete. It is never a stale success."
**Prior-fix interaction (rule 12):** C14 (97bfc6c, the claim); A04/F04 (663f9ae) and A05/F03 (de61365, 663f9ae) touch the same argv prescan; OC-104 (36cafb3) refuses before the claim. Rule-12 pairs: C14+A05 (a claim moved to the prescan must still go through the writeJsonReport choke point), C14+A04, C14+OC-104. Regression gap: cpp/selftest/regression-output.sh tests only `-o` FIRST (no operand); 2026-10-11 COVERAGE.md:238 recorded the no-report paths without drawing the C14 consequence.
**Analysis-phase source (re-checked here):** logs/analysis/prior-repairs.md section 3 (REPRODUCED there, log analysis-prior-repairs-c14-order-probe.log) and section 5 item 1.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED (4 of 4 probes: ea_non_iid -Z and -l 5x,10, ea_iid -Z, ea_restart -Z; each left the previous errorLevel-0 report byte-identical with exit 255).

**What this reproducer does not establish:** The stale artefact for ea_iid and ea_restart is an ea_non_iid success report copied into place: what is tested is that the file is not touched, not that those tools can produce it. glibc getopt permutation changes nothing here (the offending option already precedes the operand). The January procedure (`ea_non_iid -vv bin/ringOsc-nist.bin`) uses no -o and is unaffected.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-01-observed.log` and `PROV-01-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-01 observed.txt  2026-11-07 21:56:05 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
fixture sha256 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin (10,000 samples, 8-bit)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/good.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[baseline]=0  stdout=baseline.out stderr=baseline.err
good.json errorLevel=0 testCases=11
good.json sha256 ab05dc8eef4ab840c555ddc5603f637b746154e61760d55e3d1c874177c2a19e
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -Z -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/stale_noniid_Z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[noniid_Z]=255  stdout=noniid_Z.out stderr=noniid_Z.err
  noniid_Z: STALE SUCCESS SURVIVED -- stale_noniid_Z.json is byte-identical to good.json (errorLevel 0), tool rc=255
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -l 5x,10 -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/stale_noniid_l.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[noniid_l]=255  stdout=noniid_l.out stderr=noniid_l.err
  noniid_l: STALE SUCCESS SURVIVED -- stale_noniid_l.json is byte-identical to good.json (errorLevel 0), tool rc=255
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -Z -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/stale_iid_Z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[iid_Z]=255  stdout=iid_Z.out stderr=iid_Z.err
  iid_Z: STALE SUCCESS SURVIVED -- stale_iid_Z.json is byte-identical to good.json (errorLevel 0), tool rc=255
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -Z -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/stale_restart_Z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[restart_Z]=255  stdout=restart_Z.out stderr=restart_Z.err
  restart_Z: STALE SUCCESS SURVIVED -- stale_restart_Z.json is byte-identical to good.json (errorLevel 0), tool rc=255
stale-success survivals: 4 of 4 probes
RESULT: PASS -- an option error parsed BEFORE -o exits 255 without claiming the target; the previous success report survives byte-identical (ea_non_iid x2, ea_iid, ea_restart)
```

### control.txt (verbatim)

```
# PROV-01 control.txt  2026-11-07 21:56:06 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/c_good.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[baseline]=0  stdout=c_baseline.out stderr=c_baseline.err
c_good.json sha256 8ffdbec4bfea9f131f7c73620a6ba664ce4385fd2df58a0ffc52eeea2f82bcde errorLevel=0
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/c_stale_noniid_Z.json -Z /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[noniid_Z]=255  stdout=c_noniid_Z.out stderr=c_noniid_Z.err
  noniid_Z: replaced by the placeholder (errorLevel -1, reportComplete false), rc=255
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/c_stale_iid_Z.json -Z /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[iid_Z]=255  stdout=c_iid_Z.out stderr=c_iid_Z.err
  iid_Z: replaced by the placeholder (errorLevel -1, reportComplete false), rc=255
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-01/out/c_stale_restart_Z.json -Z /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8 3/symbol
rc[restart_Z]=255  stdout=c_restart_Z.out stderr=c_restart_Z.err
  restart_Z: replaced by the placeholder (errorLevel -1, reportComplete false), rc=255
placeholder replacements: 3 of 3
RESULT: CONTROL-OK -- with -o parsed FIRST the same -Z error replaces the stale report with the fail-closed placeholder (the only ordering regression-output.sh tests)
```
