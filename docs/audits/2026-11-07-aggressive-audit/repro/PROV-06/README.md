# PROV-06 -- Repeated -o leaves a permanent C14 placeholder at the first path after a run that exits 0

**Provisional ID:** PROV-06 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (fail-closed for the first path; no diagnostic)
**Direction:** neutral
**Component:** cpp/non_iid_main.cpp:main() :230-234 (`case 'o'`: claimReportTarget() at every occurrence, outputfilename overwritten); cpp/iid_main.cpp:227-231; cpp/restart_main.cpp:444-448.
**Spec:** n/a (report integrity / CLI contract).
**Prior-fix interaction (rule 12):** C14 (97fbc6c). The 2026-10-11 record and the analysis both class it fail-closed; a harness that passes -o twice reads a refusal where it expected a report.
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 4.2 and 9.9 (measured repeated-o rc=0); output.md section 3 C14 row.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: `-q -o a.json -o b.json rand8_short.bin 8` -> exit 0; a.json errorLevel -1, reportComplete false, no testCases, 'Refuse this file'; b.json errorLevel 0 with hAssessed 5.860893744485249; nothing on stdout/stderr about the superseded -o.

**What this reproducer does not establish:** Only ea_non_iid was run.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-06-observed.log` and `PROV-06-control.log`.

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
# PROV-06 observed.txt  2026-11-07 21:56:10 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-06/out/a.json -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-06/out/b.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[repeated_o]=0  stdout=rep.out stderr=rep.err
a.json: errorLevel=-1 reportComplete=false testCases=<absent> errorMessage="The assessment did not complete; this placeholder was written when the output path was claimed. Any earlier report at this path has been replaced. Refuse this file."
b.json: errorLevel=0 reportComplete=<absent> Overall.hAssessed=5.860893744485249
stdout/stderr mention of the discarded first -o: stdout=0 stderr=0 (0 = no diagnostic)
RESULT: PASS -- exit 0, b.json is the full report, a.json is left as a permanent placeholder (errorLevel -1, 'Refuse this file') with no diagnostic about the second -o
```

### control.txt (verbatim)

```
# PROV-06 control.txt  2026-11-07 21:56:10 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-06/out/a1.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[single_o]=0  stdout=single.out stderr=single.err
a1.json: errorLevel=0 reportComplete=<absent> Overall.hAssessed=5.860893744485249
RESULT: CONTROL-OK -- one -o: the path holds the complete report; the placeholder in run.sh is the second -o's doing
```
